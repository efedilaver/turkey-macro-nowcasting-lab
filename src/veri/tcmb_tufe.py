"""TUFE genel endeksi (TCMB EVDS3 uzerinden TUIK): eski ve yeni baz zincirleme.

Ne yapar
    1. EVDS3'ten iki seriyi indirir ve ham JSON olarak data/ham/tcmb_tufe/ altina yazar:
         TP.FG.J0              TUFE genel, 2003=100 (veri grubu bie_tukfiy4, "Arsiv"; Ocak 2026'ya kadar)
         TP.TUKFIY2025.GENEL   TUFE genel, 2025=100 (veri grubu bie_tukfiy2025; 2005-01'den geriye uzanir)
    2. Zincirleme: BAGLAMA_AYI (2025-12) ve oncesi icin eski seri aynen; sonrasi icin
       yeni seri x k, k = eski(2025-12) / yeni(2025-12). Sonuc 2003=100 olcegindedir.
    3. Dogrulamalar: iki seri ortusen donemde (2005-01..2025-12) sabit oranli mi,
       Ocak 2026'da eski yayinla zincir uyusuyor mu, ay eksigi var mi.
    4. data/islenmis/tcmb_tufe_turkiye_aylik.csv (tarih,deger; ayin ilk gunu) yazar.

Kullanim:  python src/veri/tcmb_tufe.py
Anahtar .env icinde EVDS_API_KEY olarak durur; yazdirilmaz.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evds3_istemci as ev  # noqa: E402

KOK = ev.KOK
HAM = KOK / "data" / "ham" / "tcmb_tufe"
CIKTI = KOK / "data" / "islenmis" / "tcmb_tufe_turkiye_aylik.csv"

ESKI = "TP.FG.J0"
YENI = "TP.TUKFIY2025.GENEL"
BAGLAMA_AYI = pd.Timestamp("2025-12-01")
ORTUSME_TOLERANS = 2e-4  # esas olarak eski endeksin 2 ondalik yuvarlamasi (~4e-5)


def indir() -> dict:
    HAM.mkdir(parents=True, exist_ok=True)
    damga = date.today().strftime("%Y%m%d")
    yanit = {}
    for kod, bas in ((ESKI, "01-01-2003"), (YENI, "01-01-2005")):
        y = ev.seri_ham(kod, bas)
        yanit[kod] = y
        (HAM / f"{kod}_{damga}.json").write_text(json.dumps(y, ensure_ascii=False), encoding="utf-8")
    return yanit


def zincirle(eski: pd.Series, yeni: pd.Series) -> tuple[pd.Series, dict]:
    for ad, s in (("eski", eski), ("yeni", yeni)):
        tam = pd.date_range(s.index.min(), s.index.max(), freq="MS")
        if len(tam.difference(s.dropna().index)) > 0:
            raise SystemExit(f"{ad} TUFE serisinde eksik ay var: {list(tam.difference(s.dropna().index))[:5]}")
    if BAGLAMA_AYI not in eski.index or BAGLAMA_AYI not in yeni.index:
        raise SystemExit("baglama ayi iki seride de bulunmali")
    k = eski[BAGLAMA_AYI] / yeni[BAGLAMA_AYI]

    ort = eski.index.intersection(yeni.index)
    ort_oncesi = ort[ort <= BAGLAMA_AYI]
    oran = eski.loc[ort_oncesi] / yeni.loc[ort_oncesi]
    sapma = (oran / k - 1).abs()

    zincir_yeni = yeni * k
    sonuc = pd.concat([eski[eski.index <= BAGLAMA_AYI], zincir_yeni[zincir_yeni.index > BAGLAMA_AYI]]).sort_index()

    bilgi = {
        "k": float(k),
        "ortusme_baslangic": ort_oncesi.min(),
        "ortusme_bitis": ort_oncesi.max(),
        "ortusme_ay": int(len(ort_oncesi)),
        "oran_maks_sapma": float(sapma.max()),
        "oran_ay_en_buyuk": sapma.idxmax(),
    }
    ocak = pd.Timestamp("2026-01-01")
    if ocak in eski.index and ocak in yeni.index:
        bilgi["ocak2026_eski_yayin"] = float(eski[ocak])
        bilgi["ocak2026_zincir"] = float(zincir_yeni[ocak])
        bilgi["ocak2026_fark_yuzde"] = float((zincir_yeni[ocak] / eski[ocak] - 1) * 100)
    if sapma.max() > ORTUSME_TOLERANS:
        raise SystemExit(f"UYARI: iki baz ortusen donemde sabit oranli degil (maks sapma {sapma.max():.2e}); zincirleme yontemi gozden gecirilmeli")
    return sonuc, bilgi


def kaynak_yaz(bilgi: dict, son_ay: pd.Timestamp) -> None:
    metin = f"""TCMB EVDS3 - Tuketici Fiyat Endeksi (TUIK), genel endeks
