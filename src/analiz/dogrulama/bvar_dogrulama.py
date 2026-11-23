"""BVAR motor genişlemesinin (H-004) yapay veriyle doğrulanması.

Çalıştırma: python src/analiz/dogrulama/bvar_dogrulama.py  (~12 dk)
T1 (AR yolu eskiyle aynı) yalnızca ESKI_MOTOR ortam değişkeniyle eski motor kopyası verilirse çalışır.
 Gerçek veri KULLANILMAZ,
main() çağrılmaz (kayit/denemeler.csv ve kayit/sonuclar'a hiçbir şey yazılmaz)."""
import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[3]  # proje kökü
import os, tempfile
BURA = Path(__file__).resolve().parent
VERI = Path(tempfile.mkdtemp(prefix="bvar_dogrulama_"))   # yapay veri repo dışında
sys.path.insert(0, str(KOK / "src" / "analiz"))


def yukle(ad, yol):
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


yeni = yukle("test_et_yeni", KOK / "src/analiz/test_et.py")
eski = yukle("test_et_eski", os.environ["ESKI_MOTOR"]) if os.environ.get("ESKI_MOTOR") else None
if eski:
    for _ad in ("KOK", "AYARLAR", "GUNLUK", "SONUCLAR", "KASA_BAYRAK"):   # kopya başka yerde; yolları projeye bağla
        setattr(eski, _ad, getattr(yeni, _ad))
import bvar as bv  # noqa: E402

gunluk_once = (KOK / "kayit/denemeler.csv").stat().st_mtime
sonuc_once = sorted((KOK / "kayit/sonuclar").iterdir())
TAMAM = []


def kontrol(ad, kosul, ayrinti=""):
    TAMAM.append(bool(kosul))
    print(f"[{'GEÇTİ' if kosul else 'KALDI'}] {ad} {ayrinti}")


def yaz(seri, ad):
    yol = VERI / f"{ad}.csv"
    pd.DataFrame({"tarih": seri.index.strftime("%Y-%m-%d"), "deger": seri.values}).to_csv(yol, index=False)
    return yol


# ------------------------------------------------------------- yapay veri üreteci
tarih = pd.date_range("2010-01-01", "2026-10-01", freq="MS")
T, n = len(tarih), 4
A1 = np.array([[0.90, 0.00, 0.00, 0.00],
               [0.00, 0.85, 0.00, -0.05],
               [0.00, 0.20, 0.80, 0.00],
               [0.00, 0.10, 0.10, 0.85]])
Sig = np.array([[1.0, 0.2, 0.1, 0.0], [0.2, 4.0, 1.2, 0.3], [0.1, 1.2, 1.0, 0.1], [0.0, 0.3, 0.1, 0.5]])
rng = np.random.default_rng(5)
g = np.zeros((T + 200, n))  # büyüme oranları (aylık log puan) / AOFM düzeyi farkı
for t in range(1, T + 200):
    g[t] = A1 @ g[t - 1] + np.linalg.cholesky(Sig) @ rng.standard_normal(n)
g = g[200:]
ort = np.array([0.3, 1.5, 1.8, 0.0])          # ortalama aylık büyüme
z = np.cumsum(g + ort, axis=0)                 # 100*log düzeyler (birim kök + sürüklenme)
sue = pd.Series(np.exp((z[:, 0] + 420) / 100), tarih)
usd = pd.Series(np.exp((z[:, 1] + 40) / 100), tarih)
tufe = pd.Series(np.exp((z[:, 2] + 160) / 100), tarih)
aofm = pd.Series(10 + g[:, 3].cumsum() * 0.3 - (g[:, 3].cumsum() * 0.3).mean(), tarih)

kasa = pd.Timestamp("2025-04-01")


