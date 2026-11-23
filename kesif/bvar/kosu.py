"""BVAR geliştirme (KEŞİF) koşucusu: resmi test motorunun BVAR hesabını kayda yazmadan çalıştırır.

Bu bir resmi deneme DEĞİLDİR. kayit/denemeler.csv'ye yazmaz, hipotez kartı yoktur
(kullanıcı 2026-11-07'de bu geliştirme işi için kayıt kuralından feragat etti).
Kaç varyant denendiği bilinsin diye her çalıştırma kesif/bvar/varyant_gunlugu.csv'ye eklenir.
Kasa her zaman kapalıdır (kasa=False sabit); örneklem dışı dönem H-004 ile aynıdır.

Kullanım:
    python kesif/bvar/kosu.py --tanim kesif/bvar/tanimlar/V1_sv.json --donusum logdiff --hedef-gecikme 1
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "src" / "analiz"))
import test_et  # noqa: E402

BURASI = Path(__file__).resolve().parent
GUNLUK = BURASI / "varyant_gunlugu.csv"
DONEMLER = {"sakin_1912_2108": ("2019-12", "2021-08"), "kur_soku_2109_2212": ("2021-09", "2022-12"),
            "y2023": ("2023-01", "2023-12"), "dezenf_2401_2503": ("2024-01", "2025-03")}


def ek_olculer(tb: pd.DataFrame) -> dict:
    tb = tb.assign(tarih=pd.to_datetime(tb["tarih"]))
    e_ar, e_bv = tb.gercek - tb.ar, tb.gercek - tb.bvar
    kaz = e_ar ** 2 - e_bv ** 2
    sira = kaz.sort_values(ascending=False).index
    ilk5 = sira[:5]
    kalan = sira[5:]
    sonuc = {"ilk5_kazanc_payi": float(kaz[ilk5].sum() / kaz.sum()) if kaz.sum() else float("nan"),
             "oran_ilk5_haric": float(np.sqrt((e_bv[kalan] ** 2).mean() / (e_ar[kalan] ** 2).mean())),
             "ort_hata": float(e_bv.mean())}
    for ad, (a, b) in DONEMLER.items():
        m = (tb.tarih >= a) & (tb.tarih <= b)
        i90 = (tb.q05[m] <= tb.gercek[m]) & (tb.gercek[m] <= tb.q95[m])
        sonuc[f"oran_{ad}"] = float(np.sqrt((e_bv[m] ** 2).mean() / (e_ar[m] ** 2).mean()))
        sonuc[f"kaps90_{ad}"] = float(i90.mean())
    return sonuc


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--tanim", required=True)
    p.add_argument("--donusum", required=True)
    p.add_argument("--hedef-gecikme", type=int, required=True)
    a = p.parse_args()
    tanim = json.loads(Path(a.tanim).read_text(encoding="utf-8"))
    hedef = next(s for s in tanim["seriler"] if s["ad"] == tanim["hedef"])["yol"]
    ns = argparse.Namespace(hedef=str(KOK / hedef), donusum=a.donusum, hedef_gecikme=a.hedef_gecikme,
                            haric=None, kasa=False, bvar_tanim=a.tanim, model="bvar")
    t0 = datetime.now()
    s = test_et.calistir_bvar(ns)
    ek = ek_olculer(pd.DataFrame(s["tablo"]))
    etiket = f"{Path(a.tanim).stem}_{a.donusum}_h{a.hedef_gecikme}"
    damga = t0.strftime("%Y%m%d-%H%M%S")
    (BURASI / "sonuclar" / f"{etiket}_{damga}.json").write_text(
        json.dumps({**s, "ek": ek}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    satir = {"zaman": t0.isoformat(timespec="seconds"), "etiket": etiket, "tanim": a.tanim,
             "n_oos": s["n_oos"], "rmse_oran": round(s["rmse_oran"], 4), "dm_p": round(s["dm_p"], 4),
             "yon_model": round(s["yon_isabet_model"], 3), "yon_ref": round(s["yon_isabet_referans"], 3),
             "kaps68": round(s["kapsama_68"], 3), "kaps90": round(s["kapsama_90"], 3),
             **{k: round(v, 3) for k, v in ek.items()}, "sure_sn": int((datetime.now() - t0).total_seconds())}
    with GUNLUK.open("a", newline="", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)           # paralel koşular aynı anda yazmasın
        w = csv.DictWriter(f, fieldnames=list(satir))
        if f.tell() == 0:
            w.writeheader()
        w.writerow(satir)
        fcntl.flock(f, fcntl.LOCK_UN)
    print(json.dumps(satir, ensure_ascii=False, indent=1))
    print("PIT ondalık:", s["pit_ondalik_sayim"])


if __name__ == "__main__":
    main()
