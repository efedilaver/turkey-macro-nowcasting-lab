"""TÜİK Sanayi Üretim Endeksi, imalat (C) alt endeksi: H-001 / H-003 hedef serisi.

Üretilen dosyalar (data/islenmis/):
  tuik_sueimalat_turkiye_aylik.csv        ANA HEDEF. Ilk açıklanan: her ay t için, t'nin ilk
                                          yayımlandığı aylık bültendeki "imalat sanayi sektörü
                                          endeksi, bir önceki yılın aynı ayına göre" yüzde
                                          değişimi (takvim etkisinden arındırılmış endeks;
                                          TÜİK bu değeri aynı baskıdaki t ve t-12 düzeylerinden
                                          hesaplar, 1 ondalığa yuvarlı). Birim: yüzde puan.
                                          Test: --donusum duzey --gosterge-donusum yoy
  tuik_sueimalatrevize_turkiye_aylik.csv  Güncel (revize) düzey: EVDS TP.TSANAYTKVM2021.C
                                          (imalat, takvim etkisinden arındırılmış, 2021=100).
                                          Test: --donusum yoy (yalnız karşılaştırma/yedek).
  tuik_sueimalatbaski_turkiye_aylik.csv   Denetim izi: bülten kimliği, yayın tarihi, baz yılı,
                                          revize serinin yoy'u ve fark.

Ham veri (data/ham/tuik_sue/): bülten JSON'ları (bulten/) ve EVDS yanıtları.

Kaynaklar:
  TÜİK Veri Portalı haber bülteni API'si (anahtarsız): https://veriportali.tuik.gov.tr/api/tr/press
  TCMB EVDS3 (anahtar .env: EVDS_API_KEY): serileri revize düzey ve tanı amaçlıdır.

Kullanım:
    python src/veri/tuik_sue_imalat.py [--yenile] [--baslangic YYYY-MM]
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from dotenv import dotenv_values

KOK = Path(__file__).resolve().parents[2]
HAM = KOK / "data" / "ham" / "tuik_sue"
BULTEN_DIZIN = HAM / "bulten"
ISLENMIS = KOK / "data" / "islenmis"

PORTAL = "https://veriportali.tuik.gov.tr"
EVDS = "https://evds3.tcmb.gov.tr/igmevdsms-dis/"
EVDS_REVIZE = "TP.TSANAYTKVM2021.C"   # imalat, takvim etkisinden arındırılmış (tercih 1)
EVDS_ARINDIRILMAMIS = "TP.TSANAY2021.C"  # yalnız tanı için (takvim etkisi ayrımı)
ZAMAN_ASIMI = 90
BEKLE = 0.25

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
         "Eylül", "Ekim", "Kasım", "Aralık"]

# Varsayılan ilk bülten ayı: 2013-03. Gerekçe: 2013-01 baz yılı değişikliği bültenidir (2010=100);
# 2013-02 bülteni yıllık değişimin takvim arındırması hakkında bir şey söylemez ve imalat değeri (7,0)
# revize ARINDIRILMAMIŞ yoy'a eşittir (2012 artık yıl). 2013-03'ten itibaren bültenler yıllık değişimi
# açıkça "takvim etkisinden arındırılmış" diye tanımlar. H-001 testi 2017-01'den başlar.
VARSAYILAN_BASLANGIC = (2013, 3)


# ------------------------------------------------------------------ HTTP
def _get(url: str, **kw) -> requests.Response:
    son = None
    for deneme in range(4):
        try:
            r = requests.get(url, timeout=ZAMAN_ASIMI, **kw)
            if r.status_code == 200:
                return r
            son = f"HTTP {r.status_code}"
        except requests.RequestException as hata:
            son = type(hata).__name__
        time.sleep(2 * (deneme + 1))
    raise RuntimeError(f"{url.split('?')[0]} alınamadı: {son}")


def portal_json(yol: str) -> dict:
    r = _get(PORTAL + yol, headers={"User-Agent": "altveri-lab",
                                    "X-Requested-With": "XMLHttpRequest",
                                    "Accept": "application/json"})
    j = r.json()
    if j.get("isError"):
        raise RuntimeError(f"{yol}: {j.get('message')}")
    return j["data"]


# ------------------------------------------------------------------ bültenler
def donem_coz(donem: str):
    p = donem.split()
    if len(p) == 2 and p[0] in AYLAR and p[1].isdigit():
        return int(p[1]), AYLAR.index(p[0]) + 1
    return None  # üç aylık ("IV. Dönem 2005") vb.


def en_yeni_bulten_kimligi() -> str:
    liste = portal_json("/api/tr/press")
    adaylar = [x for x in liste if x["title"].strip() == "Sanayi Üretim Endeksi"]
    if len(adaylar) != 1:
        raise RuntimeError(f"'Sanayi Üretim Endeksi' bülteni listede {len(adaylar)} kez geçiyor")
    return str(adaylar[0]["id"])


def bulten_al(kimlik: str, yenile: bool) -> dict:
    """Bülten JSON'unu önbellekten ya da API'den al. Ham dosya yazıldıktan sonra
    değiştirilmez; bülten sayfaları yayımdan sonra sabittir."""
    BULTEN_DIZIN.mkdir(parents=True, exist_ok=True)
    onbellek = list(BULTEN_DIZIN.glob(f"*_{kimlik}.json"))
    if onbellek and not yenile:
        return json.loads(onbellek[0].read_text(encoding="utf-8"))
    d = portal_json(f"/api/tr/press/{kimlik}")
    donem = donem_coz(d["period"])
    ad = f"{donem[0]}-{donem[1]:02d}" if donem else d["period"].replace(" ", "_")
    (BULTEN_DIZIN / f"{ad}_{kimlik}.json").write_text(
        json.dumps(d, ensure_ascii=False), encoding="utf-8")
    time.sleep(BEKLE)
    return d


def bultenleri_topla(baslangic: tuple[int, int], yenile: bool) -> dict:
    """Arşiv zinciri: her bülten kendinden önceki 12 bülteni listeler. En yeniden
    başlayıp 12'şer geriye atlar, sonra aradaki bültenleri indirir."""
    indeks: dict[tuple[int, int], str] = {}
    guncel = en_yeni_bulten_kimligi()
    cur = guncel
    zincir_yenile = yenile
    while cur:
        d = bulten_al(cur, yenile=zincir_yenile or cur == guncel)
        donem = donem_coz(d["period"])
        if donem:
            indeks[donem] = cur
        onceki = [x for x in d["previousPresses"] if donem_coz(x["period"])]
        for x in onceki:
            indeks.setdefault(donem_coz(x["period"]), x["url"].rsplit("/", 1)[-1])
        if not onceki or min(donem_coz(x["period"]) for x in onceki) <= baslangic:
            break
        cur = min(onceki, key=lambda x: donem_coz(x["period"]))["url"].rsplit("/", 1)[-1]
    sonuc = {}
    for donem in sorted(indeks):
        if donem >= baslangic:
            sonuc[donem] = bulten_al(indeks[donem], yenile=False)
    return sonuc