def tanim_yaz(ad, yollar, cekilis=500, tufe_donusum=None):
    t = json.loads((KOK / "hipotezler/H-004_bvar.json").read_text())
    for s in t["seriler"]:
        s["yol"] = str(yollar[s["ad"]])
        if tufe_donusum and s["ad"] == "tufe":
            s["donusum"] = tufe_donusum
    t["cekilis"] = cekilis
    yol = VERI / f"{ad}.json"
    yol.write_text(json.dumps(t))
    return yol, t


tam = {"sue": yaz(sue, "sue"), "usdtry": yaz(usd, "usd"), "tufe": yaz(tufe, "tufe"), "aofm": yaz(aofm, "aofm")}
# kasa sonrası değerleri bozulmuş kopya
_orijinal = {"sue": sue, "usdtry": usd, "tufe": tufe, "aofm": aofm}
bozuk = {k: yaz(s.where(s.index < kasa, 1e6), f"{k}_bozuk") for k, s in _orijinal.items()}   # aynı float'tan yazılır
tanim_tam, _ = tanim_yaz("tanim_tam", tam)
tanim_bozuk, _ = tanim_yaz("tanim_bozuk", bozuk)


def ns(**k):
    v = dict(hipotez="TEST", gosterge=None, donusum="logdiff", gosterge_donusum=None, hedef_gecikme=1,
             gosterge_gecikme=0, haric="", kasa=False, model="bvar", bvar_tanim=None)
    v.update(k)
    return argparse.Namespace(**v)


# ------------------------------------------------------------- T1: AR yolu değişmedi
for donusum, h in ([("yoy", 2), ("logdiff", 1)] if eski else []):
    a = ns(model="ar", hedef=str(tam["tufe"]), gosterge=str(tam["usdtry"]), donusum=donusum, hedef_gecikme=h,
           haric="2020-03:2020-06")
    r_eski, r_yeni = eski.calistir(a), yeni.calistir(a)
    kontrol(f"T1 AR yolu eskiyle aynı ({donusum}, h={h})", r_eski == r_yeni, f"rmse_oran={r_yeni['rmse_oran']:.4f}")

# ------------------------------------------------------------- T2: çekirdek matematik
Yt = np.log(np.column_stack([sue, usd, tufe])) * 100
Yt = np.column_stack([Yt, aofm.values])[:170]
Y_, X_ = bv.gecikme_matrisi(Yt, 12)
B_ols = np.linalg.lstsq(X_, Y_, rcond=None)[0]
fark = np.abs(bv.kur(Yt, 12, 1e3, np.ones(4))["B"][:-1] - B_ols[:-1]).max()
kontrol("T2a λ=1000 -> OLS", fark < 1e-3, f"(en büyük fark {fark:.1e})")

rng2 = np.random.default_rng(0)
a_ = 40000
B1 = np.zeros((4 * 2 + 1, 4)); B1[:4] = A1.T; B1[-1] = [0.1, 0.2, 0.3, 0.0]
B_ler = np.repeat(B1[None], a_, 0); S_ler = np.repeat(Sig[None], a_, 0)
gecmis = np.array([[1.0, 2.0, 0.5, -0.3], [0.2, -1.0, 0.4, 0.1]])
gozlenen = np.array([[np.nan, 3.0, np.nan, np.nan]])
yol = bv.kosullu_yollar(B_ler, S_ler, gecmis, gozlenen, rng2)[:, -1]
x = np.concatenate([gecmis[-1], gecmis[-2], [1.0]])
mu = x @ B1
K, U = np.array([False, True, False, False]), np.array([True, False, True, True])
mu_k = mu[U] + Sig[np.ix_(U, K)] @ np.linalg.solve(Sig[np.ix_(K, K)], 3.0 - mu[K])
C_k = Sig[np.ix_(U, U)] - Sig[np.ix_(U, K)] @ np.linalg.solve(Sig[np.ix_(K, K)], Sig[np.ix_(K, U)])
kontrol("T2b koşullu ortalama analitikle aynı", np.abs(yol[:, U].mean(0) - mu_k).max() < 0.03,
        f"(sapma {np.abs(yol[:, U].mean(0) - mu_k).max():.3f})")
