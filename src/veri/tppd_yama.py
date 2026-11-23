"""TPPD akaryakit serisindeki arsiv deligini Petrol Ofisi (PO) arsiviyle yamalar.

SORUN: TPPD "gecmis fiyatlar" arsivi (Istanbul-Avrupa) 2025-12 -> 2026-04 arasinda ~132 gunluk,
hicbir urunde degisiklik kaydi olmayan bir delik icerir (2019-2024'te degisiklikler arasi en uzun aralik 8-39 gun).
ALT KAYNAK: Petrol Ofisi "Gecmis Akaryakit Fiyatlari" (https://www.petrolofisi.com.tr/arsiv-fiyatlari;
POST /Fuel/Search, template=3, cityId=34, districtId=03431 = ISTANBUL (AVRUPA)). Gunluk satirlar, KDV dahil, TL/LT.
Urun eslemesi: benzin95 <- "V/Max Kursunsuz 95"; motorin <- "V/Max Diesel" (PO'nun V/Pro Diesel sutunu 2024-12-31'den beri '-' (bos); ileri
doldurulursa yapay sabit seri uretir, bu yuzden KULLANILMAZ. V/Max Diesel 2019-12-30'dan beri dolu; yalnizca GUNLUK ORAN kullanildigi
icin ~%0,1-0,2 duzey farki (premium) onemsiz; 2023-2024 uyum istatistigi asagida).

YAMA YONTEMI (oransal zincirleme):
  1. TPPD gunluk seri = degisiklik kayitlarinin ileri doldurulmasi (tppd_akaryakit.py ile ayni).
  2. Delik: TPPD kayit tarihleri arasinda 2025-01-01 sonrasi, > ESIK_GUN gunluk TEK aralik. Birden fazla/hic yoksa durur.
     g0 = deligin basindaki son TPPD kayit gunu (son ortak gozlem gunu), g1 = TPPD'nin ilk yeni kaydi.
  3. g0 < d < g1 gunleri icin:  yama[d] = TPPD[g0] * PO[d] / PO[g0]
     (g0'da PO ile TPPD esitlenir; PO'nun yalnizca GUNLUK ORANSAL degisimi TPPD duzeyine uygulanir).
  4. d >= g1: TPPD'ye geri donulur (ilk yeni kayit TPPD'nin kendi degeri). d <= g0: TPPD aynen.
  5. Aylik deger = gunluk ortalama (bugune kadar, tppd_akaryakit.py ile ayni). Nominal TL; reellestirme
     burada yapilmaz (akaryakit-USD serisi kur ile bolunur: ((benzin+motorin)/2)/USDTRY, icinde bulunulan ay haric,
     akaryakit_usd.py ile ayni tanim).

DOGRULAMALAR: yama aylari < delik ayi mevcut tppd_* dosyalariyla BIREBIR ayni (assert); USD serisi de oyle.
Mevcut tppd_* dosyalarina YAZILMAZ; yalnizca tppdyama_* dosyalari yazilir.

KASA: Betik 2025-04-01 ve sonrasi icin fiyat DEGERI yazdirmaz; yalnizca tarih/sayi. Kasa oncesi uyum istatistikleri
2023-01-01..2024-12-31 ortak donemi icindir.
Calistirma: python src/veri/tppd_yama.py [--yenile]
"""
from __future__ import annotations
import argparse, importlib.util, re, time
from datetime import date
from pathlib import Path
import numpy as np, pandas as pd, requests
from bs4 import BeautifulSoup

KOK = Path(__file__).resolve().parents[2]
HAM = KOK / "data/ham/po_akaryakit"
OUT = KOK / "data/islenmis"
URL = "https://www.petrolofisi.com.tr/Fuel/Search"
ESIK_GUN = 60
KASA = pd.Timestamp("2025-04-01")      # yalnizca deger yazdirmama kurali icin (ayarlar.json'a dokunulmaz)
UYUM = (pd.Timestamp("2023-01-01"), pd.Timestamp("2024-12-31"))
URUN = {"benzin": "benzin", "motorin": "motorin_max"}   # TPPD urunu -> PO sutunu (yama/sinama)
PO_KOLON = {"benzin": "V/Max Kurşunsuz 95", "motorin": "V/Pro Diesel", "motorin_max": "V/Max Diesel"}


