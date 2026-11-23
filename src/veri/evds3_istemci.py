"""TCMB EVDS3 icin kucuk istemci (H-002 veri betikleri tarafindan kullanilir).

Anahtar proje kokundeki .env dosyasindan (python-dotenv) `EVDS_API_KEY` adiyla
okunur ve YALNIZCA `key` HTTP basliginda gonderilir. Anahtar hicbir yere
yazdirilmaz, loglanmaz, dosyaya yazilmaz. User-Agent: altveri-lab.

Adresler (EVDS3, Ocak 2026'dan beri):
    taban : https://evds3.tcmb.gov.tr/igmevdsms-dis/
    veri  : series=<KOD>&startDate=dd-mm-yyyy&endDate=dd-mm-yyyy&type=json
    liste : serieList/type=json&code=<veri_grubu>
"""
from __future__ import annotations

import os
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

KOK = Path(__file__).resolve().parents[2]
TABAN = "https://evds3.tcmb.gov.tr/igmevdsms-dis/"
ZAMAN_ASIMI = 60
DENEME = 4


def _anahtar() -> str:
    load_dotenv(KOK / ".env")
    k = (os.environ.get("EVDS_API_KEY") or "").strip()
    if not k:
        raise SystemExit("EVDS_API_KEY tanimli degil (.env). Anahtari evds3.tcmb.gov.tr -> Profil'den alin.")
    return k


def _al(yol: str):
    """GET istegi; gecici hatalarda ustel bekleyerek tekrar dener. Basliklari asla yazdirmaz."""
    baslik = {"User-Agent": "altveri-lab", "key": _anahtar()}
    son = "bilinmiyor"
    for i in range(DENEME):
        try:
            r = requests.get(TABAN + yol, headers=baslik, timeout=ZAMAN_ASIMI)
        except requests.RequestException as hata:
            son = f"baglanti hatasi ({type(hata).__name__})"
        else:
            if r.status_code == 200:
                return r
            son = f"HTTP {r.status_code}"
            if r.status_code in (400, 401, 403, 404):  # tekrar denemenin anlami yok
                break
        time.sleep(2 ** i)
    raise SystemExit(f"EVDS3 istegi basarisiz: {yol.split('&')[0]} -> {son}")


def bugun_str() -> str:
    return date.today().strftime("%d-%m-%Y")


def seri_listesi(veri_grubu: str) -> list:
    return _al(f"serieList/type=json&code={veri_grubu}").json()


def seri_ham(kod: str, bas: str, bit: str | None = None) -> dict:
    """Tek serinin ham JSON yaniti (items dahil). bas/bit: dd-mm-yyyy."""
    bit = bit or bugun_str()
    return _al(f"series={kod}&startDate={bas}&endDate={bit}&type=json").json()


def ham_to_seri(yanit: dict, kod: str, sikl: str) -> pd.Series:
    """Ham yaniti tarih indeksli float Series'e cevirir.

    sikl='A' (aylik): Tarih 'YYYY-M' -> ayin ilk gunu.
    sikl='H' (haftalik): Tarih 'dd-mm-yyyy' (Cuma).
    """
    alan = kod.replace(".", "_")
    tarih, deger = [], []
    for x in yanit.get("items", []):
        v = x.get(alan)
        deger.append(float(v) if v not in (None, "") else np.nan)
        t = x["Tarih"]
        if sikl == "A":
            y, a = t.split("-")
            tarih.append(pd.Timestamp(int(y), int(a), 1))
        else:
            tarih.append(pd.to_datetime(t, format="%d-%m-%Y"))
    s = pd.Series(deger, index=pd.DatetimeIndex(tarih), name=kod).sort_index()
    if not s.index.is_unique:
        raise SystemExit(f"{kod}: yinelenen tarih var")
    return s