def metin_temizle(icerik: str) -> str:
    t = html.unescape(re.sub(r"<[^>]+>", " ", icerik or ""))
    return re.sub(r"\s+", " ", t.replace("﻿", " ")).strip()


YOY_ISARET = re.compile(r"yılın aynı ayına göre|yıllık")
AYLIK_ISARET = re.compile(r"bir önceki aya göre|aylık")
IMALAT = re.compile(r"imalat\s+sanayi\s+sektörü\s+endeksi")
YUZDE = re.compile(r"\s*%\s*(\d+(?:,\d+)?)")
FIIL = re.compile(r"(art|azal|düş|geril)", re.I)  # yükseliş / düşüş sözcük kökleri
SABIT = re.compile(r"\s*(aynı kaldı|değişmedi)")


def imalat_yoy_ayikla(t: str):
    """Bülten metninden imalat sektörünün YILLIK değişimini (yüzde) çıkarır.
    Dönen: (değer | None, not). Aylık cümleyle karışmasın diye her 'imalat sanayi
    sektörü endeksi' ifadesinden önceki son yıllık/aylık işaretine bakılır."""
    bulunan = []
    for m in IMALAT.finditer(t):
        onceki = t[: m.start()]
        y = [x.end() for x in YOY_ISARET.finditer(onceki)]
        a = [x.end() for x in AYLIK_ISARET.finditer(onceki)]
        bag = "yoy" if (y and (not a or max(y) > max(a))) else "mom"
        if bag != "yoy":
            continue
        if SABIT.match(t[m.end(): m.end() + 40]):  # "... endeksi aynı kaldı" = %0,0
            bulunan.append((0.0, "aynı kaldı"))
            continue
        p = YUZDE.match(t[m.end(): m.end() + 40])
        if not p:
            continue
        f = FIIL.search(t[m.end() + p.end(): m.end() + p.end() + 220])
        if not f:
            bulunan.append((None, "yön fiili yok"))
            continue
        deger = float(p.group(1).replace(",", "."))
        bulunan.append((deger if f.group(1).lower() == "art" else -deger, ""))
    if not bulunan:
        return None, "imalat yoy cümlesi bulunamadı"
    if len({b[0] for b in bulunan}) > 1:
        return None, f"çelişkili: {bulunan}"
    return bulunan[0]


