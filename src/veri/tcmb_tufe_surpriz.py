"""H-005 hedef serisi: TUFE aylik % degisim, PKA cari ay beklentisi, surpriz.

Ne yapar
    1. data/islenmis/tcmb_tufe_turkiye_aylik.csv (zincirlenmis endeks) -> 100*(I_t/I_{t-1}-1), 2 ondalik.
       Cikti: tcmb_tufeaylik_turkiye_aylik.csv
    2. EVDS3 veri grubu bie_urbek, seri TP.BEK.S01.A.A = Piyasa Katilimcilari Anketi (PKA),
       "Cari Ayin Aylik TUFE Beklentisi (% Degisim)", ARITMETIK ORTALAMA. Anketin yapildigi ay = hedef ay.
       Ham yanit: data/ham/tcmb_pka/. Cikti: tcmb_pkatufebeklenti_turkiye_aylik.csv
       (eksik aylar doldurulmaz; yalniz degeri olan aylar yazilir.)
    3. Surpriz = TUFE aylik degisim - PKA beklentisi (iki de dolu olan aylar), 2 ondalik.
       Cikti: tcmb_tufesurpriz_turkiye_aylik.csv
    4. Kontrol: EVDS formulas=1 (yuzde degisim) ile hesaplanan degisimin farki (yalniz kasa oncesi ozet).

Veri kasa tarihinde kirpilmaz (test motoru keser). Ekrana kasa donemi degeri yazilmaz.
Kullanim: python src/veri/tcmb_tufe_surpriz.py   (anahtar .env: EVDS_API_KEY; yazdirilmaz)
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
HAM = KOK / "data" / "ham" / "tcmb_pka"
ISL = KOK / "data" / "islenmis"
PKA_KOD = "TP.BEK.S01.A.A"
KASA_ONCESI = pd.Timestamp("2025-04-01")  # yalniz raporlama sinirI (veri kirpilmaz)


def yaz(s: pd.Series, ad: str) -> None:
    df = pd.DataFrame({"tarih": s.index.strftime("%Y-%m-%d"), "deger": s.values})
    df.to_csv(ISL / ad, index=False)


def main() -> None:
    HAM.mkdir(parents=True, exist_ok=True)
    damga = date.today().strftime("%Y%m%d")

    # 1) TUFE aylik degisim
    idx = pd.read_csv(ISL / "tcmb_tufe_turkiye_aylik.csv", parse_dates=["tarih"]).set_index("tarih")["deger"]
    tam = pd.date_range(idx.index.min(), idx.index.max(), freq="MS")
    if len(tam.difference(idx.index)) > 0:
        raise SystemExit("TUFE endeksinde eksik ay var")
    tufe = (100 * (idx / idx.shift(1) - 1)).dropna().round(2)
    yaz(tufe, "tcmb_tufeaylik_turkiye_aylik.csv")

    # 2) PKA
    y = ev.seri_ham(PKA_KOD, "01-01-2013")
    (HAM / f"{PKA_KOD}_{damga}.json").write_text(json.dumps(y, ensure_ascii=False), encoding="utf-8")
    pka_tam = ev.ham_to_seri(y, PKA_KOD, "A")
    eksik = pka_tam[pka_tam.isna()].index
    pka = pka_tam.dropna()
    yaz(pka, "tcmb_pkatufebeklenti_turkiye_aylik.csv")

    # 3) surpriz
    ortak = tufe.index.intersection(pka.index)
    surpriz = (tufe.loc[ortak] - pka.loc[ortak]).round(2)
    yaz(surpriz, "tcmb_tufesurpriz_turkiye_aylik.csv")

    # 4) EVDS yuzde degisim kontrolu (formulas=1 -> yuzde degisim), yalniz kasa oncesi
    notlar = []
    try:
        for kod in ("TP.FG.J0",):
            r = ev._al(f"series={kod}&startDate=01-01-2003&endDate={ev.bugun_str()}&type=json&formulas=1").json()
            alan = kod.replace(".", "_") + "-1"  # formulas=1 yanitinda alan adi '-1' soneklidir
            k = {}
            for it in r["items"]:
                v = it.get(alan)
                if v not in (None, "", "ND"):
                    yl, ay = it["Tarih"].split("-")
                    k[pd.Timestamp(int(yl), int(ay), 1)] = float(v)
            evs = pd.Series(k).sort_index()
            ort = evs.index.intersection(tufe.index)
            ort = ort[(ort <= pd.Timestamp("2025-12-01")) & (ort < KASA_ONCESI)]
            fark = (evs.loc[ort].round(2) - tufe.loc[ort]).abs()
            notlar.append(f"EVDS formulas=1 ({kod}) ile fark: n={len(ort)}, maks={fark.max():.3f}, >0.01 olan ay={(fark > 0.0101).sum()}")
    except SystemExit as h:
        notlar.append(f"formulas=1 kontrolu yapilamadi: {h}")

    on = surpriz[surpriz.index < KASA_ONCESI]
    print(f"TUFE aylik degisim: {tufe.index.min():%Y-%m} .. {tufe.index.max():%Y-%m}, n={len(tufe)}")
    print(f"PKA ({PKA_KOD}, aritmetik ortalama): {pka.index.min():%Y-%m} .. {pka.index.max():%Y-%m}, n={len(pka)}; EVDS'de bos ay: {[d.strftime('%Y-%m') for d in eksik]}")
    aralik = pd.date_range(pka.index.min(), pka.index.max(), freq="MS")
    print("PKA ic bosluklar:", [d.strftime("%Y-%m") for d in aralik.difference(pka.index)])
    print(f"Surpriz: {surpriz.index.min():%Y-%m} .. {surpriz.index.max():%Y-%m}, n={len(surpriz)}")
    print(f"Kasa oncesi (<2025-04): n={len(on)}, ilk={on.index.min():%Y-%m}, son={on.index.max():%Y-%m}")
    print(f"Kasa oncesi betimsel: ort={on.mean():.3f}, sd={on.std():.3f}, min={on.min():.2f}, maks={on.max():.2f}, medyan={on.median():.2f}")
    for n in notlar:
        print(n)


if __name__ == "__main__":
    main()
