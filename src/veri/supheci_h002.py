"""H-002 şüpheci incelemesi için türetilmiş seriler (_supheci ekli; mevcut dosyalara dokunmaz).

Üretilen dosyalar
    1. data/islenmis/tuik_perakendehacimnsa_turkiye_aylik_supheci.csv
       Hedefin mevsim ve takvim etkisinden ARINDIRILMAMIŞ (OECD ADJUSTMENT=N) hali.
       Kaynak: ana betiğin (tuik_perakende.py) indirdiği ham OECD dosyası, aynı akış ve boyutlar;
       yalnız ADJUSTMENT=N seçilir. Ham dosya değiştirilmez; yeniden indirme yapılmaz.
    2. data/islenmis/tcmb_tufeplasebo_turkiye_aylik_supheci.csv
       Plasebo gösterge: 100 * 100 / TÜFE (nominal tutarı sabit tutulmuş "reel" seri).
       Ay kapsamı kart göstergesiyle (tcmb_kartharcamareel_turkiye_aylik.csv) birebir aynıdır,
       böylece motorun örneklemi ve OOS bölünmesi ana testle aynı kalır.

Kullanım:  python src/veri/supheci_h002.py
Kasa tarihinde KESME YAPILMAZ; kesmeyi test motoru yapar.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parents[2]
HAM_OECD = KOK / "data" / "ham" / "tuik_perakende" / "oecd_indserv_tur_tovm_20261029.csv"
TUFE = KOK / "data" / "islenmis" / "tcmb_tufe_turkiye_aylik.csv"
KART = KOK / "data" / "islenmis" / "tcmb_kartharcamareel_turkiye_aylik.csv"
CIKTI_NSA = KOK / "data" / "islenmis" / "tuik_perakendehacimnsa_turkiye_aylik_supheci.csv"
CIKTI_PLASEBO = KOK / "data" / "islenmis" / "tcmb_tufeplasebo_turkiye_aylik_supheci.csv"


def nsa_hedef() -> pd.Series:
    d = pd.read_csv(HAM_OECD)
    s = d[(d["ADJUSTMENT"] == "N") & (d["MEASURE"] == "TOVM") & (d["ACTIVITY"] == "G47")]
    for ad in ("UNIT_MEASURE", "TRANSFORMATION", "TIME_HORIZ", "METHODOLOGY", "BASE_PER"):
        if s[ad].nunique() != 1:
            raise SystemExit(f"N serisinde {ad} birden fazla değer içeriyor: {s[ad].unique()}")
    if s["TIME_PERIOD"].duplicated().any():
        raise SystemExit("N serisinde yinelenen ay var")
    seri = pd.Series(s["OBS_VALUE"].values, index=pd.to_datetime(s["TIME_PERIOD"] + "-01")).sort_index()
    tam = pd.date_range(seri.index.min(), seri.index.max(), freq="MS")
    if len(tam.difference(seri.index)) or seri.isna().any() or (seri <= 0).any():
        raise SystemExit("N serisinde eksik ay ya da sıfır/negatif değer var")
    return seri


def plasebo_gosterge() -> pd.Series:
    tufe = pd.read_csv(TUFE, parse_dates=["tarih"]).set_index("tarih")["deger"]
    kart = pd.read_csv(KART, parse_dates=["tarih"]).set_index("tarih")["deger"]
    t = tufe.reindex(kart.index)
    if t.isna().any():
        raise SystemExit("Kart aylarından bazıları için TÜFE yok")
    return 100.0 * 100.0 / t


def yaz(seri: pd.Series, yol: Path, ondalik: int) -> None:
    pd.DataFrame({"tarih": seri.index.strftime("%Y-%m-%d"), "deger": seri.round(ondalik).values}).to_csv(yol, index=False)
    print(f"yazıldı: {yol.relative_to(KOK)}  ({len(seri)} ay, {seri.index.min():%Y-%m}..{seri.index.max():%Y-%m})")


def main() -> None:
    yaz(nsa_hedef(), CIKTI_NSA, 4)
    yaz(plasebo_gosterge(), CIKTI_PLASEBO, 8)


if __name__ == "__main__":
    main()