# ------------------------------------------------------------------ EVDS
def evds_cek(kod: str, anahtar: str, ham_yaz: bool = True) -> pd.Series:
    r = _get(EVDS + f"series={kod}&startDate=01-01-1986&endDate=31-12-2026&type=json",
             headers={"User-Agent": "altveri-lab", "key": anahtar})
    j = r.json()
    if len(j["items"]) >= 1000 or j.get("totalCount") not in (None, len(j["items"])):
        raise RuntimeError(f"EVDS {kod}: satır sayısı tutarsız/1000 sınırı "
                           f"(totalCount={j.get('totalCount')}, gelen={len(j['items'])})")
    if ham_yaz:
        HAM.mkdir(parents=True, exist_ok=True)
        (HAM / f"evds_{kod}.json").write_text(json.dumps(j, ensure_ascii=False), encoding="utf-8")
    alan = kod.replace(".", "_")
    kayit = {}
    for it in j["items"]:
        v = it.get(alan)
        if v in (None, ""):
            continue
        y, a = it["Tarih"].split("-")
        kayit[pd.Timestamp(int(y), int(a), 1)] = float(v)
    return pd.Series(kayit).sort_index()


# ------------------------------------------------------------------ ana akış
def kaynak_yaz(n_bulten: int, ilk: str, son: str) -> None:
    HAM.mkdir(parents=True, exist_ok=True)
    (HAM / "KAYNAK.txt").write_text(
        "TÜİK Sanayi Üretim Endeksi, imalat (C) alt endeksi\n"
        f"Son çalıştırma/indirme tarihi: {date.today().isoformat()}\n\n"
        "1) bulten/*.json: TÜİK Veri Portalı haber bülteni API'si (anahtarsız)\n"
        "   https://veriportali.tuik.gov.tr/api/tr/press/<kimlik>  (başlık: X-Requested-With: XMLHttpRequest)\n"
        f"   {n_bulten} aylık 'Sanayi Üretim Endeksi' bülteni, {ilk} .. {son}.\n"
        "   Her dosya o bültenin API yanıtıdır; 'content' alanı yayın günündeki metindir ve\n"
        "   ilk açıklanan yıllık değişimin kaynağıdır. Lisans: TÜİK verisi, kaynak gösterilerek\n"
        "   kullanım (TÜİK telif/kullanım koşulları); yeniden dağıtım yapılmaz.\n\n"
        f"2) evds_{EVDS_REVIZE}.json: TCMB EVDS3, imalat SÜE takvim etkisinden arındırılmış\n"
        "   (veri grubu bie_tsanaytkvm2021), güncel/revize düzey, 2021=100.\n"
        f"3) evds_{EVDS_ARINDIRILMAMIS}.json: aynı grup, arındırılmamış imalat (yalnız tanı).\n"
        "   https://evds3.tcmb.gov.tr/igmevdsms-dis/series=<KOD>&startDate=..&endDate=..&type=json\n"
        "   Anahtar .env içindeki EVDS_API_KEY'den okunur; bu dosyaya yazılmaz.\n"
        "   Lisans: EVDS kullanım koşulları, kaynak gösterilerek kullanım.\n\n"
        "Not: bulten/ klasöründe önceki çalıştırmalardan kalan, başlangıç ayından önceki (2013-01/02)\n"
        "   dosyalar bulunabilir; çıktıya yalnız başlangıç ayından sonraki bültenler girer.\n"
        "Ham dosyalar elle değiştirilmez. Betik: src/veri/tuik_sue_imalat.py\n",
        encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--yenile", action="store_true", help="önbellekteki bültenleri yeniden indir")
    ap.add_argument("--baslangic", default="%04d-%02d" % VARSAYILAN_BASLANGIC,
                    help="ilk bülten ayı (YYYY-MM)")
    args = ap.parse_args()
    bas = tuple(int(x) for x in args.baslangic.split("-"))

    anahtar = dotenv_values(KOK / ".env").get("EVDS_API_KEY", "").strip()
    if not anahtar:
        print("EVDS_API_KEY .env içinde tanımlı değil", file=sys.stderr)
        return 1

    print("Bültenler toplanıyor ...", flush=True)
    bultenler = bultenleri_topla(bas, args.yenile)
    print(f"  {len(bultenler)} aylık bülten: {min(bultenler)} .. {max(bultenler)}")

    satirlar, sorunlar = [], []
    for (y, a), d in sorted(bultenler.items()):
        t = metin_temizle(d["content"])
        deger, not_ = imalat_yoy_ayikla(t)
        baz = re.search(r"\((\d{4})=100", t)
        satirlar.append({
            "tarih": f"{y}-{a:02d}-01",
            "deger": deger,
            "bulten_kimlik": d["id"],
            "yayin_tarihi": d["date"][:10],
            "baz_yili": baz.group(1) if baz else "",
            "metinde_takvim_ibaresi": int("takvim etkisinden arındırılmış" in t.lower()),
            "not": not_,
        })
        if deger is None:
            sorunlar.append((f"{y}-{a:02d}", d["id"], not_))
    df = pd.DataFrame(satirlar)

    cal = evds_cek(EVDS_REVIZE, anahtar)
    unadj = evds_cek(EVDS_ARINDIRILMAMIS, anahtar)
    df["tarih_ts"] = pd.to_datetime(df["tarih"])
    yoy_cal = 100 * (cal / cal.shift(12) - 1)
    yoy_un = 100 * (unadj / unadj.shift(12) - 1)
    df["revize_yoy"] = df["tarih_ts"].map(yoy_cal).round(2)
    df["revize_arindirilmamis_yoy"] = df["tarih_ts"].map(yoy_un).round(2)
    df["fark_revize"] = (df["deger"] - df["revize_yoy"]).round(2)

    ISLENMIS.mkdir(parents=True, exist_ok=True)
    # 1) ana hedef: ilk açıklanan yoy (eksik değerleri yazma)
    df.dropna(subset=["deger"])[["tarih", "deger"]].to_csv(
        ISLENMIS / "tuik_sueimalat_turkiye_aylik.csv", index=False)
    # 2) denetim izi
    df.drop(columns=["tarih_ts"]).to_csv(
        ISLENMIS / "tuik_sueimalatbaski_turkiye_aylik.csv", index=False)
    # 3) revize düzey (kırpma yok)
    pd.DataFrame({"tarih": cal.index.strftime("%Y-%m-%d"), "deger": cal.values}).to_csv(
        ISLENMIS / "tuik_sueimalatrevize_turkiye_aylik.csv", index=False)

    kaynak_yaz(len(bultenler), "%04d-%02d" % min(bultenler), "%04d-%02d" % max(bultenler))

    ana = df.dropna(subset=["deger"])
    print(f"Ana hedef: {len(ana)} gözlem, {ana['tarih'].iloc[0]} .. {ana['tarih'].iloc[-1]}")
    print(f"Revize düzey: {len(cal)} gözlem, {cal.index[0].date()} .. {cal.index[-1].date()}")
    if sorunlar:
        print("AYRIŞTIRILAMAYAN bültenler:")
        for s in sorunlar:
            print("  ", s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
