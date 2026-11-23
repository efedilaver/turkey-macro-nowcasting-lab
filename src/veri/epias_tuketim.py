"""EPİAŞ Şeffaflık Platformu gerçek zamanlı tüketim: iş günü aylık ortalaması (H-001).

Akış: saatlik tüketim (MWh) -> günlük toplam (yalnız 24 saati tam günler) -> iş günü
filtresi -> aylık ortalama (MWh/gün). Yalnız tamamlanmış aylar yazılır.

Çıktılar (data/islenmis/):
  epias_tuketimisgunu_turkiye_aylik.csv        tarih,deger (ayın ilk günü; MWh/iş günü)
  epias_tuketimisgunu_turkiye_aylik_kapsam.csv beklenen/geçerli iş günü, eksik saat sayısı
  evds_tuketimisgunu_turkiye_aylik.csv         KARŞILAŞTIRMA (kartın ana göstergesi değil): aynı iş
                                               günü mantığı, EVDS TP.ELEKTUKETIM.TKT1 (TEİAŞ günlük
                                               tüketim = üretim + ithalat - ihracat) üzerinden
  evds_tuketimisgunu_turkiye_aylik_kapsam.csv  aynısının kapsamı

Ham veri (data/ham/epias/): aylık API yanıtları consumption_YYYY-MM.json.
Geçmiş ayların yeniden indirilmesinde değişen saatler guncelleme_gunlugu.csv'ye yazılır
(kart riski: geçmiş gerçek zamanlı değerlerin sonradan güncellenmesi).

İş günü: Pzt-Cum, şunlar hariç: 1 Ocak, 23 Nisan, 1 Mayıs, 19 Mayıs, 15 Temmuz (2017'den),
30 Ağustos, 29 Ekim; Ramazan Bayramı (3 gün) ve Kurban Bayramı (4 gün); arife günleri
(her iki bayramın arifesi ve 28 Ekim; yarım gün olsa da dışarıda tutulur). İdari izin ve
köprü günleri çıkarılmaz (kart kararı).

Kimlik bilgileri .env içinde EPIAS_KULLANICI / EPIAS_SIFRE; bilet çıktıya yazılmaz.

Kullanım:
    python src/veri/epias_tuketim.py [--yenile] [--tani]
"""
from __future__ import annotations

import argparse
import calendar
import csv
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
from dotenv import dotenv_values

KOK = Path(__file__).resolve().parents[2]
HAM = KOK / "data" / "ham" / "epias"
ISLENMIS = KOK / "data" / "islenmis"

URL_BILET = "https://giris.epias.com.tr/cas/v1/tickets"
URL_VERI = "https://seffaflik.epias.com.tr/electricity-service/v1/consumption/data/realtime-consumption"
EVDS = "https://evds3.tcmb.gov.tr/igmevdsms-dis/"
UA = "altveri-lab"
ILK_AY = (2016, 1)          # veri 2015-12-31'de başlar (tek gün); ilk tam ay 2016-01
BILET_OMRU_SN = 90 * 60     # bilet 2 saat geçerli; 90 dakikada yenile
MIN_GECERLI_ORAN = 0.8      # ayın iş günlerinin en az bu oranı tam olmalı

# ----------------------------------------------------------------- tatil tablosu
# Kaynak: Nager.Date Public Holidays API (https://date.nager.at/api/v3/PublicHolidays/<yıl>/TR,
# 2026-10-29'da alındı), 2016 Ramazan Bayramı tarihi ayrıca haber kaynaklarıyla doğrulandı
# (5-7 Temmuz, arife 4 Temmuz). `--tani` tabloyu Nager ile yeniden karşılaştırır.
# Biçim: yıl -> (ay, gün) bayramın 1. günü. Ramazan 3 gün, Kurban 4 gün sürer.
RAMAZAN_1 = {2016: (7, 5), 2017: (6, 25), 2018: (6, 15), 2019: (6, 4), 2020: (5, 24),
             2021: (5, 13), 2022: (5, 2), 2023: (4, 21), 2024: (4, 10), 2025: (3, 30),
             2026: (3, 20)}
KURBAN_1 = {2016: (9, 12), 2017: (9, 1), 2018: (8, 21), 2019: (8, 11), 2020: (7, 31),
            2021: (7, 20), 2022: (7, 9), 2023: (6, 28), 2024: (6, 16), 2025: (6, 6),
            2026: (5, 27)}
SABIT_TATIL = [(1, 1), (4, 23), (5, 1), (5, 19), (8, 30), (10, 29)]  # 15 Temmuz ayrıca (2017'den)
SABIT_ARIFE = [(10, 28)]
TABLO_YILLARI = sorted(RAMAZAN_1)


