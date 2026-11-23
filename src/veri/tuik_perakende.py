"""TUIK perakende ticaret satis hacim endeksi (H-002 hedefi) -> data/islenmis/tuik_perakendehacim_turkiye_aylik.csv

DURUM (2026-10-29): ILK ACIKLANAN SERI KURULAMADI; dosya GUNCEL (REVIZE) duzey serisidir.

Denenen yollar ve sonuclari
    1. EVDS3: veri gruplari listesinde perakende satis hacmi yok (680 veri grubu tarandi).
    2. TUIK SDMX (nsiws.tuik.gov.tr): kimlik dogrulama ister (401). Portalda Turkiye telefonuyla
       SMS dogrulamali API anahtari ya da info@tuik.gov.tr gerekir. .env'de TUIK anahtari yok.
    3. OECD STES Revisions (DSD_STES_REVISIONS@DF_STES_REVISIONS): Turkiye icin TOVM (perakende
       hacmi) YOK (PRVM var). Bu betik her calistirmada bunu bir kontrol sorgusuyla (DEU) yeniden dener.
    4. TUIK bulten arsivi: portal JavaScript uygulamasi, programatik erisim API anahtarina bagli.

Kullanilan kaynak (revize seri): OECD "Production, sales, work started and orders"
    OECD.SDD.STES,DSD_STES@DF_INDSERV,4.3 ; REF_AREA=TUR, FREQ=M, MEASURE=TOVM (Retail trade volume),
    ACTIVITY=G47, UNIT_MEASURE=IX. OECD bu veriyi TUIK'ten alir ve kendi bazina (2015=100) cevirir.
    ADJUSTMENT: kartin tercih sirasi once takvim arindirilmis (W), yoksa mevsim ve takvim
    arindirilmis (Y). Turkiye icin W yok; Y kullanilir.

Kullanim:  python src/veri/tuik_perakende.py
Anahtar gerekmez. Kasa tarihinde KESME YAPILMAZ.
"""
from __future__ import annotations

import io
from datetime import date
from pathlib import Path

import pandas as pd
import requests

KOK = Path(__file__).resolve().parents[2]
HAM = KOK / "data" / "ham" / "tuik_perakende"
CIKTI = KOK / "data" / "islenmis" / "tuik_perakendehacim_turkiye_aylik.csv"

OECD = "https://sdmx.oecd.org/public/rest/data/"
REVIZYON_AKISI = "OECD.SDD.STES,DSD_STES_REVISIONS@DF_STES_REVISIONS,4.0"
INDSERV_AKISI = "OECD.SDD.STES,DSD_STES@DF_INDSERV,4.3"
BASLIK = {"User-Agent": "altveri-lab", "Accept": "application/vnd.sdmx.data+csv; charset=utf-8; labels=id"}
TERCIH = ["W", "Y"]  # kart: once takvim arindirilmis, yoksa mevsim ve takvim arindirilmis


def al(akis: str, anahtar: str, ek: str = "") -> requests.Response:
    url = f"{OECD}{akis}/{anahtar}?dimensionAtObservation=AllDimensions{ek}"
    r = requests.get(url, headers=BASLIK, timeout=120)
    if r.status_code not in (200, 404):
        raise SystemExit(f"OECD istegi basarisiz: HTTP {r.status_code} ({anahtar})")
    return r


def revizyon_kontrol() -> str:
    """OECD STES Revisions'ta TUR perakende hacmi (TOVM) var mi? Kontrol sorgusu: DEU TOVM."""
    # anahtar: REF_AREA.FREQ.MEASURE.UNIT_MEASURE.ACTIVITY.EDITION
    kontrol = al(REVIZYON_AKISI, "DEU.M.TOVM...", "&startPeriod=2026-06")
    if kontrol.status_code != 200:
        return "BELIRSIZ (kontrol sorgusu DEU TOVM de basarisiz; sorgu bicimi gozden gecirilmeli)"
    tur = al(REVIZYON_AKISI, "TUR.M.TOVM...", "&startPeriod=2026-06")
    if tur.status_code == 404:
        return "YOK (TUR.M.TOVM bos; kontrol sorgusu DEU.M.TOVM dolu)"
    return "VAR - OECD Revisions artik TUR TOVM iceriyor: ilk aciklanan yol kurulmali (bu betik henuz islemiyor)"


def indir() -> pd.DataFrame:
    HAM.mkdir(parents=True, exist_ok=True)
    # anahtar: REF_AREA.FREQ.MEASURE.UNIT_MEASURE.ACTIVITY.ADJUSTMENT.TRANSFORMATION.TIME_HORIZ.METHODOLOGY
    r = al(INDSERV_AKISI, "TUR.M.TOVM.IX.G47....")
    if r.status_code != 200:
        raise SystemExit("OECD DF_INDSERV: TUR perakende hacmi bulunamadi")
    damga = date.today().strftime("%Y%m%d")
    (HAM / f"oecd_indserv_tur_tovm_{damga}.csv").write_bytes(r.content)
    return pd.read_csv(io.BytesIO(r.content))


