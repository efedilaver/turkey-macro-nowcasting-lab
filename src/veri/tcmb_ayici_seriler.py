"""BVAR gelistirme (kesif) icin ay ici bilinen iki gosterge: EVDS3 -> data/ham + data/islenmis.

Ne yapar
    1. EVDS3'ten iki seriyi indirir, yanitlarin aynisini data/ham/evds_ayici/ altina
       tarih damgasiyla yazar (+ KAYNAK.txt).
         TP.FG.B01.95          ITO Istanbul ucretliler gecinme endeksi, genel (1995=100), aylik.
                               ITO ay verisini izleyen ayin 1'inde, TUIK'ten (ayin 3'u) once aciklar.
         TP.BRENTPETROL.EUBP   Avrupa Brent spot FOB (USD/varil), is gunu -> EVDS aylik ortalama
    2. Islenmis seriler (tarih,deger; ayin ilk gunu):
         ito_gecinme_istanbul_aylik.csv     ITO genel endeks, mevsimsellik var (ham duzey)
         ito_gecinmema_istanbul_aylik.csv   ITO, ay-yil ortalamasi cikarilarak mevsimsellikten
                                            arindirilmis duzey. Mevsim faktorleri YALNIZCA
                                            MEVSIM_SON (2019-11) ve oncesinden hesaplanir; boylece
                                            2019-12'de baslayan orneklem disi doneme bilgi sizmaz.
         tcmb_brent_dunya_aylik.csv         Brent aylik ortalama, USD/varil (VAR'a bu girer: USD/TRY
                                            zaten VAR'da; log-dogrusal VAR'da TL fiyatiyla ayni bilgi,
                                            ama trendsiz oldugu icin patlayan kok uretmez)
         tcmb_brenttl_dunya_aylik.csv       Brent (USD) aylik ort. x USD/TRY aylik ort. = TL/varil
                                            (USD/TRY: data/islenmis/tcmb_usdtry_turkiye_aylik.csv)
    3. Dogrulamalar: ay eksigi yok, deger pozitif.

Kasa: Seriler bugune kadar indirilir; kasa kesimini motor yapar. Betik kasa donemine ait
hicbir degeri ekrana yazdirmaz (yalnizca tarih araliklari).

Kullanim:  python src/veri/tcmb_ayici_seriler.py   (once tcmb_bvar_seriler.py calismis olmali)
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
HAM = KOK / "data" / "ham" / "evds_ayici"
ISLENMIS = KOK / "data" / "islenmis"
MEVSIM_BAS, MEVSIM_SON = "2011-01-01", "2019-11-01"   # mevsim faktorlerinin tahmin penceresi

KAYNAK_METNI = """Kaynak: TCMB EVDS3 (https://evds3.tcmb.gov.tr), indiren: src/veri/tcmb_ayici_seriler.py
Dosyalar API yanitinin aynisidir: <SERI_KODU>_<YYYYMMDD>.json (indirme tarihi).
TP.FG.B01.95         veri grubu bie_ito95        ITO Istanbul ucretliler gecinme endeksi, genel, 1995=100, aylik
TP.BRENTPETROL.EUBP  veri grubu bie_brentpetrol  Avrupa Brent spot FOB, USD/varil; istek frequency=5&aggregationTypes=avg
"""


def indir(kod: str, bas: str, aylik_ort: bool, damga: str) -> pd.Series:
    ek = "&frequency=5&aggregationTypes=avg" if aylik_ort else ""
    yanit = ev._al(f"series={kod}&startDate={bas}&endDate={ev.bugun_str()}&type=json{ek}").json()
    (HAM / f"{kod}_{damga}.json").write_text(json.dumps(yanit, ensure_ascii=False), encoding="utf-8")
    return ev.ham_to_seri(yanit, kod, "A")


def dogrula(ad: str, s: pd.Series) -> pd.Series:
    s = s.dropna()
    eksik = pd.date_range(s.index.min(), s.index.max(), freq="MS").difference(s.index)
    if len(eksik):
        raise SystemExit(f"{ad}: eksik ay var: {[t.strftime('%Y-%m') for t in eksik[:5]]}")
    if (s <= 0).any():
        raise SystemExit(f"{ad}: pozitif olmayan deger var")
    return s


def yaz(s: pd.Series, dosya: str, ad: str) -> None:
    pd.DataFrame({"tarih": s.index.strftime("%Y-%m-%d"), "deger": s.values}).to_csv(
        ISLENMIS / dosya, index=False, float_format="%.6f")
    print(f"{ad:10s} {s.index.min():%Y-%m} .. {s.index.max():%Y-%m}  n={len(s):3d}  -> data/islenmis/{dosya}")


def mevsimden_arindir(s: pd.Series) -> pd.Series:
    """100*dlog'dan ay-yil ortalamasini (yalniz MEVSIM_BAS..MEVSIM_SON) cikar, duzeye geri topla."""
    dl = 100 * np.log(s).diff()
    pencere = dl[(dl.index >= MEVSIM_BAS) & (dl.index <= MEVSIM_SON)]
    faktor = pencere.groupby(pencere.index.month).mean()
    faktor = faktor - faktor.mean()          # yalnizca mevsim deseni; ortalama enflasyon korunur
    duz = dl - dl.index.month.map(faktor).values
    duz.iloc[0] = 0.0
    return float(s.iloc[0]) * np.exp(duz.cumsum() / 100)


def main() -> None:
    HAM.mkdir(parents=True, exist_ok=True)
    (HAM / "KAYNAK.txt").write_text(KAYNAK_METNI, encoding="utf-8")
    damga = date.today().strftime("%Y%m%d")
    bu_ay = pd.Timestamp(date.today().replace(day=1))

    ito = dogrula("ito", indir("TP.FG.B01.95", "01-01-2005", False, damga))
    yaz(ito, "ito_gecinme_istanbul_aylik.csv", "ito")
    yaz(mevsimden_arindir(ito), "ito_gecinmema_istanbul_aylik.csv", "ito_ma")

    brent = indir("TP.BRENTPETROL.EUBP", "01-01-2005", True, damga)
    brent = dogrula("brent", brent[brent.index < bu_ay])
    yaz(brent, "tcmb_brent_dunya_aylik.csv", "brent_usd")
    usd =pd.read_csv(ISLENMIS / "tcmb_usdtry_turkiye_aylik.csv", parse_dates=["tarih"]).set_index("tarih")["deger"]
    brent_tl = dogrula("brent_tl", (brent * usd).dropna())
    yaz(brent_tl, "tcmb_brenttl_dunya_aylik.csv", "brent_tl")


if __name__ == "__main__":
    main()