def tatil_gunleri(yil: int) -> dict[date, str]:
    if yil not in RAMAZAN_1 or yil not in KURBAN_1:
        raise ValueError(f"{yil} için bayram tarihi tabloda yok; tabloyu genişletin "
                         f"(kapsanan: {TABLO_YILLARI[0]}-{TABLO_YILLARI[-1]})")
    t: dict[date, str] = {}
    for a, g in SABIT_TATIL:
        t[date(yil, a, g)] = "resmi tatil"
    if yil >= 2017:
        t[date(yil, 7, 15)] = "resmi tatil (15 Temmuz)"
    for a, g in SABIT_ARIFE:
        t[date(yil, a, g)] = "arife (28 Ekim)"
    for ad, tablo, gun in (("Ramazan Bayramı", RAMAZAN_1, 3), ("Kurban Bayramı", KURBAN_1, 4)):
        bas = date(yil, *tablo[yil])
        t.setdefault(bas - timedelta(days=1), f"arife ({ad})")
        for i in range(gun):
            t[bas + timedelta(days=i)] = ad
    return t


def is_gunu_mu(d: date, tatiller: dict[date, str]) -> bool:
    return d.weekday() < 5 and d not in tatiller


# ----------------------------------------------------------------- API
class Oturum:
    def __init__(self, kullanici: str, sifre: str):
        self._k, self._s = kullanici, sifre
        self._tgt, self._zaman = None, 0.0

    def bilet(self, zorla: bool = False) -> str:
        if zorla or not self._tgt or time.time() - self._zaman > BILET_OMRU_SN:
            r = requests.post(URL_BILET, data={"username": self._k, "password": self._s},
                              headers={"Accept": "text/plain", "User-Agent": UA}, timeout=30)
            if r.status_code != 201 or not r.text.startswith("TGT-"):
                raise RuntimeError(f"EPİAŞ bilet alınamadı: HTTP {r.status_code}")
            self._tgt, self._zaman = r.text.strip(), time.time()
        return self._tgt

    def tuketim(self, bas: date, bit: date) -> dict:
        """[bas, bit] günleri arası saatlik tüketim. Ofset yerel saate göre verilir:
        2016-03-27 öncesi +02:00, sonrası +03:00 (yanlış ofset ay sonu gününü kaybettirir)."""
        govde = {"startDate": f"{bas.isoformat()}T00:00:00{ofset(bas)}",
                 "endDate": f"{bit.isoformat()}T00:00:00{ofset(bit)}"}
        son_hata = ""
        for deneme in range(4):
            try:
                r = requests.post(URL_VERI, json=govde, timeout=180, headers={
                    "TGT": self.bilet(zorla=deneme == 1), "Content-Type": "application/json",
                    "Accept": "application/json", "User-Agent": UA})
                if r.status_code == 200 and "items" in r.json():
                    return r.json()
                son_hata = f"HTTP {r.status_code}"
            except (requests.RequestException, ValueError) as hata:
                son_hata = type(hata).__name__
            time.sleep(2 * (deneme + 1))
        raise RuntimeError(f"{bas}..{bit} alınamadı: {son_hata}")


def ofset(d: date) -> str:
    return "+02:00" if d < date(2016, 3, 27) else "+03:00"


