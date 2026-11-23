"""Tek yetkili test motoru: bir göstergenin hedef seriyi gerçek zamanlı
tahmin (nowcast) etmeye katkı sağlayıp sağlamadığını ölçer.

Karşılaştırma:
    referans: y_t = a + b * y_(t-h)
    model:    y_t = a + b * y_(t-h) + c * x_(t-g)

h = hedef serinin yayın gecikmesi (tahmin anında bilinen son değer),
g = gösterge gecikmesi (0 = aynı ayın göstergesi tahmin anında hazır).

Örneklem dışı değerlendirme genişleyen pencereyle yapılır ve her adımda
eğitim verisi yalnızca o anda yayımlanmış olabilecek gözlemleri içerir.

Her çalıştırma kayit/denemeler.csv dosyasına eklenir (başarısız olsa bile),
böylece toplam deneme sayısı dürüst kalır.

Kullanım:
    python src/analiz/test_et.py --hipotez H-001 \
        --hedef data/islenmis/hedef.csv --gosterge data/islenmis/gosterge.csv \
        --donusum yoy --hedef-gecikme 2 [--gosterge-gecikme 0] \
        [--haric 2020-03:2020-06,2023-02:2023-03] [--kasa]

Birden fazla gösterge (köprü regresyonu, 2026-11-07'de H-007 için eklendi):
    --gosterge a.csv,b.csv,c.csv  ->  y_t = a + b * y_(t-h) + c1 * x1_(t-g) + c2 * x2_(t-g) + ...
    Hepsi aynı --gosterge-donusum ve --gosterge-gecikme'yi alır. Tek göstergede davranış değişmez.

BVAR modu (--model bvar, 2026-11-06'da H-004 için eklendi):
    referans: aynı AR referansı (y_t = a + b * y_(t-h))
    model:    Minnesota BVAR (src/analiz/bvar.py); değişkenler, yayın gecikmeleri ve
              prior ayarları --bvar-tanim JSON dosyasında, test öncesi sabitlenir.
    Her örneklem dışı ayda λ yalnızca o anda bilinen veriyle seçilir; her seri kendi
    yayın gecikmesine göre maskelenir (düzensiz uç, Σ'ya göre koşullu simülasyon).
    Nokta tahmin = tahmin dağılımının ortalaması. Ek çıktı: %68/%90 bant kapsaması, PIT.
    Tanımda "sv" alanı varsa ortak stokastik oynaklık kullanılır (bvar.sv_cekilisleri,
    2026-11-07'de H-006 için eklendi); yoksa davranış H-004'teki gibidir.
    --haric BVAR modunda ayları değerlendirmeden ve AR eğitiminden çıkarır; VAR
    tahminine bütün aylar girer. Günlük sütunları aynıdır (gosterge = "BVAR:<tanım>").

    python src/analiz/test_et.py --hipotez H-004 --model bvar \
        --bvar-tanim hipotezler/H-004_bvar.json \
        --hedef data/islenmis/tcmb_tufema_turkiye_aylik.csv --donusum logdiff --hedef-gecikme 1
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[2]
AYARLAR = KOK / "ayarlar.json"
GUNLUK = KOK / "kayit" / "denemeler.csv"
SONUCLAR = KOK / "kayit" / "sonuclar"
KASA_BAYRAK = KOK / ".kasa_acik"

GUNLUK_SUTUNLAR = [
    "zaman", "hipotez", "hedef", "gosterge", "donusum", "hedef_gecikme",
    "gosterge_gecikme", "haric", "kasa_modu", "durum", "n_oos", "oos_baslangic",
    "oos_bitis", "rmse_referans", "rmse_model", "rmse_oran", "dm_stat", "dm_p",
    "yon_isabet_model", "yon_isabet_referans", "toplam_deneme", "duzeltilmis_esik",
]


# ---------------------------------------------------------------- yardımcılar
def seri_oku(yol: str) -> pd.Series:
    df = pd.read_csv(yol)
    eksik = {"tarih", "deger"} - set(df.columns)
    if eksik:
        raise ValueError(f"{yol}: eksik sütun(lar) {eksik}; beklenen 'tarih,deger'")
    df["tarih"] = pd.to_datetime(df["tarih"])
    s = df.set_index("tarih")["deger"].astype(float).sort_index()
    return s.resample("MS").mean()


def donustur(s: pd.Series, donusum: str) -> pd.Series:
    if donusum == "duzey":
        return s
    if (s.dropna() <= 0).any():
        raise ValueError(f"'{donusum}' dönüşümü pozitif değer ister; seride <= 0 değer var")
    if donusum == "yoy":
        return 100 * (s / s.shift(12) - 1)
    if donusum == "logdiff":
        return 100 * np.log(s).diff()
    raise ValueError(f"bilinmeyen dönüşüm: {donusum}")


def haric_maske(index: pd.DatetimeIndex, haric: str) -> np.ndarray:
    maske = np.zeros(len(index), dtype=bool)
    if not haric:
        return maske
    for parca in haric.split(","):
        bas, _, bit = parca.strip().partition(":")
        bas_t = pd.Timestamp(bas)
        bit_t = pd.Timestamp(bit or bas) + pd.offsets.MonthEnd(0)
        maske |= (index >= bas_t) & (index <= bit_t)
    return maske


def ols_tahmin(X_egitim, y_egitim, X_yeni) -> float:
    beta, *_ = np.linalg.lstsq(X_egitim, y_egitim, rcond=None)
    return float(X_yeni @ beta)


def normal_cdf(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def diebold_mariano(e_model: np.ndarray, e_ref: np.ndarray, h: int) -> tuple[float, float]:
    """Kare kayıp, Newey-West varyans (h-1 gecikme), Harvey-Leybourne-Newbold
    küçük örneklem düzeltmesi. Tek yönlü p: model referanstan iyi mi?"""
    d = e_model ** 2 - e_ref ** 2
    n = len(d)
    d_ort = d.mean()
    gamma0 = np.mean((d - d_ort) ** 2)
    var = gamma0
    for k in range(1, max(h, 1)):
        if k >= n:
            break
        gk = np.mean((d[k:] - d_ort) * (d[:-k] - d_ort))
        var += 2 * (1 - k / max(h, 1)) * gk
    if var <= 0:
        return float("nan"), float("nan")
    dm = d_ort / math.sqrt(var / n)
    hln = math.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n) if n > 2 * h else 1.0
    dm *= hln
    return dm, normal_cdf(dm)  # negatif dm = model daha iyi


def gunluk_yaz(satir: dict) -> int:
    GUNLUK.parent.mkdir(parents=True, exist_ok=True)
    yeni = not GUNLUK.exists() or GUNLUK.stat().st_size == 0
    onceki = 0
    if not yeni:
        with open(GUNLUK, newline="", encoding="utf-8") as f:
            onceki = sum(1 for _ in csv.DictReader(f))
    satir["toplam_deneme"] = onceki + 1
    with open(GUNLUK, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=GUNLUK_SUTUNLAR)
        if yeni:
            w.writeheader()
        w.writerow({k: satir.get(k, "") for k in GUNLUK_SUTUNLAR})
    return onceki + 1


def yuvarla(x, n=4):
    return "" if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), n)


# ---------------------------------------------------------------- ana akış
def calistir(a: argparse.Namespace) -> dict:
    if getattr(a, "model", "ar") == "bvar":
        return calistir_bvar(a)
    ayar = json.loads(AYARLAR.read_text(encoding="utf-8"))
    kasa_bas = pd.Timestamp(ayar["kasa_baslangic"])
    oran = float(ayar.get("ornek_disi_oran", 0.4))
    alfa = float(ayar.get("anlamlilik", 0.05))
    h, g = a.hedef_gecikme, a.gosterge_gecikme

    if a.kasa and not KASA_BAYRAK.exists():
        raise PermissionError("Kasa kapalı. İnsanın proje kökünde .kasa_acik dosyası oluşturması gerekir.")

    y = donustur(seri_oku(a.hedef), a.donusum)
    # Birden fazla gösterge virgülle verilebilir (köprü regresyonu); hepsi aynı dönüşüm ve gecikmeyi alır.
    yollar = [s.strip() for s in a.gosterge.split(",") if s.strip()]
    xler = [donustur(seri_oku(yol), a.gosterge_donusum or a.donusum) for yol in yollar]
    x = xler[0]
    xsut = [f"x{j}" for j in range(len(xler))]

    df = pd.DataFrame({"y": y, "y_gec": y.shift(h), **{c: xs.shift(g) for c, xs in zip(xsut, xler)}}).dropna()
    df = df[~haric_maske(df.index, a.haric)]

    if a.kasa:
        tum = df
        oos_idx = [i for i, t in enumerate(tum.index) if t >= kasa_bas]
    else:
        tum = df[df.index < kasa_bas]
        n = len(tum)
        bas = int(round(n * (1 - oran)))
        oos_idx = list(range(bas, n))

    if len(tum) < 36 or len(oos_idx) < 12:
        raise ValueError(f"Yetersiz gözlem: toplam {len(tum)}, örneklem dışı {len(oos_idx)} "
                         "(en az 36 ve 12 gerekir)")

    X_ref = np.column_stack([np.ones(len(tum)), tum["y_gec"].values])
    X_mod = np.column_stack([X_ref] + [tum[c].values for c in xsut])
    yv = tum["y"].values

    tahmin_ref, tahmin_mod, gercek, son_bilinen, tarihler = [], [], [], [], []
    for i in oos_idx:
        t = tum.index[i]
        egitim = tum.index <= t - pd.DateOffset(months=h)  # o anda yayımlanmış hedefler
        if egitim.sum() < 24:
            continue
        tahmin_ref.append(ols_tahmin(X_ref[egitim], yv[egitim], X_ref[i]))
        tahmin_mod.append(ols_tahmin(X_mod[egitim], yv[egitim], X_mod[i]))
        gercek.append(yv[i])
        son_bilinen.append(tum["y_gec"].values[i])
        tarihler.append(t)

    gercek = np.array(gercek)
    e_ref = gercek - np.array(tahmin_ref)
    e_mod = gercek - np.array(tahmin_mod)
    rmse_ref = float(np.sqrt(np.mean(e_ref ** 2)))
    rmse_mod = float(np.sqrt(np.mean(e_mod ** 2)))
    dm, dm_p = diebold_mariano(e_mod, e_ref, h)
    yon = np.sign(gercek - np.array(son_bilinen))
    yon_mod = float(np.mean(np.sign(np.array(tahmin_mod) - son_bilinen) == yon))
    yon_ref = float(np.mean(np.sign(np.array(tahmin_ref) - son_bilinen) == yon))

    # Bilgi amaçlı: eğitim döneminde gösterge-hedef öncülük korelasyonları
    egitim_son = tarihler[0] - pd.DateOffset(months=1)
    oncu = {}
    for j, xj in enumerate(xler):
        yx = pd.DataFrame({"y": y, "x": xj}).dropna().loc[:egitim_son]
        ek = "" if len(xler) == 1 else f"{j}"
        oncu.update({f"x{ek}(t{-k:+d})": yuvarla(yx["y"].corr(yx["x"].shift(k)), 3) for k in range(-3, 4)})

    return {
        "durum": "tamamlandi", "n_oos": len(gercek),
        "oos_baslangic": str(tarihler[0].date()), "oos_bitis": str(tarihler[-1].date()),
        "rmse_referans": rmse_ref, "rmse_model": rmse_mod, "rmse_oran": rmse_mod / rmse_ref,
        "dm_stat": dm, "dm_p": dm_p, "yon_isabet_model": yon_mod, "yon_isabet_referans": yon_ref,
        "oncu_korelasyon_egitim": oncu, "alfa": alfa,
    }


def calistir_bvar(a: argparse.Namespace) -> dict:
    """BVAR modeli, AR referansına karşı. Ayrıntı: modül belgesi ve src/analiz/bvar.py."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import bvar as bv

    ayar = json.loads(AYARLAR.read_text(encoding="utf-8"))
    kasa_bas = pd.Timestamp(ayar["kasa_baslangic"])
    oran = float(ayar.get("ornek_disi_oran", 0.4))
    alfa = float(ayar.get("anlamlilik", 0.05))
    h = a.hedef_gecikme

    if a.kasa and not KASA_BAYRAK.exists():
        raise PermissionError("Kasa kapalı. İnsanın proje kökünde .kasa_acik dosyası oluşturması gerekir.")
    if not a.bvar_tanim:
        raise ValueError("--model bvar için --bvar-tanim gerekir")

    tanim = json.loads(Path(a.bvar_tanim).read_text(encoding="utf-8"))
    seriler = tanim["seriler"]
    hedef_ad = tanim["hedef"]
    hs = next((s for s in seriler if s["ad"] == hedef_ad), None)
    if hs is None:
        raise ValueError(f"tanımda hedef serisi yok: {hedef_ad}")
    if (KOK / hs["yol"]).resolve() != Path(a.hedef).resolve():
        raise ValueError(f"--hedef, tanımdaki hedef serisiyle aynı dosya olmalı ({hs['yol']})")
    L = {s["ad"]: int(s["yayin_gecikmesi"]) for s in seriler}
    p = int(tanim["gecikme"])
    delta = np.array([float(s.get("delta", tanim["delta"])) for s in seriler])   # seri bazında δ olabilir
    d = float(tanim["sonum"])
    iz = tanim["lambda_izgara"]
    izgara = np.geomspace(float(iz["min"]), float(iz["max"]), int(iz["adet"]))
    adet, kok_siniri = int(tanim["cekilis"]), float(tanim["kok_siniri"])

    # VAR verisi (VAR dönüşümüyle); kasa kapalıysa kasa öncesinde kesilir
    sutunlar = {}
    for s in seriler:
        z = seri_oku(str(KOK / s["yol"]))
        if s["donusum"] == "log":
            if (z.dropna() <= 0).any():
                raise ValueError(f"{s['ad']}: log dönüşümü pozitif değer ister")
            z = 100 * np.log(z)
        elif s["donusum"] == "logdiff":
            if (z.dropna() <= 0).any():
                raise ValueError(f"{s['ad']}: logdiff dönüşümü pozitif değer ister")
            z = 100 * np.log(z).diff()
        elif s["donusum"] != "duzey":
            raise ValueError(f"{s['ad']}: bilinmeyen VAR dönüşümü {s['donusum']}")
        sutunlar[s["ad"]] = z
    Z = pd.DataFrame(sutunlar)
    Z = Z[Z.index >= pd.Timestamp(tanim["baslangic"])]
    Z = Z.loc[Z.dropna().index[0]:]          # bütün serilerin başladığı ilk ay
    if not a.kasa:
        Z = Z[Z.index < kasa_bas]
    Z = Z.reindex(pd.date_range(Z.index.min(), Z.index.max(), freq="MS"))

    seviye = seri_oku(a.hedef)
    if not a.kasa:
        seviye = seviye[seviye.index < kasa_bas]
    y = donustur(seviye, a.donusum)
    df = pd.DataFrame({"y": y, "y_gec": y.shift(h)}).dropna()
    df = df[df.index >= Z.index[0] + pd.DateOffset(months=p)]   # AR ile BVAR aynı pencere
    df = df[~haric_maske(df.index, a.haric)]

    if a.kasa:
        tum = df
        oos_idx = [i for i, t in enumerate(tum.index) if t >= kasa_bas]
    else:
        tum = df[df.index < kasa_bas]
        n = len(tum)
        oos_idx = list(range(int(round(n * (1 - oran))), n))
    if len(tum) < 36 or len(oos_idx) < 12:
        raise ValueError(f"Yetersiz gözlem: toplam {len(tum)}, örneklem dışı {len(oos_idx)} "
                         "(en az 36 ve 12 gerekir)")

    X_ref = np.column_stack([np.ones(len(tum)), tum["y_gec"].values])
    yv = tum["y"].values
    rng = np.random.default_rng(int(tanim["tohum"]))

    tablo = []
    for i in oos_idx:
        t = tum.index[i]
        egitim = tum.index <= t - pd.DateOffset(months=h)
        if egitim.sum() < 24:
            continue
        ref = ols_tahmin(X_ref[egitim], yv[egitim], X_ref[i])
        cek, tani = bv.hedef_cekilisleri(Z, hedef_ad, hs["donusum"], a.donusum, t, h, L, p, delta, d,
                                         izgara, adet, kok_siniri, rng, sv=tanim.get("sv"))
        q05, q16, q84, q95 = np.percentile(cek, [5, 16, 84, 95])
        tablo.append({"tarih": t, "gercek": yv[i], "son_bilinen": tum["y_gec"].values[i],
                      "ar": ref, "bvar": float(cek.mean()), "q05": q05, "q16": q16, "q84": q84, "q95": q95,
                      "pit": float(np.mean(cek <= yv[i])), "lambda": tani["lambda"],
                      "atilan_pay": tani["atilan_pay"], "adim": tani["adim"], "sv_son": tani["sv_son"]})

    tb = pd.DataFrame(tablo)
    gercek = tb["gercek"].values
    e_ref = gercek - tb["ar"].values
    e_mod = gercek - tb["bvar"].values
    rmse_ref = float(np.sqrt(np.mean(e_ref ** 2)))
    rmse_mod = float(np.sqrt(np.mean(e_mod ** 2)))
    dm, dm_p = diebold_mariano(e_mod, e_ref, h)
    son = tb["son_bilinen"].values
    yon = np.sign(gercek - son)
    yon_mod = float(np.mean(np.sign(tb["bvar"].values - son) == yon))
    yon_ref = float(np.mean(np.sign(tb["ar"].values - son) == yon))
    kap68 = float(np.mean((gercek >= tb["q16"]) & (gercek <= tb["q84"])))
    kap90 = float(np.mean((gercek >= tb["q05"]) & (gercek <= tb["q95"])))
    pit_sayim = np.histogram(tb["pit"].values, bins=10, range=(0, 1))[0].tolist()

    return {
        "durum": "tamamlandi", "model": "bvar", "n_oos": len(tb),
        "oos_baslangic": str(tb["tarih"].iloc[0].date()), "oos_bitis": str(tb["tarih"].iloc[-1].date()),
        "rmse_referans": rmse_ref, "rmse_model": rmse_mod, "rmse_oran": rmse_mod / rmse_ref,
        "dm_stat": dm, "dm_p": dm_p, "yon_isabet_model": yon_mod, "yon_isabet_referans": yon_ref,
        "kapsama_68": kap68, "kapsama_90": kap90, "pit_ondalik_sayim": pit_sayim,
        "lambda_ozet": {"min": float(tb["lambda"].min()), "medyan": float(tb["lambda"].median()),
                        "max": float(tb["lambda"].max())},
        "atilan_cekilis_payi_ort": float(tb["atilan_pay"].mean()),
        "bvar_tanim": tanim, "tablo": tb.assign(tarih=tb["tarih"].dt.strftime("%Y-%m-%d")).to_dict("records"),
        "oncu_korelasyon_egitim": {}, "alfa": alfa,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Öncü gösterge nowcast testi")
    p.add_argument("--hipotez", required=True)
    p.add_argument("--hedef", required=True)
    p.add_argument("--gosterge", default=None, help="--model ar için zorunlu")
    p.add_argument("--donusum", choices=["yoy", "logdiff", "duzey"], default="yoy")
    p.add_argument("--gosterge-donusum", choices=["yoy", "logdiff", "duzey"], default=None)
    p.add_argument("--hedef-gecikme", type=int, default=2)
    p.add_argument("--gosterge-gecikme", type=int, default=0)
    p.add_argument("--haric", default="")
    p.add_argument("--kasa", action="store_true")
    p.add_argument("--model", choices=["ar", "bvar"], default="ar",
                   help="ar: AR + gösterge, AR'ye karşı (varsayılan). bvar: Minnesota BVAR, AR'ye karşı")
    p.add_argument("--bvar-tanim", default=None, help="BVAR tanım dosyası (JSON); --model bvar için zorunlu")
    a = p.parse_args()
    if a.model == "ar" and not a.gosterge:
        p.error("--model ar için --gosterge gerekir")
    if a.model == "bvar" and not a.bvar_tanim:
        p.error("--model bvar için --bvar-tanim gerekir")
    bvar_modu = a.model == "bvar"

    satir = {
        "zaman": datetime.now().isoformat(timespec="seconds"), "hipotez": a.hipotez,
        "hedef": a.hedef, "gosterge": f"BVAR:{a.bvar_tanim}" if bvar_modu else a.gosterge,
        "donusum": a.donusum + (f"/{a.gosterge_donusum}" if a.gosterge_donusum else ""),
        "hedef_gecikme": a.hedef_gecikme, "gosterge_gecikme": "" if bvar_modu else a.gosterge_gecikme,
        "haric": a.haric, "kasa_modu": a.kasa,
    }
    try:
        sonuc = calistir(a)
    except Exception as hata:  # başarısız denemeler de sayılır
        satir["durum"] = f"hata: {hata}"
        toplam = gunluk_yaz(satir)
        print(f"HATA: {hata}\n(Deneme #{toplam} olarak kaydedildi.)", file=sys.stderr)
        sys.exit(1)

    for k in ("n_oos", "oos_baslangic", "oos_bitis", "durum"):
        satir[k] = sonuc[k]
    for k in ("rmse_referans", "rmse_model", "rmse_oran", "dm_stat", "dm_p",
              "yon_isabet_model", "yon_isabet_referans"):
        satir[k] = yuvarla(sonuc[k])
    toplam = gunluk_yaz({**satir, "duzeltilmis_esik": ""})
    esik = sonuc["alfa"] / toplam
    # eşiği de günlüğe yansıt (son satırı güncelle)
    with open(GUNLUK, newline="", encoding="utf-8") as f:
        satirlar = list(csv.DictReader(f))
    satirlar[-1]["duzeltilmis_esik"] = f"{esik:.2e}"
    with open(GUNLUK, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=GUNLUK_SUTUNLAR)
        w.writeheader()
        w.writerows(satirlar)

    SONUCLAR.mkdir(parents=True, exist_ok=True)
    damga = datetime.now().strftime("%Y%m%d-%H%M%S")
    (SONUCLAR / f"{a.hipotez}_{damga}.json").write_text(
        json.dumps({**satir, **sonuc, "toplam_deneme": toplam, "duzeltilmis_esik": esik},
                   ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    if a.kasa:
        KASA_BAYRAK.unlink(missing_ok=True)  # kasa tek kullanımlık

    dm_p = sonuc["dm_p"]
    if bvar_modu:
        lo = sonuc["lambda_ozet"]
        print(f"""
=== {a.hipotez} [BVAR] {'[KASA DOĞRULAMASI]' if a.kasa else ''}
Örneklem dışı dönem : {sonuc['oos_baslangic']} → {sonuc['oos_bitis']} ({sonuc['n_oos']} gözlem)
RMSE referans (AR)  : {sonuc['rmse_referans']:.3f}
RMSE model (BVAR)   : {sonuc['rmse_model']:.3f}
RMSE oranı          : {sonuc['rmse_oran']:.3f}   (< 1 ise BVAR referanstan iyi)
Yön isabeti         : model %{100*sonuc['yon_isabet_model']:.0f} | referans %{100*sonuc['yon_isabet_referans']:.0f}
DM testi            : stat {sonuc['dm_stat']:.2f}, tek yönlü p = {dm_p:.4f}
Toplam deneme       : {toplam}  → düzeltilmiş eşik (Bonferroni) = {esik:.2e}
Düzeltilmiş eşikte anlamlı mı: {'EVET' if dm_p < esik else 'HAYIR'}
Bant kapsaması      : %68 bant %{100*sonuc['kapsama_68']:.0f} | %90 bant %{100*sonuc['kapsama_90']:.0f}
PIT ondalık sayımı  : {sonuc['pit_ondalik_sayim']}   (iyi kalibrasyonda kabaca eşit)
Seçilen λ           : min {lo['min']:.3f} | medyan {lo['medyan']:.3f} | max {lo['max']:.3f}
Atılan çekiliş payı : %{100*sonuc['atilan_cekilis_payi_ort']:.1f} (ortalama)
Ay ay tahminler     : kayit/sonuclar/{a.hipotez}_{damga}.json ("tablo")
""".rstrip())
        return
    print(f"""
=== {a.hipotez} {'[KASA DOĞRULAMASI]' if a.kasa else ''}
Örneklem dışı dönem : {sonuc['oos_baslangic']} → {sonuc['oos_bitis']} ({sonuc['n_oos']} gözlem)
RMSE referans (AR)  : {sonuc['rmse_referans']:.3f}
RMSE model (+gösterge): {sonuc['rmse_model']:.3f}
RMSE oranı          : {sonuc['rmse_oran']:.3f}   (< 1 ise gösterge katkı sağlıyor)
Yön isabeti         : model %{100*sonuc['yon_isabet_model']:.0f} | referans %{100*sonuc['yon_isabet_referans']:.0f}
DM testi            : stat {sonuc['dm_stat']:.2f}, tek yönlü p = {dm_p:.4f}
Toplam deneme       : {toplam}  → düzeltilmiş eşik (Bonferroni) = {esik:.2e}
Düzeltilmiş eşikte anlamlı mı: {'EVET' if dm_p < esik else 'HAYIR'}
Eğitim dönemi öncülük korelasyonları (y_t ile x'in kaydırılmış hali):
  {sonuc['oncu_korelasyon_egitim']}
""".rstrip())


if __name__ == "__main__":
    main()