kontrol("T2c koşullu kovaryans analitikle aynı", np.abs(np.cov(yol[:, U].T) - C_k).max() < 0.05,
        f"(sapma {np.abs(np.cov(yol[:, U].T) - C_k).max():.3f})")
kontrol("T2d bilinen değer yolda aynen duruyor", np.all(yol[:, 1] == 3.0))

# ------------------------------------------------------------- T3: uçtan uca, bilinen DGP
t0 = time.time()
r3 = yeni.calistir(ns(hedef=str(tam["tufe"]), bvar_tanim=str(tanim_tam)))
sure = time.time() - t0
print(f"    T3: OOS {r3['oos_baslangic']} → {r3['oos_bitis']} n={r3['n_oos']}, RMSE oranı {r3['rmse_oran']:.3f}, "
      f"kapsama %68={r3['kapsama_68']:.2f} %90={r3['kapsama_90']:.2f}, λ medyan {r3['lambda_ozet']['medyan']:.3f}, "
      f"atılan %{100*r3['atilan_cekilis_payi_ort']:.1f}, süre {sure:.0f} sn, PIT {r3['pit_ondalik_sayim']}")
kontrol("T3a OOS kasa öncesinde bitiyor", pd.Timestamp(r3["oos_bitis"]) < kasa)
print("    T3b (bilgi): düzey-VAR'ın AR'ye oranı yukarıda; kalıcı enflasyonlu DGP'de prior yanlış merkezli (tani.py)")
kontrol("T3c %68 kapsama makul (%50-%85)", 0.50 <= r3["kapsama_68"] <= 0.85)
kontrol("T3d %90 kapsama makul (%78-%100)", 0.78 <= r3["kapsama_90"] <= 1.0)

# ------------------------------------------------------------- T4: kasa sızıntısı
r4 = yeni.calistir(ns(hedef=str(bozuk["tufe"]), bvar_tanim=str(tanim_bozuk)))
ayni = all(abs(r3[k] - r4[k]) < 1e-12 for k in ("rmse_model", "rmse_referans", "kapsama_68", "dm_stat"))
kontrol("T4 kasa sonrası veri bozulunca sonuç birebir aynı", ayni)

# ------------------------------------------------------------- T5: bilgi seti sızıntısı (tek ay)
tanim = json.loads(tanim_tam.read_text())
L = {s["ad"]: s["yayin_gecikmesi"] for s in tanim["seriler"]}
Z = pd.DataFrame({"sue": 100 * np.log(sue), "usdtry": 100 * np.log(usd), "tufe": 100 * np.log(tufe), "aofm": aofm})
Z = Z[(Z.index >= "2011-01-01") & (Z.index < kasa)]
izg = np.geomspace(0.01, 10, 25)
for h, don in [(1, "logdiff"), (12, "yoy")]:
    t_ = pd.Timestamp("2022-06-01")
    tau, son = bv.bilgi_seti(t_, h, L, "tufe")
    Zb = Z.copy()
    for ad, s_ in son.items():
        Zb.loc[Zb.index > s_, ad] = Zb.loc[Zb.index > s_, ad] + 500.0     # bilinmemesi gereken her şeyi boz
    c1, d1 = bv.hedef_cekilisleri(Z, "tufe", "log", don, t_, h, L, 12, np.ones(4), 1.0, izg, 300, 1.02, np.random.default_rng(1))
    c2, _ = bv.hedef_cekilisleri(Zb, "tufe", "log", don, t_, h, L, 12, np.ones(4), 1.0, izg, 300, 1.02, np.random.default_rng(1))
    kontrol(f"T5a h={h}: bilinmeyen değerleri bozmak sonucu değiştirmiyor", np.array_equal(c1, c2),
            f"(τ={tau:%Y-%m}, dengeli uç {d1['dengeli_son']:%Y-%m}, {d1['adim']} adım; "
            f"bilinen son: {', '.join(f'{k} {v:%Y-%m}' for k, v in son.items())})")
    Zk = Z.copy()
    Zk.loc[son["usdtry"], "usdtry"] += 30.0                                # bilinen bir değeri değiştir
    c3, _ = bv.hedef_cekilisleri(Zk, "tufe", "log", don, t_, h, L, 12, np.ones(4), 1.0, izg, 300, 1.02, np.random.default_rng(1))
    kontrol(f"T5b h={h}: bilinen son kur değeri tahmini etkiliyor", abs(c3.mean() - c1.mean()) > 1e-3,
            f"(ortalama {c1.mean():.3f} -> {c3.mean():.3f})")

