"""Test motoru için Minnesota BVAR (doğal eşlenik Normal-ters Wishart, sahte gözlemler).

Bu modül test motorunun (`test_et.py --model bvar`) parçasıdır; tek başına
"bulgu" üretmek için çağrılmaz. Matematik `ogrenme/bvar/bvar_ders.ipynb` ile aynıdır:

    prior   : Minnesota, Bańbura-Giannone-Reichlin (2010) sahte gözlemleri, θ = 1
    λ seçimi: marjinal olabilirlik (kapalı formül), her tahmin noktasında yeniden
    tahmin   : posterior çekilişleri + düzensiz uçta (ragged edge) Σ'ya göre koşullu simülasyon

Gerçek zamanlılık kuralı (en önemli kısım):
    Hedef ayı t, hedef gecikmesi h, hedefin yayın gecikmesi L_y için tahmin anı
    τ = t - (h - L_y) aydır (ay sonu). Her seri v, τ - L_v ayına kadar bilinir.
    `hedef_cekilisleri` bu sınırdan sonraki her değeri NaN yapar; model yalnızca
    bütün serilerin bilindiği son aya (dengeli uç) kadar tahmin edilir, sonrasında
    bilinen değerler koşullu simülasyona gözlem olarak girer.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import multigammaln
from scipy.stats import invwishart


# ------------------------------------------------------------------ çekirdek
def gecikme_matrisi(Y: np.ndarray, p: int) -> tuple[np.ndarray, np.ndarray]:
    """Y: T×n -> (Y_t, X_t). X_t = [y_{t-1}, ..., y_{t-p}, 1]."""
    T, _ = Y.shape
    X = np.hstack([Y[p - l: T - l] for l in range(1, p + 1)] + [np.ones((T - p, 1))])
    return Y[p:], X


def ar1_sigma(Y: np.ndarray) -> np.ndarray:
    """Her seri için sabitli AR(1) artıklarının standart sapması (prior ölçeği)."""
    s = []
    for i in range(Y.shape[1]):
        y, x = Y[1:, i], np.column_stack([Y[:-1, i], np.ones(len(Y) - 1)])
        b = np.linalg.lstsq(x, y, rcond=None)[0]
        s.append(np.std(y - x @ b, ddof=2))
    return np.array(s)


def sahte_gozlemler(sigma, delta, lam, p, d=1.0, eps=1e-4):
    n = len(sigma)
    Jp = np.diag(np.arange(1, p + 1) ** d)
    Yd = np.vstack([np.diag(delta * sigma) / lam, np.zeros((n * (p - 1), n)),
                    np.diag(sigma), np.zeros((1, n))])
    Xd = np.zeros((n * p + n + 1, n * p + 1))
    Xd[: n * p, : n * p] = np.kron(Jp, np.diag(sigma)) / lam
    Xd[-1, -1] = eps
    return Yd, Xd


def log_m(Y: np.ndarray, X: np.ndarray) -> float:
    """Düz (|Σ|^{-(n+1)/2}) ön-prior altında log marjinal yoğunluk (sabitler hariç)."""
    T, n = Y.shape
    k = X.shape[1]
    XtX = X.T @ X
    E = Y - X @ np.linalg.solve(XtX, X.T @ Y)
    return float(-n * (T - k) / 2 * np.log(np.pi) - n / 2 * np.linalg.slogdet(XtX)[1]
                 + multigammaln((T - k) / 2, n) - (T - k) / 2 * np.linalg.slogdet(E.T @ E)[1])


def kur(Y_tum: np.ndarray, p: int, lam: float, delta: np.ndarray, d: float = 1.0) -> dict:
    Y, X = gecikme_matrisi(Y_tum, p)
    n = Y.shape[1]
    Yd, Xd = sahte_gozlemler(ar1_sigma(Y_tum), delta, lam, p, d)
    Ys, Xs = np.vstack([Y, Yd]), np.vstack([X, Xd])
    XtX = Xs.T @ Xs
    B = np.linalg.solve(XtX, Xs.T @ Ys)
    E = Ys - Xs @ B
    return {"B": B, "S": E.T @ E, "nu": Ys.shape[0] - Xs.shape[1], "XtX_inv": np.linalg.inv(XtX),
            "log_ml": log_m(Ys, Xs) - log_m(Yd, Xd), "n": n, "p": p, "lam": lam}


def lambda_sec(Y_tum, p, izgara, delta, d=1.0) -> dict:
    modeller = [kur(Y_tum, p, float(l), delta, d) for l in izgara]
    return modeller[int(np.argmax([m["log_ml"] for m in modeller]))]


def eslik_matrisleri(B_ler: np.ndarray, n: int, p: int) -> np.ndarray:
    """(a, k, n) çekilişlerden (a, np, np) eşlik matrisleri."""
    a = B_ler.shape[0]
    F = np.zeros((a, n * p, n * p))
    F[:, :n, :] = np.transpose(B_ler[:, : n * p, :], (0, 2, 1))
    F[:, n:, :-n] = np.eye(n * (p - 1))
    return F


def cekilisler(model: dict, adet: int, rng: np.random.Generator, kok_siniri: float = 1.02,
               en_fazla_kat: int = 50) -> tuple[np.ndarray, np.ndarray, float]:
    """Posterior'dan (B, Σ) çekilişleri; kökü kok_siniri'nı aşanlar atılır.

    Kabul oranına göre uyarlanarak, `adet` patlamayan çekiliş toplanana kadar çekilir.
    Toplam çekiliş `en_fazla_kat * adet`'i aşarsa (kabul < ~%2) hata verilir.
    """
    B, S, nu, n, p = model["B"], model["S"], model["nu"], model["n"], model["p"]
    k = B.shape[0]
    L_V = np.linalg.cholesky(model["XtX_inv"])
    B_top, S_top, toplam, atilan = [], [], 0, 0
    while toplam < en_fazla_kat * adet:
        eksik = adet - sum(len(x) for x in B_top)
        if eksik <= 0:
            break
        kabul = max((toplam - atilan) / toplam, 0.02) if toplam else 1.0
        m = min(int(eksik / kabul * 1.15) + 5, 20 * adet)
        Sig = np.asarray(invwishart.rvs(df=nu, scale=S, size=m, random_state=rng)).reshape(m, n, n)
        LS = np.linalg.cholesky(Sig)
        Z = rng.standard_normal((m, k, n))
        Bd = B[None] + np.einsum("ij,mjq,mlq->mil", L_V, Z, LS)      # B + L_V Z LS'
        kok = np.abs(np.linalg.eigvals(eslik_matrisleri(Bd, n, p))).max(axis=1)
        tamam = kok <= kok_siniri
        toplam += m
        atilan += int((~tamam).sum())
        B_top.append(Bd[tamam])
        S_top.append(Sig[tamam])
    B_ler, S_ler = np.concatenate(B_top)[:adet], np.concatenate(S_top)[:adet]
    if len(B_ler) < adet:
        raise ValueError(f"Yeterli patlamayan çekiliş yok ({len(B_ler)}/{adet})")
    return B_ler, S_ler, atilan / toplam


def sv_cekilisleri(Y_tum: np.ndarray, p: int, lam: float, delta: np.ndarray, d: float, adet: int,
                   rng: np.random.Generator, kok_siniri: float, sv: dict) -> tuple:
    """Ortak stokastik oynaklıklı BVAR (Carriero, Clark ve Marcellino 2016), Gibbs örnekleyici.

    Model:  y_t = B' x_t + exp(h_t / 2) ε_t,  ε_t ~ N(0, Σ)
            h_t = φ h_{t-1} + η_t,  η_t ~ N(0, s²),  h_1 ~ N(0, s² / (1 - φ²))
    Prior:  (B, Σ) Minnesota sahte gözlemleri (λ dışarıdan verilir; ölçekleri değişmez),
            s² ~ ters gamma(a0, b0); φ sabit.
    Adımlar: (1) h verilince satırlar exp(-h/2) ile ağırlıklandırılır, (B, Σ) doğal eşlenik
             posteriordan çekilir; (2) (B, Σ) verilince h, tek/çift indeks blokları hâlinde
             (Markov yapısı sayesinde blok içi koşullu bağımsız) bağımsız-öneri Metropolis ile;
             (3) s² ters gammadan.
    Patlayan çekilişler zincir bittikten sonra atılır (kısıtlı posteriordan ret örneklemesi).
    Döndürür: B_ler (a,k,n), S_ler (a,n,n), h_son (a,), s2 (a,), atılan pay
    """
    phi = float(sv.get("phi", 0.95))
    a0, b0 = float(sv.get("a0", 3.0)), float(sv.get("b0", 0.1))
    yanma, seyrek = int(sv.get("yanma", 500)), int(sv.get("seyrek", 2))
    Y, X = gecikme_matrisi(Y_tum, p)
    T, n = Y.shape
    k = X.shape[1]
    Yd, Xd = sahte_gozlemler(ar1_sigma(Y_tum), delta, lam, p, d)
    XdtXd, XdtYd = Xd.T @ Xd, Xd.T @ Yd
    YdtYd = Yd.T @ Yd
    nu = T + Yd.shape[0] - k
    h = np.zeros(T)
    s2 = b0 / (a0 - 1)
    B_top, S_top, h_top, s2_top = [], [], [], []
    toplam, atilan, it = 0, 0, 0
    hedef_it = yanma + 50 * adet * seyrek
    while len(B_top) < adet and it < hedef_it:
        # (1) (B, Σ) | h
        w = np.exp(-h / 2)[:, None]
        Xw, Yw = X * w, Y * w
        XtX = Xw.T @ Xw + XdtXd
        XtX_inv = np.linalg.inv(XtX)
        XtX_inv = 0.5 * (XtX_inv + XtX_inv.T)
        Bh = XtX_inv @ (Xw.T @ Yw + XdtYd)
        S = Yw.T @ Yw + YdtYd - Bh.T @ XtX @ Bh
        S = 0.5 * (S + S.T)
        Sig = np.asarray(invwishart.rvs(df=nu, scale=S, random_state=rng)).reshape(n, n)
        Bd = Bh + np.linalg.cholesky(XtX_inv) @ rng.standard_normal((k, n)) @ np.linalg.cholesky(Sig).T
        # (2) h | B, Σ
        e = Y - X @ Bd
        q = np.einsum("ti,ij,tj->t", e, np.linalg.inv(Sig), e)
        for eslik in (0, 1):
            i = np.arange(eslik, T, 2)
            onceki = np.where(i > 0, h[np.maximum(i - 1, 0)], 0.0)
            sonraki = np.where(i < T - 1, h[np.minimum(i + 1, T - 1)], 0.0)
            ic = (i > 0) & (i < T - 1)
            mu = np.where(ic, phi * (onceki + sonraki) / (1 + phi ** 2),
                          np.where(i == 0, phi * sonraki, phi * onceki))
            v = np.where(ic, s2 / (1 + phi ** 2), s2)
            oneri = mu + np.sqrt(v) * rng.standard_normal(len(i))
            log_r = (-n / 2 * oneri - q[i] / 2 * np.exp(-oneri)) - (-n / 2 * h[i] - q[i] / 2 * np.exp(-h[i]))
            kabul = np.log(rng.random(len(i))) < log_r
            h[i] = np.where(kabul, oneri, h[i])
        # (3) s² | h
        art = h[1:] - phi * h[:-1]
        ssr = float(art @ art) + (1 - phi ** 2) * h[0] ** 2
        s2 = 1.0 / rng.gamma(a0 + T / 2, 1.0 / (b0 + ssr / 2))
        it += 1
        if it > yanma and (it - yanma) % seyrek == 0:
            toplam += 1
            kok = np.abs(np.linalg.eigvals(eslik_matrisleri(Bd[None], n, p)[0])).max()
            if kok > kok_siniri:
                atilan += 1
                continue
            B_top.append(Bd)
            S_top.append(Sig)
            h_top.append(h[-1])
            s2_top.append(s2)
    if len(B_top) < adet:
        raise ValueError(f"SV: yeterli patlamayan çekiliş yok ({len(B_top)}/{adet})")
    return (np.array(B_top), np.array(S_top), np.array(h_top), np.array(s2_top),
            atilan / max(toplam, 1))


def kosullu_yollar(B_ler: np.ndarray, S_ler: np.ndarray, gecmis: np.ndarray, gozlenen: np.ndarray,
                   rng: np.random.Generator, olcek: np.ndarray | None = None) -> np.ndarray:
    """Her çekiliş için bir gelecek yolu.

    gecmis  : (p, n) dengeli ucun son p ayı (tamamen bilinen), kronolojik
    gozlenen: (m, n) dengeli uçtan sonraki m ay; NaN = bilinmiyor (simüle edilir),
              sayı = o anda bilinen değer (yol bu değeri taşır, diğerleri Σ'ya göre koşullanır)
    olcek   : (a, m) isteğe bağlı; s. adımda çekilişin kovaryansı olcek[:, s] · Σ olur
              (stokastik oynaklık). Koşullu ortalama ölçekten etkilenmez, koşullu varyans ölçeklenir.
    Döndürür: (a, p + m, n)
    """
    a = B_ler.shape[0]
    p, n = gecmis.shape
    m = gozlenen.shape[0]
    yol = np.empty((a, p + m, n))
    yol[:, :p] = gecmis
    S_temel = S_ler
    LS_temel = np.linalg.cholesky(S_ler)
    for s in range(m):
        t = p + s
        if olcek is None:
            S_ler, LS = S_temel, LS_temel
        else:
            S_ler = S_temel * olcek[:, s, None, None]
            LS = LS_temel * np.sqrt(olcek[:, s, None, None])
        x = np.concatenate([yol[:, t - l] for l in range(1, p + 1)] + [np.ones((a, 1))], axis=1)
        mu = np.einsum("ak,akn->an", x, B_ler)
        obs = gozlenen[s]
        K = ~np.isnan(obs)
        if K.all():
            yol[:, t] = obs
            continue
        if not K.any():
            yol[:, t] = mu + np.einsum("anq,aq->an", LS, rng.standard_normal((a, n)))
            continue
        U = ~K
        S_KK = S_ler[:, K][:, :, K]
        S_UK = S_ler[:, U][:, :, K]
        S_UU = S_ler[:, U][:, :, U]
        A = np.transpose(np.linalg.solve(S_KK, np.transpose(S_UK, (0, 2, 1))), (0, 2, 1))  # S_UK S_KK^-1
        mu_U = mu[:, U] + np.einsum("auk,ak->au", A, obs[K][None, :] - mu[:, K])
        C = S_UU - np.einsum("auk,avk->auv", A, S_UK)
        C = 0.5 * (C + np.transpose(C, (0, 2, 1)))
        LC = np.linalg.cholesky(C)
        y = np.empty((a, n))
        y[:, K] = obs[K]
        y[:, U] = mu_U + np.einsum("auv,av->au", LC, rng.standard_normal((a, int(U.sum()))))
        yol[:, t] = y
    return yol


# ------------------------------------------------------------------ gerçek zamanlı tahmin
def bilgi_seti(t: pd.Timestamp, h: int, L: dict, hedef_ad: str) -> tuple[pd.Timestamp, dict]:
    """Tahmin anı τ ve her serinin bilindiği son ay."""
    tau = t - pd.DateOffset(months=h - L[hedef_ad])
    return tau, {ad: tau - pd.DateOffset(months=g) for ad, g in L.items()}


def hedef_cekilisleri(Z: pd.DataFrame, hedef_ad: str, var_donusum: str, hedef_donusum: str,
                      t: pd.Timestamp, h: int, L: dict, p: int, delta: np.ndarray, d: float,
                      izgara: np.ndarray, adet: int, kok_siniri: float,
                      rng: np.random.Generator, parametre: tuple | None = None,
                      sv: dict | None = None) -> tuple[np.ndarray, dict]:
    """t ayındaki hedef dönüşümünün (logdiff/yoy/duzey) tahmin dağılımından çekilişler.

    Z: VAR dönüşümlü aylık veri (sütunlar = seriler). Z'de τ'dan sonraki gerçek değerler
    bulunabilir; bu fonksiyon onları bilgi setine göre maskeler.
    parametre: yalnızca doğrulama içindir. (B, Σ) verilirse tahmin yapılmaz, bilinen
    parametrelerle simüle edilir (motor bu argümanı hiç kullanmaz).
    """
    if h < max(1, L[hedef_ad]):
        raise ValueError("hedef gecikmesi en az 1 ve hedefin yayın gecikmesi kadar olmalı")
    tau, bilinen_son = bilgi_seti(t, h, L, hedef_ad)
    b = min(bilinen_son.values())
    Zg = Z.reindex(pd.date_range(Z.index[0], t, freq="MS")).copy()
    for ad, son in bilinen_son.items():
        Zg.loc[Zg.index > son, ad] = np.nan
    blok = Zg.loc[:b]
    if blok.isna().any().any():
        raise ValueError(f"Dengeli örneklemde ({b:%Y-%m} öncesi) eksik değer var")
    Y_tum = blok.values
    n = Y_tum.shape[1]
    if len(Y_tum) < 2 * p + 12:
        raise ValueError(f"BVAR için tahmin örneklemi çok kısa ({len(Y_tum)} ay)")
    gozlenen = Zg.loc[b + pd.DateOffset(months=1): t].values
    olcek, sv_son = None, float("nan")
    if parametre is None:
        model = lambda_sec(Y_tum, p, izgara, delta, d)
        if sv:
            # λ sabit varyanslı modelin marjinal olabilirliğiyle seçilir, SV zinciri o λ ile koşar
            B_ler, S_ler, h_son, s2, atilan = sv_cekilisleri(Y_tum, p, model["lam"], delta, d, adet, rng,
                                                              kok_siniri, sv)
            phi = float(sv.get("phi", 0.95))
            hh, ol = h_son.copy(), []
            for _ in range(len(gozlenen)):
                hh = phi * hh + np.sqrt(s2) * rng.standard_normal(len(hh))
                ol.append(np.exp(hh))
            olcek = np.array(ol).T if ol else None
            sv_son = float(np.median(np.exp(h_son)))
        else:
            B_ler, S_ler, atilan = cekilisler(model, adet, rng, kok_siniri)
    else:
        model = {"lam": float("nan")}
        B_ler, S_ler, atilan = np.repeat(parametre[0][None], adet, 0), np.repeat(parametre[1][None], adet, 0), 0.0
    yollar = kosullu_yollar(B_ler, S_ler, Y_tum[-p:], gozlenen, rng, olcek)

    j = list(Z.columns).index(hedef_ad)
    seri = np.concatenate([np.tile(Y_tum[:, j], (adet, 1)), yollar[:, p:, j]], axis=1)  # son sütun = t
    if var_donusum == "logdiff":
        # VAR'da hedef aylık log farkı (100×Δlog): düzey yerine log farkların toplamı kullanılır
        if hedef_donusum == "logdiff":
            y = seri[:, -1]
        elif hedef_donusum == "yoy":
            y = 100 * (np.exp(seri[:, -12:].sum(axis=1) / 100.0) - 1)
        else:
            raise ValueError("VAR dönüşümü logdiff iken hedef dönüşümü logdiff veya yoy olmalı")
    else:
        duzey = np.exp(seri / 100.0) if var_donusum == "log" else seri
        if hedef_donusum == "logdiff":
            y = 100 * (np.log(duzey[:, -1]) - np.log(duzey[:, -2]))
        elif hedef_donusum == "yoy":
            y = 100 * (duzey[:, -1] / duzey[:, -13] - 1)
        elif hedef_donusum == "duzey":
            y = duzey[:, -1]
        else:
            raise ValueError(f"bilinmeyen hedef dönüşümü: {hedef_donusum}")
    return y, {"lambda": model["lam"], "atilan_pay": atilan, "tahmin_ani": tau, "dengeli_son": b,
               "adim": len(gozlenen), "n_tahmin": len(Y_tum), "n": n, "sv_son": sv_son}
