"""BVAR dersi icin EVDS3'ten 4 aylik seri ceker (yalnizca egitim amacli).

Bu betik arastirma hattinin (hipotez -> test motoru) parcasi DEGILDIR.
Ciktilar `ogrenme/bvar/veri/` altina yazilir; `data/`, `kayit/` ve
`hipotezler/` klasorlerine dokunulmaz.

Kasa disiplini: istek bitis tarihi 31-03-2025'tir. Kasa donemi
(ayarlar.json -> kasa_baslangic = 2025-04-01) hic indirilmez.

Seriler (EVDS3):
    TP.TSANAYMT2021.BCD   Sanayi uretim endeksi, toplam, mevsim+takvim arindirilmis (2021=100)
    TP.TUKFIYARND.OKTG01  TUFE genel, mevsim etkisinden arindirilmis (2025=100)
    TP.DK.USD.A.YTL       USD/TRY doviz alis (gunluk -> aylik ortalama)
    TP.APIFON4            TCMB agirlikli ortalama fonlama maliyeti, % (is gunu -> aylik ortalama)

Calistirma (proje kokunden):
    python ogrenme/bvar/veri_cek.py
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "src" / "veri"))
from evds3_istemci import _al, ham_to_seri  # noqa: E402

BURA = Path(__file__).resolve().parent
HAM = BURA / "veri" / "ham"
CIKTI = BURA / "veri" / "bvar_ders_aylik.csv"

BAS = "01-01-2011"   # AOFM 2011-01'de basliyor
BIT = "31-03-2025"   # kasa_baslangic'tan bir gun once

SERILER = {
    "sue": ("TP.TSANAYMT2021.BCD", False),
    "tufe": ("TP.TUKFIYARND.OKTG01", False),
    "usdtry": ("TP.DK.USD.A.YTL", True),   # True: gunluk, aylik ortalamaya cevir
    "aofm": ("TP.APIFON4", True),
}


def cek(kod: str, gunluk: bool) -> pd.Series:
    ek = "&frequency=5&aggregationTypes=avg" if gunluk else ""
    yanit = _al(f"series={kod}&startDate={BAS}&endDate={BIT}&type=json{ek}").json()
    HAM.mkdir(parents=True, exist_ok=True)
    (HAM / f"{kod}_{date.today():%Y%m%d}.json").write_text(json.dumps(yanit, ensure_ascii=False))
    return ham_to_seri(yanit, kod, "A")


def main() -> None:
    sutunlar = {}
    for ad, (kod, gunluk) in SERILER.items():
        s = cek(kod, gunluk)
        print(f"{ad:7s} {kod:22s} {s.index.min():%Y-%m} .. {s.index.max():%Y-%m}  n={s.notna().sum()}")
        sutunlar[ad] = s
    df = pd.DataFrame(sutunlar)
    df = df.loc["2011-01-01":"2025-03-01"]
    if df.index.max() >= pd.Timestamp("2025-04-01"):
        raise SystemExit("Kasa donemi veriye sizdi; durdu.")
    eksik = df.isna().sum()
    if eksik.any():
        print("Eksik gozlem:\n", eksik[eksik > 0])
    df.index.name = "tarih"
    df.to_csv(CIKTI, float_format="%.6f")
    print(f"Yazildi: {CIKTI.relative_to(KOK)}  ({len(df)} ay)")


if __name__ == "__main__":
    main()