# ------------------------------------------------------------- T6: ikincil ayar (yoy, h=12)
tanim_az, _ = tanim_yaz("tanim_az", tam, cekilis=200)
r6 = yeni.calistir(ns(hedef=str(tam["tufe"]), bvar_tanim=str(tanim_az), donusum="yoy", hedef_gecikme=12))
kontrol("T6 yoy h=12 çalışıyor", r6["n_oos"] >= 12 and all(x["adim"] == 13 for x in r6["tablo"]),
        f"(n={r6['n_oos']}, RMSE oranı {r6['rmse_oran']:.3f}, kapsama %90={r6['kapsama_90']:.2f})")

# ------------------------------------------------------------- T7: TÜFE VAR'da aylık log fark
tanim_fark, _ = tanim_yaz("tanim_fark", tam, tufe_donusum="logdiff")
r7 = yeni.calistir(ns(hedef=str(tam["tufe"]), bvar_tanim=str(tanim_fark)))
print(f"    T7: RMSE oranı {r7['rmse_oran']:.3f}, kapsama %68={r7['kapsama_68']:.2f} %90={r7['kapsama_90']:.2f}, "
      f"λ medyan {r7['lambda_ozet']['medyan']:.3f}, PIT {r7['pit_ondalik_sayim']}")
kontrol("T7a logdiff VAR: BVAR AR'yi geçiyor", r7["rmse_oran"] < 0.95)
kontrol("T7b logdiff VAR: %90 kapsama makul (%78-%100)", 0.78 <= r7["kapsama_90"] <= 1.0)
# logdiff VAR ile hedef logdiff: tek ay tahmini, düzey VAR yolundan bağımsız hesap
tanim_fark_az, _ = tanim_yaz("tanim_fark_az", tam, cekilis=200, tufe_donusum="logdiff")
r8 = yeni.calistir(ns(hedef=str(tam["tufe"]), bvar_tanim=str(tanim_fark_az), donusum="yoy", hedef_gecikme=12))
kontrol("T8 logdiff VAR, yoy h=12 çalışıyor", r8["n_oos"] >= 12,
        f"(RMSE oranı {r8['rmse_oran']:.3f}, kapsama %68={r8['kapsama_68']:.2f} %90={r8['kapsama_90']:.2f})")
r8b = yeni.calistir(ns(hedef=str(bozuk["tufe"]), bvar_tanim=str(tanim_yaz("tanim_fark_bozuk", bozuk, cekilis=200, tufe_donusum="logdiff")[0]),
                       donusum="yoy", hedef_gecikme=12))
kontrol("T8b logdiff VAR: kasa sonrası bozulunca sonuç aynı", abs(r8["rmse_model"] - r8b["rmse_model"]) < 1e-12)

# ------------------------------------------------------------- kayıtlara dokunulmadı
kontrol("Kayıt: denemeler.csv değişmedi", (KOK / "kayit/denemeler.csv").stat().st_mtime == gunluk_once)
kontrol("Kayıt: sonuclar klasörü değişmedi", sorted((KOK / "kayit/sonuclar").iterdir()) == sonuc_once)
print(f"\n{sum(TAMAM)}/{len(TAMAM)} kontrol geçti")