def tppd_modul():
    sp = importlib.util.spec_from_file_location("tppd_akaryakit", KOK / "src/veri/tppd_akaryakit.py")
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


def po_indir(bas: date, bit: date, yenile: bool) -> Path:
    f = HAM / f"istanbul_avrupa_{bas:%Y%m%d}_{bit:%Y%m%d}.html"
    if f.exists() and not yenile:
        return f
    p = dict(template=3, cityId=34, districtId="03431", startDate=bas.strftime("%d.%m.%Y"), endDate=bit.strftime("%d.%m.%Y"))
    for i in range(4):
        try:
            r = requests.post(URL, data=p, headers={"User-Agent": "Mozilla/5.0 altveri-lab"}, timeout=90)
            if r.status_code == 200 and "<table" in r.text:
                f.write_bytes(r.content); time.sleep(1); return f
        except requests.RequestException:
            pass
        time.sleep(2 ** i)
    raise SystemExit(f"PO indirilemedi: {p}")


def po_ayristir(f: Path) -> pd.DataFrame:
    s = BeautifulSoup(f.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    t = s.find("table")
    hd = [th.get_text(strip=True) for th in t.find_all("th")]
    idx = {k: hd.index(v) for k, v in PO_KOLON.items()}
    satir = []
    for tr in t.find("tbody").find_all("tr"):
        td = tr.find_all("td")
        r = {"tarih": pd.to_datetime(td[0].get_text(strip=True), format="%d.%m.%Y")}
        for k, i in idx.items():
            sp = td[i].find("span", class_="with-tax")
            try: r[k] = float(sp.get_text(strip=True))
            except (ValueError, AttributeError): r[k] = np.nan
        satir.append(r)
    return pd.DataFrame(satir)


def aylik(g: pd.Series) -> pd.Series:
    m = g.groupby(g.index.to_period("M")).mean(); m.index = m.index.to_timestamp()
    return m[m.index >= "2011-01-01"].round(4)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--yenile", action="store_true"); a = ap.parse_args()
    HAM.mkdir(parents=True, exist_ok=True)
    bugun = date.today()
    # --- PO ham (yillik parcalar) ---
    parc = [po_ayristir(po_indir(date(2011, 1, 1) if y == 2011 else date(y, 1, 1), min(date(y, 12, 31), bugun), a.yenile))
            for y in range(2011, bugun.year + 1)]
    po = pd.concat(parc).drop_duplicates("tarih", keep="last").sort_values("tarih").set_index("tarih")
    tum = pd.date_range(po.index.min(), po.index.max())
    print(f"PO satir: {len(po)} | {po.index.min().date()} -> {po.index.max().date()} | eksik gun: {len(tum.difference(po.index))}",
          "| eksik gun (2019+):", len(tum[tum >= '2019-01-01'].difference(po.index)))
    pog = po.reindex(pd.date_range(po.index.min(), pd.Timestamp(bugun))).ffill()
    # --- TPPD ---
    T = tppd_modul()
    d = pd.concat([T.ayristir(f) for f in sorted(T.HAM.glob("*.html"))]).drop_duplicates("tarih", keep="last").sort_values("tarih").set_index("tarih")
    d["motorin"] = d.motorin_b
    gun = pd.date_range(d.index.min(), pd.Timestamp(bugun))
    tg = d[["benzin", "motorin"]].reindex(gun).ffill()
    # --- delik tespiti ---
    kayit = d.index[d.index >= "2025-01-01"]
    aralik = pd.Series(kayit[1:] - kayit[:-1], index=kayit[1:]).dt.days
    buyuk = aralik[aralik > ESIK_GUN]
    assert len(buyuk) == 1, f"tek delik bekleniyordu, bulunan: {len(buyuk)}"
    g1 = buyuk.index[0]; g0 = g1 - pd.Timedelta(days=int(buyuk.iloc[0]))
    assert g0 in d.index
    print(f"TPPD delik: son ortak kayit {g0.date()} -> ilk yeni kayit {g1.date()} ({int(buyuk.iloc[0])} gun)")
    # --- PO'da degisiklik tarihleri (delik penceresi; yalnizca tarih/sayi) ---
    for k in ("benzin", "motorin_max"):
        s = po[k].dropna(); ch = s.index[s.diff().fillna(0) != 0]
        w = ch[(ch > g0) & (ch < g1)]
        print(f"PO {k}: delik icinde degisiklik sayisi={len(w)}; tarihler=", [str(x.date()) for x in w])
        onc = ch[(ch >= '2019-01-01') & (ch <= g0)]; ara = pd.Series(onc[1:] - onc[:-1]).dt.days
        print(f"PO {k}: 2019..{g0.date()} degisiklik={len(onc)}, ardisik aralik max={int(ara.max())} gun, medyan={int(ara.median())}")
    # --- kasa oncesi uyum (2023-2024) ---
    u0, u1 = UYUM
    for k, pk in (("benzin", "benzin"), ("motorin", "motorin"), ("motorin", "motorin_max")):
        x = np.log(pog[pk][u0:u1]); y = np.log(tg[k][u0:u1])
        lr = x - y
        dx, dy = x.diff().dropna(), y.diff().dropna()
        mx = np.log(aylik(pog[pk][:u1]))[u0:u1]; my = np.log(aylik(tg[k][:u1]))[u0:u1]
        tch = set(d.index[(d.index >= u0) & (d.index <= u1) & (d[k if k != 'motorin' else 'motorin'].diff() != 0)])
        pch = pog[pk][u0:u1].diff().fillna(0); pch = set(pch.index[pch != 0])
        es = sum(any((t + pd.Timedelta(days=j)) in pch for j in (-1, 0, 1)) for t in tch)
        print(f"UYUM {k} <- PO {pk} ({u0.year}-{u1.year}): gunluk log-duzey farki ort={lr.mean():.4f} sd={lr.std():.4f}; "
              f"gunluk log-degisim korelasyonu={dx.corr(dy):.3f}; aylik log-degisim korel.={mx.diff().corr(my.diff()):.3f}; "
              f"TPPD degisiklik gunlerinin PO'da +-1 gun eslesmesi={es}/{len(tch)}")
    # --- sahte-delik geriye donuk sinama (kasa oncesi, 132 gunluk pencereler) ---
    L = int(buyuk.iloc[0])
    for k, pk in URUN.items():
        hatalar, uc = [], []
        for bas in pd.date_range("2022-01-01", pd.Timestamp("2024-12-31") - pd.Timedelta(days=L + 1), freq="30D"):
            e = bas + pd.Timedelta(days=L)
            ref = tg[k]; ya = ref.copy()
            gunler = ya.index[(ya.index > bas) & (ya.index < e)]
            ya[gunler] = ref[bas] * pog[pk][gunler] / pog[pk][bas]
            m1, m0 = aylik(ya[:e]), aylik(ref[:e])
            ay = m0.index[(m0.index > bas.to_period("M").to_timestamp()) & (m0.index + pd.offsets.MonthEnd(0) < e)]
            hatalar += list((m1[ay] / m0[ay] - 1).abs()); uc.append(abs(ya[e - pd.Timedelta(days=1)] / ref[e - pd.Timedelta(days=1)] - 1))
        print(f"SINAMA {k}: {len(uc)} sahte delik ({L} gun, 2022-2024); aylik ort. mutlak % hata medyan={np.median(hatalar)*100:.2f} "
              f"p90={np.percentile(hatalar,90)*100:.2f} maks={max(hatalar)*100:.2f}; delik-sonu gun hatasi medyan={np.median(uc)*100:.2f} maks={max(uc)*100:.2f}")
    # --- yama ---
    yama = tg.copy()
    gunler = yama.index[(yama.index > g0) & (yama.index < g1)]
    for k, pk in URUN.items():
        ham = po[pk].reindex(pd.date_range(g0, g1))
        assert ham.notna().sum() >= len(ham) - 1, f"PO {pk} delik penceresinde bos (ffill ile yapay seri olusur)"
        assert po[pk].dropna().index.max() >= g1
        yama.loc[gunler, k] = tg.loc[g0, k] * pog.loc[gunler, pk] / pog.loc[g0, pk]
    assert (yama.loc[:g0] == tg.loc[:g0]).all().all() and (yama.loc[g1:] == tg.loc[g1:]).all().all()
    print(f"yamalanan gun sayisi: {len(gunler)} ({gunler.min().date()} -> {gunler.max().date()})")
    ilk_ay = g0.to_period("M").to_timestamp()
    sonuc = {}
    for k, ad in (("benzin", "benzin95"), ("motorin", "motorin")):
        m = aylik(yama[k]); eski = pd.read_csv(OUT / f"tppd_{ad}_istanbulavrupa_aylik.csv", parse_dates=["tarih"]).set_index("tarih")["deger"]
        oncesi = m.index < ilk_ay
        assert m.index.equals(eski.index), "ay kumeleri farkli"
        assert np.allclose(m[oncesi].values, eski[oncesi].values, atol=1e-4, rtol=0) and oncesi.sum() > 100, "yama oncesi donem birebir degil"
        print(f"{ad}: {len(m)} ay, {m.index.min():%Y-%m}..{m.index.max():%Y-%m}; {ilk_ay:%Y-%m} oncesi {oncesi.sum()} ay birebir ayni (assert ok); "
              f"degisen ay sayisi={int((~np.isclose(m.values, eski.values, atol=1e-4, rtol=0)).sum())}")
        pd.DataFrame({"tarih": m.index.strftime("%Y-%m-%d"), "deger": m.values}).to_csv(OUT / f"tppdyama_{ad}_istanbulavrupa_aylik.csv", index=False)
        sonuc[k] = m
    # --- USD (akaryakit_usd.py ile ayni tanim; o betik degistirilmedi) ---
    usd = pd.read_csv(OUT / "tcmb_usdtry_turkiye_aylik.csv", parse_dates=["tarih"]).set_index("tarih")["deger"]
    s = (((sonuc["benzin"] + sonuc["motorin"]) / 2) / usd).dropna()
    s = s[s.index < pd.Timestamp(bugun.replace(day=1))]
    eksik = pd.date_range(s.index.min(), s.index.max(), freq="MS").difference(s.index)
    assert len(eksik) == 0 and (s > 0).all()
    eski = pd.read_csv(OUT / "tppd_akaryakitusd_istanbulavrupa_aylik.csv", parse_dates=["tarih"]).set_index("tarih")["deger"]
    assert s.index.equals(eski.index)
    oncesi = s.index < ilk_ay
    assert np.allclose(s[oncesi].values, eski[oncesi].values, atol=2e-6, rtol=0), "USD yama oncesi birebir degil"
    pd.DataFrame({"tarih": s.index.strftime("%Y-%m-%d"), "deger": s.values}).to_csv(
        OUT / "tppdyama_akaryakitusd_istanbulavrupa_aylik.csv", index=False, float_format="%.6f")
    print(f"akaryakitusd yama: {s.index.min():%Y-%m}..{s.index.max():%Y-%m} n={len(s)}; {ilk_ay:%Y-%m} oncesi {oncesi.sum()} ay birebir (assert ok)")

    (HAM / "KAYNAK.txt").write_text(
        "Kaynak: Petrol Ofisi A.S. 'Gecmis Akaryakit Fiyatlari' sayfasi\n"
        "URL: https://www.petrolofisi.com.tr/arsiv-fiyatlari (sayfanin kendi ajax uc noktasi: POST https://www.petrolofisi.com.tr/Fuel/Search,\n"
        "  template=3, cityId=34, districtId=03431 'ISTANBUL (AVRUPA)', startDate/endDate=dd.mm.yyyy; yillik parcalar)\n"
        f"Indirme tarihi: {bugun:%Y-%m-%d} (src/veri/tppd_yama.py ile)\n"
        "Lisans: kamuya acik sayfa; acik lisans belirtilmemis, yalnizca arastirma amacli. Resmi EPDK verisi degil, dagitici pompa fiyati arsividir.\n"
        "Amac: TPPD arsivindeki 2025-12 -> 2026-04 deligini yamalamak icin GUNLUK ORANSAL degisim kaynagi (duzeyi TPPD belirler).\n"
        "Sutunlar: V/Max Kursunsuz 95 (benzin), V/Pro Diesel (standart motorin), V/Max Diesel (yalnizca uyum karsilastirmasi); KDV dahil, TL/LT.\n", encoding="utf-8")


if __name__ == "__main__":
    main()
