"""Akaryakit pompa fiyati endeksi, USD cinsinden (BVAR gelistirme / kesif icin).

Girdi : data/islenmis/tppd_benzin95_istanbulavrupa_aylik.csv, tppd_motorin_istanbulavrupa_aylik.csv
        (src/veri/tppd_akaryakit.py; TL/litre, OTV+KDV dahil, gunluk fiyattan aylik ortalama)
        data/islenmis/tcmb_usdtry_turkiye_aylik.csv
Cikti : data/islenmis/tppd_akaryakitusd_istanbulavrupa_aylik.csv
        deger = ((benzin + motorin) / 2) / USDTRY  (USD/litre)

Neden USD: TL fiyatlar hizlanan trend tasir ve BVAR'da patlayan kok uretir (Brent TL'de goruldu).
USD/TRY zaten VAR'da oldugu icin log-dogrusal VAR'da TL fiyatiyla ayni bilgiyi tasir.
Icinde bulunulan ay (tamamlanmamis) atilir. Betik deger yazdirmaz, yalnizca tarih araligi.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

ISLENMIS = Path(__file__).resolve().parents[2] / "data" / "islenmis"


def oku(dosya: str) -> pd.Series:
    return pd.read_csv(ISLENMIS / dosya, parse_dates=["tarih"]).set_index("tarih")["deger"]


def main() -> None:
    bu_ay = pd.Timestamp(date.today().replace(day=1))
    tl = (oku("tppd_benzin95_istanbulavrupa_aylik.csv") + oku("tppd_motorin_istanbulavrupa_aylik.csv")) / 2
    s = (tl / oku("tcmb_usdtry_turkiye_aylik.csv")).dropna()
    s = s[s.index < bu_ay]
    eksik = pd.date_range(s.index.min(), s.index.max(), freq="MS").difference(s.index)
    if len(eksik) or (s <= 0).any():
        raise SystemExit("eksik ay veya pozitif olmayan deger var")
    pd.DataFrame({"tarih": s.index.strftime("%Y-%m-%d"), "deger": s.values}).to_csv(
        ISLENMIS / "tppd_akaryakitusd_istanbulavrupa_aylik.csv", index=False, float_format="%.6f")
    print(f"akaryakit_usd {s.index.min():%Y-%m} .. {s.index.max():%Y-%m} n={len(s)} "
          "-> data/islenmis/tppd_akaryakitusd_istanbulavrupa_aylik.csv")


if __name__ == "__main__":
    main()
