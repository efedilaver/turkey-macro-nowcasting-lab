"""H-004 (BVAR kiyas modeli) icin dort aylik seri: EVDS3 -> data/ham + data/islenmis.

Ne yapar
    1. EVDS3'ten dort seriyi indirir, yanitlarin aynisini data/ham/evds_bvar/ altina
       tarih damgasiyla yazar (+ KAYNAK.txt).
         TP.TUKFIYARND.OKTG01  TUFE genel, mevsim etkisinden arindirilmis (2025=100), aylik
         TP.TSANAYMT2021.BCD   SUE toplam sanayi, mevsim ve takvim etkisinden arindirilmis (2021=100), aylik
         TP.DK.USD.A.YTL       USD/TRY doviz alis, gunluk -> EVDS aylik ortalama (frequency=5, avg)
         TP.APIFON4            TCMB agirlikli ortalama fonlama maliyeti (%), is gunu -> EVDS aylik ortalama
    2. Her seriyi tarih,deger (ayin ilk gunu) olarak data/islenmis/ altina yazar.
    3. Dogrulamalar: ay eksigi yok, deger pozitif, tarih tekil.

Kasa: Bu betik seriyi bugune kadar indirir (diger veri betikleri gibi). Kasa kesimini
test motoru yapar. Betik kasa donemine ait hicbir degeri ekrana yazdirmaz.

Kullanim:  python src/veri/tcmb_bvar_seriler.py
Anahtar .env icinde EVDS_API_KEY olarak durur; yazdirilmaz.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evds3_istemci as ev  # noqa: E402

KOK = ev.KOK
HAM = KOK / "data" / "ham" / "evds_bvar"
ISLENMIS = KOK / "data" / "islenmis"

# ad: (kod, baslangic dd-mm-yyyy, aylik ortalama gerekiyor mu, cikti dosyasi)
SERILER = {
    "tufema": ("TP.TUKFIYARND.OKTG01", "01-01-2005", False, "tcmb_tufema_turkiye_aylik.csv"),
    "suema":  ("TP.TSANAYMT2021.BCD",  "01-01-2005", False, "tuik_suema_turkiye_aylik.csv"),
    "usdtry": ("TP.DK.USD.A.YTL",      "01-01-2005", True,  "tcmb_usdtry_turkiye_aylik.csv"),
    "aofm":   ("TP.APIFON4",           "01-01-2011", True,  "tcmb_aofm_turkiye_aylik.csv"),
}

KAYNAK_METNI = """Kaynak: TCMB EVDS3 (https://evds3.tcmb.gov.tr), indiren: src/veri/tcmb_bvar_seriler.py
Dosyalar API yanitinin aynisidir: <SERI_KODU>_<YYYYMMDD>.json (indirme tarihi).
TP.TUKFIYARND.OKTG01  veri grubu bie_tukfiyarnd   TUFE genel (MA), 2025=100, aylik; revize edilir (mevsim faktorleri)
TP.TSANAYMT2021.BCD   veri grubu bie_tsanaymt2021 SUE toplam sanayi (mevsim+takvim arindirilmis), 2021=100; revize edilir
TP.DK.USD.A.YTL       veri grubu bie_dkdovytl     USD doviz alis; istek frequency=5&aggregationTypes=avg (aylik ortalama)
TP.APIFON4            veri grubu bie_apifon       TCMB AOFM (%); istek frequency=5&aggregationTypes=avg (aylik ortalama)
"""


def indir(kod: str, bas: str, aylik_ort: bool, damga: str) -> pd.Series:
    ek = "&frequency=5&aggregationTypes=avg" if aylik_ort else ""
    yanit = ev._al(f"series={kod}&startDate={bas}&endDate={ev.bugun_str()}&type=json{ek}").json()
    (HAM / f"{kod}_{damga}.json").write_text(json.dumps(yanit, ensure_ascii=False), encoding="utf-8")
    return ev.ham_to_seri(yanit, kod, "A")


def dogrula(ad: str, s: pd.Series) -> pd.Series:
    s = s.dropna()
    tam = pd.date_range(s.index.min(), s.index.max(), freq="MS")
    eksik = tam.difference(s.index)
    if len(eksik):
        raise SystemExit(f"{ad}: eksik ay var: {[t.strftime('%Y-%m') for t in eksik[:5]]}")
    if (s <= 0).any():
        raise SystemExit(f"{ad}: pozitif olmayan deger var")
    return s


def main() -> None:
    HAM.mkdir(parents=True, exist_ok=True)
    ISLENMIS.mkdir(parents=True, exist_ok=True)
    (HAM / "KAYNAK.txt").write_text(KAYNAK_METNI, encoding="utf-8")
    damga = date.today().strftime("%Y%m%d")
    bu_ay = pd.Timestamp(date.today().replace(day=1))
    for ad, (kod, bas, aylik_ort, dosya) in SERILER.items():
        s = indir(kod, bas, aylik_ort, damga)
        if aylik_ort:
            s = s[s.index < bu_ay]  # icinde bulunulan ay eksik: ortalamasi henuz tam degil
        s = dogrula(ad, s)
        df = pd.DataFrame({"tarih": s.index.strftime("%Y-%m-%d"), "deger": s.values})
        df.to_csv(ISLENMIS / dosya, index=False, float_format="%.6f")
        # Yalnizca tarih araligi ve gozlem sayisi yazdirilir (kasa degerleri gosterilmez)
        print(f"{ad:7s} {kod:22s} {s.index.min():%Y-%m} .. {s.index.max():%Y-%m}  n={len(s):3d}  -> data/islenmis/{dosya}")


if __name__ == "__main__":
    main()