=======================================================
Indirme tarihi : {date.today().isoformat()}
Kaynak         : TCMB EVDS3 web servisi, taban adres https://evds3.tcmb.gov.tr/igmevdsms-dis/
                 (anahtar HTTP basliginda 'key'; bu dosyada ve kodda yer almaz)
Seriler        : {ESKI}  (veri grubu bie_tukfiy4, TUFE 2003=100, "Arsiv"; son gozlem 2026-01)
                 {YENI}  (veri grubu bie_tukfiy2025, TUFE 2025=100, 2005-01'den itibaren)
Ham dosyalar   : TP.FG.J0_<YYYYMMDD>.json, TP.TUKFIY2025.GENEL_<YYYYMMDD>.json (API yanitinin aynisi)
Isleme betigi  : src/veri/tcmb_tufe.py
Islenmis cikti : data/islenmis/tcmb_tufe_turkiye_aylik.csv (tarih,deger; ayin ilk gunu; 2003=100 olcegi)

Zincirleme
  - {BAGLAMA_AYI:%Y-%m} ve oncesi: TP.FG.J0 aynen. Sonrasi: TP.TUKFIY2025.GENEL x k.
  - Baglama (ortusme) ayi: {BAGLAMA_AYI:%Y-%m}; k = eski/yeni = {bilgi['k']:.6f}
  - Dogrulama: iki seri {bilgi['ortusme_baslangic']:%Y-%m}..{bilgi['ortusme_bitis']:%Y-%m} ({bilgi['ortusme_ay']} ay) boyunca sabit oranli;
    k'dan en buyuk goreli sapma {bilgi['oran_maks_sapma']:.1e} ({bilgi['oran_ay_en_buyuk']:%Y-%m}; eski endeksin 2 ondalik yuvarlamasi).
    Yani 2025=100 serisi, eski serinin yeniden olceklenmis halidir; zincirleme gecmisi degistirmez.
  - Ocak 2026 kontrolu: eski yayin {bilgi.get('ocak2026_eski_yayin', float('nan')):.2f}, zincirlenmis {bilgi.get('ocak2026_zincir', float('nan')):.2f} (fark %{bilgi.get('ocak2026_fark_yuzde', float('nan')):.4f}).
  - Son gozlem: {son_ay:%Y-%m}

Notlar
  - TUFE endeksleri genelde revize edilmez (dogrulanmadi); bu klasordeki ham dosyalar yayin gunu kopyasi olarak da kullanilabilir.
  - Lisans: TCMB/EVDS veri kullanim kosullari gecerlidir, kaynak gosterilmelidir (kosul metni ayrica dogrulanmadi).
"""
    (HAM / "KAYNAK.txt").write_text(metin, encoding="utf-8")


def calistir() -> pd.Series:
    yanit = indir()
    eski = ev.ham_to_seri(yanit[ESKI], ESKI, "A")
    yeni = ev.ham_to_seri(yanit[YENI], YENI, "A")
    seri, bilgi = zincirle(eski, yeni)
    seri = seri.round(4)  # dosyaya yazilan ile bellekteki ayni olsun (oku() ile ayni sonuc)
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    cikti = pd.DataFrame({"tarih": seri.index.strftime("%Y-%m-%d"), "deger": seri.values})
    cikti.to_csv(CIKTI, index=False)
    kaynak_yaz(bilgi, seri.index.max())
    print(f"TUFE yazildi: {CIKTI.relative_to(KOK)}  ({len(seri)} ay, {seri.index.min():%Y-%m}..{seri.index.max():%Y-%m})")
    print(f"  baglama ayi {BAGLAMA_AYI:%Y-%m}, k={bilgi['k']:.6f}, ortusmede maks goreli sapma {bilgi['oran_maks_sapma']:.1e}")
    if "ocak2026_fark_yuzde" in bilgi:
        print(f"  Ocak 2026: eski yayin {bilgi['ocak2026_eski_yayin']:.2f} vs zincir {bilgi['ocak2026_zincir']:.2f} (fark %{bilgi['ocak2026_fark_yuzde']:.4f})")
    return seri


def oku() -> pd.Series:
    """Islenmis TUFE dosyasini (varsa) okur."""
    d = pd.read_csv(CIKTI, parse_dates=["tarih"])
    return pd.Series(d["deger"].values, index=pd.DatetimeIndex(d["tarih"]), name="tufe")


if __name__ == "__main__":
    calistir()