# ----------------------------------------------------------------- ham veri
def aylar(son: date, ilk_ay=ILK_AY):
    y, m = ilk_ay
    while (y, m) <= (son.year, son.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def ay_tam_mi(yanit: dict, y: int, m: int) -> bool:
    """Ham yanıt ayın son gününün 23:00 saatine kadar geliyor mu ve saat sayısı makul mü?"""
    it = yanit["items"]
    son_gun = calendar.monthrange(y, m)[1]
    return bool(it) and it[-1]["date"].startswith(f"{y}-{m:02d}-{son_gun:02d}T23:00") \
        and len(it) >= son_gun * 24 - 1


def ham_indir(oturum: Oturum, dun: date, yenile: bool) -> list[Path]:
    HAM.mkdir(parents=True, exist_ok=True)
    gunluk = HAM / "guncelleme_gunlugu.csv"
    dosyalar = []
    for y, m in aylar(dun):
        yol = HAM / f"consumption_{y}-{m:02d}.json"
        tam_ay = (y, m) < (dun.year, dun.month) or dun == date(y, m, calendar.monthrange(y, m)[1])
        eski = json.loads(yol.read_text(encoding="utf-8")) if yol.exists() else None
        if eski is not None and not yenile and tam_ay and ay_tam_mi(eski, y, m):
            dosyalar.append(yol)
            continue
        son_gun = min(date(y, m, calendar.monthrange(y, m)[1]), dun)
        yeni = oturum.tuketim(date(y, m, 1), son_gun)
        if eski is not None:  # geçmiş değerler değişti mi?
            e = {x["date"]: x["consumption"] for x in eski["items"]}
            n = {x["date"]: x["consumption"] for x in yeni["items"]}
            ortak = set(e) & set(n)
            fark = [abs((e[k] or 0) - (n[k] or 0)) for k in ortak if e[k] != n[k]]
            if fark or set(e) != set(n):
                yeni_dosya = not gunluk.exists()
                with gunluk.open("a", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    if yeni_dosya:
                        w.writerow(["kontrol_tarihi", "ay", "degisen_saat", "maks_mutlak_fark_mwh",
                                    "eklenen_saat", "kaybolan_saat"])
                    w.writerow([date.today().isoformat(), f"{y}-{m:02d}", len(fark),
                                round(max(fark), 2) if fark else 0, len(set(n) - set(e)),
                                len(set(e) - set(n))])
        yol.write_text(json.dumps(yeni, ensure_ascii=False), encoding="utf-8")
        dosyalar.append(yol)
        time.sleep(0.2)
    return dosyalar


def saatlikleri_oku(dosyalar: list[Path]) -> pd.DataFrame:
    satir = []
    for yol in dosyalar:
        for x in json.loads(yol.read_text(encoding="utf-8"))["items"]:
            satir.append((x["date"], x["consumption"]))
    df = pd.DataFrame(satir, columns=["zaman", "mwh"])
    return df


# ----------------------------------------------------------------- işleme
def aylik_is_gunu(tam: pd.Series, dun: date, tatiller: dict, ilk_ay=ILK_AY, saat_sayisi: pd.Series | None = None):
    """Tam günlük toplamlardan (index: gün) tamamlanmış ayların iş günü ortalaması + kapsam."""
    kapsam, deger = [], {}
    for y, m in aylar(dun, ilk_ay):
        son_gun_ay = date(y, m, calendar.monthrange(y, m)[1])
        if son_gun_ay > dun:  # tamamlanmamış ay
            continue
        gunler = [date(y, m, d) for d in range(1, son_gun_ay.day + 1)]
        beklenen = [d for d in gunler if is_gunu_mu(d, tatiller)]
        gecerli = [d for d in beklenen if pd.Timestamp(d) in tam.index]
        ort = float(tam.loc[[pd.Timestamp(d) for d in gecerli]].mean()) if gecerli else float("nan")
        satir = {"tarih": f"{y}-{m:02d}-01", "is_gunu_beklenen": len(beklenen),
                 "is_gunu_gecerli": len(gecerli)}
        if saat_sayisi is not None:  # gün başına mevcut saat sayısı -> eksik saat toplamı
            satir["eksik_saat_toplam"] = int(sum(24 - saat_sayisi.get(pd.Timestamp(d), 0) for d in gunler))
        kapsam.append(satir)
        if gecerli and len(gecerli) >= MIN_GECERLI_ORAN * len(beklenen):
            deger[f"{y}-{m:02d}-01"] = round(ort, 2)
    return deger, pd.DataFrame(kapsam)


def tatil_tablosu(ilk_yil: int, son_yil: int) -> dict:
    t: dict = {}
    for y in range(ilk_yil, son_yil + 1):
        t.update(tatil_gunleri(y))
    return t


def gunluk_ve_aylik(df: pd.DataFrame, dun: date):
    sorunlar = {}
    sorunlar["yinelenen_zaman"] = int(df["zaman"].duplicated().sum())
    df = df.drop_duplicates("zaman").copy()
    sorunlar["bos_deger"] = int(df["mwh"].isna().sum())
    sorunlar["sifir_veya_negatif"] = int((df["mwh"].fillna(1) <= 0).sum())
    df["gun"] = df["zaman"].str[:10]
    g = df.groupby("gun").agg(toplam=("mwh", "sum"), saat=("mwh", "count"))
    g.index = pd.to_datetime(g.index)
    tam = g[g["saat"] == 24]["toplam"]
    sorunlar["eksik_saatli_gun"] = {d.date().isoformat(): int(s) for d, s in g["saat"].items() if s != 24}
    tatiller = tatil_tablosu(g.index.min().year, g.index.max().year)
    deger, kapsam = aylik_is_gunu(tam, dun, tatiller, saat_sayisi=g["saat"])
    return g, deger, kapsam, sorunlar, tatiller


# ----------------------------------------------------------------- EVDS karşılaştırma serisi
def evds_gunluk(kod: str, anahtar: str) -> pd.Series:
    """EVDS günlük seri; tek istekte en çok 1000 satır döner, bu yüzden 2 yıllık pencereler."""
    HAM.mkdir(parents=True, exist_ok=True)
    seri, ham = {}, []
    for yil in range(ILK_AY[0], date.today().year + 1, 2):
        bas, bit = f"01-01-{yil}", f"31-12-{yil + 1}"
        r = requests.get(EVDS + f"series={kod}&startDate={bas}&endDate={bit}&type=json",
                         headers={"User-Agent": UA, "key": anahtar}, timeout=120)
        r.raise_for_status()
        j = r.json()
        if len(j["items"]) >= 1000:
            raise RuntimeError(f"EVDS {kod} {bas}..{bit}: 1000 satır sınırına dayandı, pencere daralt")
        ham.append(j)
        for it in j["items"]:
            v = it.get(kod.replace(".", "_"))
            if v not in (None, ""):
                seri[pd.to_datetime(it["Tarih"], dayfirst=True)] = float(v)
    (HAM / f"evds_{kod}.json").write_text(json.dumps(ham, ensure_ascii=False), encoding="utf-8")
    return pd.Series(seri).sort_index()


def evds_yedek_uret(anahtar: str, dun: date) -> tuple[dict, pd.DataFrame, pd.Series]:
    tkt = evds_gunluk("TP.ELEKTUKETIM.TKT1", anahtar)
    tatiller = tatil_tablosu(tkt.index.min().year, tkt.index.max().year)
    deger, kapsam = aylik_is_gunu(tkt, min(dun, tkt.index.max().date()), tatiller)
    return deger, kapsam, tkt


def kaynak_yaz(ilk: str, son: str) -> None:
    (HAM / "KAYNAK.txt").write_text(
        "EPİAŞ Şeffaflık Platformu, gerçek zamanlı tüketim (saatlik, MWh)\n"
        f"Son çalıştırma/indirme tarihi: {date.today().isoformat()}\n\n"
        "API: POST https://seffaflik.epias.com.tr/electricity-service/v1/consumption/data/realtime-consumption\n"
        "     gövde {startDate, endDate} (yerel ofsetli), başlık TGT=<bilet>\n"
        "Bilet: POST https://giris.epias.com.tr/cas/v1/tickets (kullanıcı adı/şifre .env'den;\n"
        "       bilet ve şifre hiçbir dosyaya yazılmaz)\n"
        "Belge: https://seffaflik.epias.com.tr/electricity-service/technical/en/index.html\n"
        f"Kapsam: aylık dosyalar consumption_YYYY-MM.json, {ilk} .. {son}. API'de veri\n"
        "        2015-12-31'de başlar (tek gün); ilk tam ay 2016-01.\n"
        "Lisans: EPİAŞ Şeffaflık Platformu kullanım koşulları; kaynak gösterilerek kullanılır.\n"
        "        Yeniden dağıtım yapılmaz.\n"
        "Karşılaştırma: evds_TP.ELEKTUKETIM.TKT1.json = TCMB EVDS3 bie_elektuketim, günlük TEİAŞ\n"
        "        tüketimi (2016-01-01'den; anahtar .env EVDS_API_KEY). Kartın yedek yolu; ana gösterge\n"
        "        EPİAŞ'tır, EVDS yalnız duyarlılık/karşılaştırma içindir. EVDS tek istekte en çok 1000\n"
        "        satır döndürür, bu yüzden 2 yıllık pencerelerle çekilir.\n"
        "Resmi tatil kaynağı: betikteki tablo (src/veri/epias_tuketim.py); Nager.Date API'si\n"
        "        (https://date.nager.at) ile karşılaştırıldı, 2016 Ramazan Bayramı haber kaynaklarıyla.\n"
        "Ham dosyalar elle değiştirilmez. Betik: src/veri/epias_tuketim.py\n",
        encoding="utf-8")


# ----------------------------------------------------------------- tanı
def tani(g: pd.DataFrame, tkt: pd.Series | None) -> None:
    print("\n--- TANI: tatil tablosu ve Nager.Date ---")
    for y in TABLO_YILLARI:
        try:
            r = requests.get(f"https://date.nager.at/api/v3/PublicHolidays/{y}/TR",
                             headers={"User-Agent": UA}, timeout=30)
            nager = {date.fromisoformat(x["date"]) for x in r.json()}
        except (requests.RequestException, ValueError):
            print(f"  {y}: Nager erişilemedi")
            continue
        bizim = {d for d, ad in tatil_gunleri(y).items() if not ad.startswith("arife")}
        print(f"  {y}: Nager'de olup tabloda olmayan={sorted(nager - bizim)} "
              f"tabloda olup Nager'de olmayan={sorted(bizim - nager)}")
    if tkt is None:
        return
    print("\n--- TANI: EPİAŞ günlük toplam / EVDS TP.ELEKTUKETIM.TKT1 (TEİAŞ günlük tüketim), yıllık ---")
    tam = g[g["saat"] == 24]["toplam"]
    o = pd.concat([tam.rename("epias"), tkt.rename("evds")], axis=1).dropna()
    o["oran"] = o["epias"] / o["evds"]
    print(f"  ortak gün={len(o)} korelasyon={o['epias'].corr(o['evds']):.4f}")
    ozet = o.groupby(o.index.year)["oran"].agg(["count", "median", "min", "max"]).round(4)
    for yil, r in ozet.iterrows():
        print(f"  {yil}: gün={int(r['count'])} oran medyan={r['median']:.4f} min={r['min']:.4f} maks={r['max']:.4f}")
    print("  (oran 1,000 dışındaysa EPİAŞ gerçek zamanlı tüketim TEİAŞ tüketiminden farklı bir tanımı/baskıyı yansıtıyor)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--yenile", action="store_true", help="tüm aylık ham dosyaları yeniden indir")
    ap.add_argument("--tani", action="store_true", help="Nager ve EVDS ile çapraz kontrol yazdır")
    args = ap.parse_args()

    e = dotenv_values(KOK / ".env")
    if not e.get("EPIAS_KULLANICI") or not e.get("EPIAS_SIFRE"):
        print("EPIAS_KULLANICI / EPIAS_SIFRE .env içinde tanımlı değil", file=sys.stderr)
        return 1
    dun = date.today() - timedelta(days=1)
    oturum = Oturum(e["EPIAS_KULLANICI"].strip(), e["EPIAS_SIFRE"].strip())

    print("Ham veri indiriliyor ...", flush=True)
    dosyalar = ham_indir(oturum, dun, args.yenile)
    df = saatlikleri_oku(dosyalar)
    g, deger, kapsam, sorunlar, _ = gunluk_ve_aylik(df, dun)

    ISLENMIS.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"tarih": list(deger), "deger": list(deger.values())}).to_csv(
        ISLENMIS / "epias_tuketimisgunu_turkiye_aylik.csv", index=False)
    kapsam.to_csv(ISLENMIS / "epias_tuketimisgunu_turkiye_aylik_kapsam.csv", index=False)
    kaynak_yaz(dosyalar[0].stem[-7:], dosyalar[-1].stem[-7:])

    ilk, son = list(deger)[0], list(deger)[-1]
    print(f"Saatlik kayıt={len(df)} gün={len(g)} ilk={g.index.min().date()} son={g.index.max().date()}")
    print(f"Aylık iş günü ortalaması: {len(deger)} gözlem, {ilk} .. {son}")
    atlanan = set(kapsam['tarih']) - set(deger)
    print(f"Yetersiz kapsam nedeniyle atlanan ay: {sorted(atlanan) if atlanan else 'yok'}")
    print("Veri sorunları:", json.dumps({k: v for k, v in sorunlar.items() if v}, ensure_ascii=False))

    # Yedek/karşılaştırma yolu: EVDS bie_elektuketim TKT1 (TEİAŞ günlük tüketim), aynı iş günü mantığı.
    # Kartın ana göstergesi EPİAŞ'tır; bu dosya yalnız duyarlılık/karşılaştırma içindir.
    evds_anahtar = (e.get("EVDS_API_KEY") or "").strip()
    tkt = None
    if evds_anahtar:
        ev_deger, ev_kapsam, tkt = evds_yedek_uret(evds_anahtar, dun)
        pd.DataFrame({"tarih": list(ev_deger), "deger": list(ev_deger.values())}).to_csv(
            ISLENMIS / "evds_tuketimisgunu_turkiye_aylik.csv", index=False)
        ev_kapsam.to_csv(ISLENMIS / "evds_tuketimisgunu_turkiye_aylik_kapsam.csv", index=False)
        print(f"EVDS karşılaştırma serisi: {len(ev_deger)} gözlem, {list(ev_deger)[0]} .. {list(ev_deger)[-1]}")
    else:
        print("EVDS_API_KEY yok: EVDS karşılaştırma serisi atlandı")
    if args.tani:
        tani(g, tkt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