def sec_ve_dogrula(d: pd.DataFrame) -> tuple[pd.Series, str, dict]:
    mevcut = sorted(d["ADJUSTMENT"].unique())
    secilen = next((a for a in TERCIH if a in mevcut), None)
    if secilen is None:
        raise SystemExit(f"Beklenen arindirma turu yok; mevcut: {mevcut}")
    s = d[d["ADJUSTMENT"] == secilen]
    for ad in ("MEASURE", "UNIT_MEASURE", "ACTIVITY", "TRANSFORMATION", "TIME_HORIZ", "METHODOLOGY"):
        if s[ad].nunique() != 1:
            raise SystemExit(f"Secilen seride {ad} birden fazla deger iceriyor: {s[ad].unique()}")
    if s["TIME_PERIOD"].duplicated().any():
        raise SystemExit("Yinelenen ay var")
    seri = pd.Series(s["OBS_VALUE"].values, index=pd.to_datetime(s["TIME_PERIOD"] + "-01"), name="deger").sort_index()
    if seri.isna().any() or (seri <= 0).any():
        raise SystemExit("Seride eksik/sifir-negatif deger var")
    tam = pd.date_range(seri.index.min(), seri.index.max(), freq="MS")
    eksik = tam.difference(seri.index)
    if len(eksik):
        raise SystemExit(f"Seride eksik ay var: {list(eksik)[:5]}")
    bilgi = {"mevcut_arindirma": mevcut, "baz": sorted(s["BASE_PER"].unique().tolist()),
             "durum": sorted(s["OBS_STATUS"].unique().tolist())}
    return seri, secilen, bilgi


def kaynak_yaz(seri: pd.Series, adj: str, bilgi: dict, rev: str) -> None:
    etiket = {"W": "takvim arindirilmis", "Y": "mevsim VE takvim arindirilmis"}[adj]
    metin = f"""TUIK perakende ticaret satis hacim endeksi (OECD DF_INDSERV uzerinden)  - H-002 hedefi
==========================================================================================
Indirme tarihi : {date.today().isoformat()}
Kaynak         : OECD SDMX API (anahtarsiz)  {OECD}{INDSERV_AKISI}/TUR.M.TOVM.IX.G47....
                 OECD veriyi TUIK'ten alir; OECD bazi (2015=100) ile sunar. TUIK'in kendi yayin bazi 2021=100'dur.
Ham dosya      : oecd_indserv_tur_tovm_<YYYYMMDD>.csv (API yanitinin aynisi; N ve Y serileri birlikte)
Isleme betigi  : src/veri/tuik_perakende.py
Islenmis cikti : data/islenmis/tuik_perakendehacim_turkiye_aylik.csv (tarih,deger)
Secilen seri   : ADJUSTMENT={adj} ({etiket}); mevcut turler: {', '.join(bilgi['mevcut_arindirma'])}; baz yili {', '.join(map(str, bilgi['baz']))}=100; OBS_STATUS {', '.join(bilgi['durum'])}
Kapsam         : {seri.index.min():%Y-%m}..{seri.index.max():%Y-%m}, {len(seri)} ay, eksik ay yok.

ILK ACIKLANAN DEGER YOK: Bu dosya GUNCEL (revize) baskidir; her ayin ilk yayinlandigi baski degildir.
  - OECD STES Revisions (aylik baski arsivi) Turkiye perakende hacmini icermiyor. Kontrol sonucu: {rev}.
  - TUIK SDMX/portal API'si kullaniciya ozel API anahtari ister (portalda Turkiye telefonuyla SMS dogrulamasi
    ya da telefonu olmayanlar icin info@tuik.gov.tr). .env'de anahtar yok.
  - Mevsim+takvim arindirilmis seri her ay yeniden tahmin edilir; gecmis degerler yayin gunundekinden farkli olabilir.

Dogrulama (elle, 2026-10-29): OECD-Y Agustos 2026 aylik degisimi %1,4 = TUIK bulteninin basinda aktarilan aylik degisimi (%1,4).
  Yillik degisim TUIK manset rakamiyla (%10,1) AYNI DEGIL: OECD-Y yillik %11,9. TUIK'in manset yillik degisimi
  (kartin hedef tanimindaki takvim arindirilmis seri) mevsim+takvim arindirilmis serinin yoy'u olmayabilir.
  OECD'de yalniz N (arindirilmamis) ve Y vardir; takvim arindirilmis (W) yoktur.

Lisans/kosul: OECD veri kullanim kosullari (oecd.org/termsandconditions); atif gerekir (metin ayrica dogrulanmadi).
  Altta yatan resmi istatistik TUIK'indir.
"""
    (HAM / "KAYNAK.txt").write_text(metin, encoding="utf-8")


def main() -> None:
    rev = revizyon_kontrol()
    print(f"OECD STES Revisions, TUR perakende hacmi (TOVM): {rev}")
    d = indir()
    seri, adj, bilgi = sec_ve_dogrula(d)
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"tarih": seri.index.strftime("%Y-%m-%d"), "deger": seri.round(4).values}).to_csv(CIKTI, index=False)
    kaynak_yaz(seri, adj, bilgi, rev)
    print(f"hedef yazildi: {CIKTI.relative_to(KOK)}  ({len(seri)} ay, {seri.index.min():%Y-%m}..{seri.index.max():%Y-%m}); "
          f"ADJUSTMENT={adj}, baz {bilgi['baz']}")
    print("ILK ACIKLANAN: kurulamadi -> dosya guncel (revize) duzey serisi")
    print(f"son ay degeri {seri.iloc[-1]:.2f}; son aylik degisim %{(seri.iloc[-1] / seri.iloc[-2] - 1) * 100:.1f}; "
          f"son yillik degisim %{(seri.iloc[-1] / seri.iloc[-13] - 1) * 100:.1f}")


if __name__ == "__main__":
    main()
