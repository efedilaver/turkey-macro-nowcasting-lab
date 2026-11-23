"""TPPD (TP Petrol Dagitim) gecmis pompa fiyatlari -> aylik ortalama (Istanbul Avrupa).

Kaynak: https://www.tppd.com.tr/gecmis-akaryakit-fiyatlari (id=34 Istanbul, county=413 ISTANBUL-AVRUPA)
Tablo yalnizca fiyat DEGISIKLIGI tarihlerini verir; gunluk seri ileri doldurularak kurulur,
aylik deger gunluk ortalamadir. Fiyatlar vergi (OTV+KDV) dahil pompa fiyatidir, TL/litre.
Ham HTML yillik parcalar halinde data/ham/tppd_akaryakit/ altina kaydedilir (varsa yeniden indirilmez;
--yenile ile zorla). Reellestirme bu betikte YAPILMAZ (nominal TL).
"""
from __future__ import annotations
import argparse, re, time
from datetime import date
from pathlib import Path
import pandas as pd, requests
from bs4 import BeautifulSoup

KOK = Path(__file__).resolve().parents[2]
HAM = KOK / "data/ham/tppd_akaryakit"
OUT = KOK / "data/islenmis"
URL = "https://www.tppd.com.tr/gecmis-akaryakit-fiyatlari"
AYLAR = {"ocak":1,"şubat":2,"mart":3,"nisan":4,"mayıs":5,"haziran":6,"temmuz":7,"ağustos":8,"eylül":9,"ekim":10,"kasım":11,"aralık":12}

def indir(bas: date, bit: date, yenile: bool) -> Path:
    f = HAM / f"istanbul_avrupa_{bas:%Y%m%d}_{bit:%Y%m%d}.html"
    if f.exists() and not yenile:
        return f
    p = {"id": 34, "county": 413, "StartDate": bas.strftime("%d.%m.%Y"), "EndDate": bit.strftime("%d.%m.%Y")}
    for i in range(4):
        try:
            r = requests.get(URL, params=p, headers={"User-Agent": "Mozilla/5.0 altveri-lab"}, timeout=60)
            if r.status_code == 200:
                f.write_bytes(r.content); time.sleep(1); return f
        except requests.RequestException:
            pass
        time.sleep(2 ** i)
    raise SystemExit(f"indirilemedi: {p}")

def sayi(x):
    x = x.strip().replace(".", "").replace(",", ".")
    try: return float(x)
    except ValueError: return None

def ayristir(f: Path) -> pd.DataFrame:
    s = BeautifulSoup(f.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    t = s.find("table")
    if t is None: return pd.DataFrame(columns=["tarih", "benzin", "motorin_a", "motorin_b"])
    hd = [th.get_text(strip=True) for th in t.find_all("th")]
    satir = []
    for tr in t.find("tbody").find_all("tr"):
        td = [c.get_text(strip=True) for c in tr.find_all("td")]
        g, ay, y = td[0].split()
        satir.append({"tarih": pd.Timestamp(int(y), AYLAR[ay.lower().replace("I","ı")], int(g)),
                      "benzin": sayi(td[hd.index("KURŞUNSUZ BENZİN (TL/LT)")]),
                      "motorin_a": sayi(td[3]), "motorin_b": sayi(td[4])})
    return pd.DataFrame(satir)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--yenile", action="store_true"); a = ap.parse_args()
    HAM.mkdir(parents=True, exist_ok=True)
    bugun = date.today(); parcalar = []
    for y in range(2010, bugun.year + 1):
        bas = date(2010, 11, 11) if y == 2010 else date(y, 1, 1)
        bit = min(date(y, 12, 31), bugun)
        parcalar.append(ayristir(indir(bas, bit, a.yenile)))
    d = pd.concat(parcalar).drop_duplicates("tarih", keep="last").sort_values("tarih").set_index("tarih")
    # Tabloda iki "MOTORIN" sutunu var. 1. sutun 2013-04'te baslayan, ~0,04-0,08 TL daha pahali (premium) urun;
    # 2. sutun 2010'dan beri kesintisiz standart motorin. Standart motorin (2. sutun) kullanilir.
    d["motorin"] = d.motorin_b
    gun = pd.date_range(d.index.min(), pd.Timestamp(bugun), freq="D")
    g = d[["benzin", "motorin"]].reindex(gun).ffill()
    for kol, ad in (("benzin", "benzin95"), ("motorin", "motorin")):
        m = g[kol].groupby(g.index.to_period("M")).agg(["mean", "count"])
        m.index = m.index.to_timestamp()
        m = m[m.index >= "2011-01-01"]
        # tamamlanmamis son ay: gun sayisi eksikse isaretle (sadece tarih araligi raporlanir)
        out = pd.DataFrame({"tarih": m.index.strftime("%Y-%m-%d"), "deger": m["mean"].round(4)})
        out.to_csv(OUT / f"tppd_{ad}_istanbulavrupa_aylik.csv", index=False)
        print(ad, out.tarih.iloc[0], "->", out.tarih.iloc[-1], len(out), "ay | NaN:", int(out.deger.isna().sum()))
    print("degisim satiri:", len(d), "| ilk:", d.index.min().date(), "son:", d.index.max().date())

if __name__ == "__main__":
    main()
