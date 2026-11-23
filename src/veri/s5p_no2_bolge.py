#!/usr/bin/env python3
"""Sentinel-5P TROPOMI L2 NO2 (collection 03) bölge alt kümesi ve aylık seri (H-003).

Kaynak: anahtarsız AWS Açık Veri kovası  s3://meeo-s5p  (https://meeo-s5p.s3.amazonaws.com/)
  RPRO/L2__NO2___/YYYY/MM/DD/*.nc   2018-05-01..2022-07-25, yalnız adında _03_020400_ geçenler
  OFFL/L2__NO2___/YYYY/MM/DD/*.nc   2022-07-26 ve sonrası, o günkü tüm OFFL dosyaları
Değişken: PRODUCT/nitrogendioxide_tropospheric_column (mol/m2), filtre qa_value >= 0,75.
Bölgeler: geoBoundaries gbOpen TUR ADM1 (sabit commit 9469f09), piksel merkezi poligon içinde.
  marmara4       = Kocaeli + Sakarya + Bursa + Tekirdağ
  kastamonusinop = Kastamonu + Sinop (plasebo)

Veri hacmi: her yörünge dosyası ~470 MB. Tam dosya İNDİRİLMEZ. Her dosyada
  1) HDF5 üst verisi (16 KiB'lık aralık okumalarıyla, ~0,15 MB),
  2) alt-uydu izi (satellite_latitude/longitude, birkaç KB) ile bölgeye yaklaşan tarama
     satırları belirlenir,
  3) yalnız o satır-yığınlarının (bölgenin alt-uydu izinin batısında/doğusunda kalmasına göre
     yalnız ilgili sütun yarısının) latitude/longitude'u ve qa_value'su, ardından yalnız qa>=0,75
     bölge pikseli bulunan yığınların NO2'si sıkıştırılmış HDF5 yığınları olarak HTTP aralık
     isteğiyle çekilip yerelde açılır (dosya başına ortalama ~3,3 MB).
Ön süzgeç: dosya adındaki başlangıç zamanından alt-uydu izinin 40 K enlemindeki boylamı kestirilir
(ON_SUZGEC); bölgeyi taramayacak yörüngelerin dosyası hiç açılmaz (günde ~2 dosya kalır).
Aday olmayan ama bölgeyi tarayan dosya olmadığı 2026-06'da tüm yörüngeler işlenerek doğrulandı;
tamamen kapatmak için --tum-yorungeler.

Ara ürün: data/ham/s5p_no2/piksel/<akış>/<YYYY>/<ay>/<dosya>.npz  (dosya başına, bölge
poligonları içindeki TÜM piksellerin lat/lon/NO2/qa değerleri; eşik sonradan değiştirilebilir).
Bir dosya için .npz varsa tekrar indirilmez: betik kaldığı yerden devam eder.

Aşamalar:
  indir      : dosya listesi + bölge alt kümesi (ağ)  -> piksel/*.npz
  birlestir  : npz'lerden günlük özet ve aylık seri (yerel, ağ yok)
  hepsi      : ikisi de (varsayılan)

Kullanım örnekleri:
  python src/veri/s5p_no2_bolge.py --bas 2019-07-01 --bit 2019-07-31 --cikti-dizin /tmp/x
  python src/veri/s5p_no2_bolge.py                      # tam dönem, varsayılan çıktılar
  python src/veri/s5p_no2_bolge.py --asama birlestir    # yalnız yeniden toplulaştır

Toplulaştırma (kart tanımı, birebir): aylık değer = ay içindeki tüm geçerli piksellerin
(qa_value >= 0,75 ve NO2 geçerli) pikselde ağırlıklı ortalaması; geçerli piksel içeren gün sayısı
5'ten az olan ay boş (NaN). Negatif NO2 değerleri kırpılmaz. Birim: mol/m2.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import threading
import time
import zlib
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import requests

KOK = Path(__file__).resolve().parents[2]
HAM = KOK / "data" / "ham" / "s5p_no2"
ISLENMIS = KOK / "data" / "islenmis"

KOVA = "https://meeo-s5p.s3.amazonaws.com/"
URUN = "L2__NO2___"
KULLANICI_AJANI = "altveri-lab/s5p-no2-bolge"  # kişisel bilgi yok
GEOJSON_URL = ("https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/"
               "gbOpen/TUR/ADM1/geoBoundaries-TUR-ADM1.geojson")
GEOJSON_YOL = HAM / "geoBoundaries-TUR-ADM1_9469f09.geojson"

BOLGELER = {
    "marmara4": ["Kocaeli", "Sakarya", "Bursa", "Tekirdağ"],
    "kastamonusinop": ["Kastamonu", "Sinop"],
}

# Dosya seçim kuralı (kart): sürüm koduna göre
RPRO_BAS = dt.date(2018, 5, 1)
RPRO_SON = dt.date(2022, 7, 25)
OFFL_BAS = dt.date(2022, 7, 26)
RPRO_SURUM = "020400"
KOLEKSIYON = "03"
QA_ESIK_HAM = 75           # qa_value uint8 (ölçek 0,01): 75 -> 0,75
MIN_GECERLI_GUN = 5
DOLGU = 1e30               # _FillValue 9,96921e36

# Dosya adından yörünge önsüzgeci: hangi dosyaların açılacağını daraltır (bkz. kalibrasyon).
ON_SUZGEC = {"t40_ofset_dk": 55.0, "yst_saat": 13.0, "merkez_lon": 31.1, "esik_derece": 27.0}
# Dosya içi 2. süzgeç: alt-uydu izi bölge kutusuna şu kadar yakınsa tarama satırı adaydır.
YARI_SWATH_DERECE = 15.9   # ~1300 km / (111 km * cos 41) = 15,4 derece; örnekte en uzak isabet 15,0 derece
ENLEM_PAYI = 3.5
SUTUN_PAYI = 1.5           # sütun yarısı seçiminde boylam payı (derece)
SUTUN_YAKIN = 20           # izin bu kadar sütun yakınındaki piksel bulunursa diğer yarı da okunur

SATIR_DOSYA_RE = re.compile(
    r"^S5P_(RPRO|OFFL)_L2__NO2____(\d{8}T\d{6})_(\d{8}T\d{6})_(\d{5})_(\d{2})_(\d{6})_(\d{8}T\d{6})\.nc$")


# ------------------------------------------------------------------ yardımcılar
def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


_YEREL = threading.local()


def _oturum() -> requests.Session:
    s = getattr(_YEREL, "s", None)
    if s is None:
        s = requests.Session()
        s.headers.update({"User-Agent": KULLANICI_AJANI})
        s.mount("https://", requests.adapters.HTTPAdapter(pool_connections=4, pool_maxsize=8))
        _YEREL.s = s
    return s


def http_al(url: str, aralik: tuple[int, int] | None = None, params: dict | None = None,
            deneme: int = 5) -> bytes:
    """Yeniden denemeli GET. Dönen: içerik baytları."""
    baslik = {}
    if aralik is not None:
        baslik["Range"] = f"bytes={aralik[0]}-{aralik[1]}"
    son = None
    for i in range(deneme):
        try:
            r = _oturum().get(url, headers=baslik, params=params, timeout=(10, 90))
            if r.status_code in (200, 206):
                return r.content
            if r.status_code in (403, 404):
                raise FileNotFoundError(f"{r.status_code} {url}")
            son = RuntimeError(f"HTTP {r.status_code} {url}")
        except FileNotFoundError:
            raise
        except Exception as e:  # ağ hatası, zaman aşımı
            son = e
        time.sleep(min(2 ** i, 20))
    raise RuntimeError(f"istek başarısız ({deneme} deneme): {son}")


def ay_listesi(bas: dt.date, bit: dt.date):
    y, m = bas.year, bas.month
    while (y, m) <= (bit.year, bit.month):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def ay_gun_sayisi(y: int, m: int) -> int:
    return (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.date(y, m, 1)).days


def surum_noktali(kod: str) -> str:
    """'020701' -> '2.7.1'"""
    return f"{int(kod[:2])}.{int(kod[2:4])}.{int(kod[4:6])}"


def surum_sayi(metin: str | None) -> tuple | None:
    """HDF5 processor_version ('2.4.0' ya da '02.09.01') -> (2, 4, 0)"""
    m = re.match(r"^\s*(\d+)\.(\d+)\.(\d+)", metin or "")
    return tuple(int(x) for x in m.groups()) if m else None


# ------------------------------------------------------------------ kova listesi
def kova_listele(onek: str) -> list[tuple[str, int]]:
    """S3 ListObjectsV2 (anahtarsız). Dönen: [(anahtar, boyut)]"""
    out, jeton = [], None
    while True:
        p = {"list-type": "2", "prefix": onek}
        if jeton:
            p["continuation-token"] = jeton
        x = http_al(KOVA, params=p).decode("utf-8")
        out += [(m.group(1), int(m.group(2)))
                for m in re.finditer(r"<Key>(.*?)</Key>.*?<Size>(\d+)</Size>", x, re.S)]
        m = re.search(r"<NextContinuationToken>(.*?)</NextContinuationToken>", x)
        if not m:
            return out
        jeton = m.group(1)


def dosya_coz(anahtar: str) -> dict | None:
    ad = anahtar.rsplit("/", 1)[-1]
    m = SATIR_DOSYA_RE.match(ad)
    if not m:
        return None
    akis, bas, bit, orbit, koll, surum, uretim = m.groups()
    p = lambda s: dt.datetime.strptime(s, "%Y%m%dT%H%M%S")  # noqa: E731
    parca = anahtar.split("/")
    return dict(anahtar=anahtar, ad=ad, akis=akis, bas=p(bas), bit=p(bit), orbit=int(orbit),
                koll=koll, surum=surum, uretim=p(uretim),
                tarih=dt.date(int(parca[2]), int(parca[3]), int(parca[4])))


def secim_kurali(d: dict) -> str | None:
    """None = seçildi; aksi halde dışlama nedeni."""
    if d["koll"] != KOLEKSIYON:
        return "koleksiyon"
    if d["akis"] == "RPRO":
        if not (RPRO_BAS <= d["tarih"] <= RPRO_SON):
            return "rpro_tarih_disi"
        return None if d["surum"] == RPRO_SURUM else "rpro_surum"
    return None if d["tarih"] >= OFFL_BAS else "offl_tarih_disi"


def akis_ay_icin(y: int, m: int) -> list[str]:
    ilk, son = dt.date(y, m, 1), dt.date(y, m, ay_gun_sayisi(y, m))
    out = []
    if ilk <= RPRO_SON:
        out.append("RPRO")
    if son >= OFFL_BAS:
        out.append("OFFL")
    return out


def onsuzgec_adayi(bas: dt.datetime) -> tuple[bool, float]:
    """Dosya adındaki başlangıç zamanından alt-uydu izinin 40 K enlemindeki boylamını kestirir.
    Dönen: (aday_mi, kestirilen_boylam)."""
    p = ON_SUZGEC
    t40 = bas + dt.timedelta(minutes=p["t40_ofset_dk"])
    saat = t40.hour + t40.minute / 60 + t40.second / 3600
    lon = ((p["yst_saat"] - saat) * 15.0 + 180) % 360 - 180
    fark = abs(((lon - p["merkez_lon"]) + 180) % 360 - 180)
    return fark <= p["esik_derece"], lon


# ------------------------------------------------------------------ bölge sınırları
def bolge_poligonlari():
    """geoBoundaries'i (gerekirse indirip) okur. Dönen: {bolge: shapely geometri}, kutu."""
    import shapely
    from shapely.geometry import shape
    from shapely.ops import unary_union
    if not GEOJSON_YOL.exists():
        HAM.mkdir(parents=True, exist_ok=True)
        veri = http_al(GEOJSON_URL)
        GEOJSON_YOL.write_bytes(veri)
        log("geoBoundaries indirildi:", GEOJSON_YOL.name, len(veri) // 1000, "KB")
    gj = json.loads(GEOJSON_YOL.read_text(encoding="utf-8"))
    iller = {f["properties"]["shapeName"]: shape(f["geometry"]) for f in gj["features"]}
    sonuc = {}
    for ad, listesi in BOLGELER.items():
        eksik = [i for i in listesi if i not in iller]
        if eksik:
            raise KeyError(f"geoBoundaries'te il adı bulunamadı: {eksik}")
        g = unary_union([iller[i] for i in listesi])
        shapely.prepare(g)
        sonuc[ad] = g
    kutu = (min(g.bounds[0] for g in sonuc.values()), min(g.bounds[1] for g in sonuc.values()),
            max(g.bounds[2] for g in sonuc.values()), max(g.bounds[3] for g in sonuc.values()))
    return sonuc, kutu


# ------------------------------------------------------------------ uzaktan HDF5 okuma
class AralikDosya(io.RawIOBase):
    """HTTP aralık istekleriyle dosya benzeri nesne; 16 KiB hizalı bloklar, önbellekli."""

    def __init__(self, url: str, boyut: int, blok: int = 1 << 14):
        self.url, self.boyut, self.blok = url, boyut, blok
        self.konum = 0
        self.onbellek: dict[int, bytes] = {}
        self.istek = 0
        self.bayt = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.konum

    def seek(self, o, w=0):
        self.konum = o if w == 0 else (self.konum + o if w == 1 else self.boyut + o)
        return self.konum

    def _blok(self, i: int) -> bytes:
        if i not in self.onbellek:
            a = i * self.blok
            b = min(a + self.blok, self.boyut) - 1
            veri = http_al(self.url, aralik=(a, b))
            self.onbellek[i] = veri
            self.istek += 1
            self.bayt += len(veri)
        return self.onbellek[i]

    def readinto(self, tampon):
        n = len(tampon)
        son = min(self.konum + n, self.boyut)
        cikti = bytearray()
        p = self.konum
        while p < son:
            i = p // self.blok
            d = self._blok(i)
            o = p - i * self.blok
            parca = d[o:o + (son - p)]
            cikti += parca
            p += len(parca)
        tampon[:len(cikti)] = cikti
        self.konum = son
        return len(cikti)


class Yiginlar:
    """Bir veri kümesinin HDF5 yığın tablosu; yığınları ham baytla çekip yerelde açar.
    Desteklenen filtreler: shuffle(2), deflate(1), fletcher32(3); sıra veri kümesinden okunur."""

    def __init__(self, ds):
        self.dtype = ds.dtype
        self.shape = ds.shape[1:]      # (scanline, ground_pixel)
        self.chunks = ds.chunks        # (1, cr, cc)
        pl = ds.id.get_create_plist()
        self.hatti = [pl.get_filter(i)[0] for i in range(pl.get_nfilters())]
        if not self.hatti or set(self.hatti) - {1, 2, 3}:
            raise RuntimeError(f"beklenmeyen filtre dizisi: {self.hatti}")
        self.tablo = {}
        for i in range(ds.id.get_num_chunks()):
            ci = ds.id.get_chunk_info(i)
            if ci.filter_mask != 0:
                raise RuntimeError("yığında atlanmış filtre var")
            self.tablo[(int(ci.chunk_offset[1]), int(ci.chunk_offset[2]))] = (ci.byte_offset, ci.size)

    def anahtarlar_satir(self, araliklar):
        """Verilen satır aralıklarını (başlangıç, bitiş) kesen tüm yığın anahtarları."""
        out = []
        for (r0, c0) in self.tablo:
            if any(r0 < b and r0 + self.chunks[1] > a for (a, b) in araliklar):
                out.append((r0, c0))
        return out

    def aralik(self, anah):
        return self.tablo[anah]

    def coz(self, ham: bytes) -> np.ndarray:
        b = ham
        for f in reversed(self.hatti):          # yazma sırasının tersi
            if f == 3:
                b = b[:-4]                        # fletcher32 sağlama toplamı (4 bayt)
            elif f == 1:
                b = zlib.decompress(b)            # zlib kendi adler32 sağlamasını doğrular
            elif f == 2:
                k = self.dtype.itemsize
                if k > 1:
                    b = np.frombuffer(b, dtype=np.uint8).reshape(k, -1).T.tobytes()
        return np.frombuffer(b, dtype=self.dtype).reshape(self.chunks)[0]

    def yerlestir(self, hedef: np.ndarray, anah, ham: bytes):
        blok = self.coz(ham)
        r0, c0 = anah
        r1, c1 = min(r0 + blok.shape[0], hedef.shape[0]), min(c0 + blok.shape[1], hedef.shape[1])
        hedef[r0:r1, c0:c1] = blok[:r1 - r0, :c1 - c0]


def lon_mesafe(lon, lo, hi):
    """Boylamın [lo,hi] aralığına derece cinsinden uzaklığı (daireyi sarar)."""
    c, yari = (lo + hi) / 2, (hi - lo) / 2
    d = np.abs(((lon - c + 180) % 360) - 180)
    return np.maximum(d - yari, 0)


def dosya_isle(girdi: dict, ayar: dict) -> dict:
    """Bir yörünge dosyasından bölge piksellerini çıkarır, npz yazar. Dönen: özet sözlük."""
    import h5py
    import shapely
    t0 = time.time()
    anahtar, boyut = girdi["anahtar"], girdi["boyut"]
    url = KOVA + anahtar
    hedef = Path(girdi["npz"])
    kutu, geoms, istek_par = ayar["kutu"], ayar["geoms"], ayar["istek_par"]
    f = AralikDosya(url, boyut)
    veri_bayt = [0]
    h = None
    meta = dict(anahtar=anahtar, surum_dosya=girdi["surum"], akis=girdi["akis"],
                bolge_adlari=list(geoms.keys()))
    try:
        h = h5py.File(f, "r")
        sv = h.attrs["processor_version"]
        meta["surum_icerik"] = sv.decode() if isinstance(sv, bytes) else str(sv)
        meta["zaman_bas"] = _s(h.attrs.get("time_coverage_start"))
        meta["zaman_bit"] = _s(h.attrs.get("time_coverage_end"))
        sd = h["PRODUCT/SUPPORT_DATA/GEOLOCATIONS"]
        sat_lat = np.asarray(sd["satellite_latitude"][0], dtype=np.float64)
        sat_lon = np.asarray(sd["satellite_longitude"][0], dtype=np.float64)
        lat_ds = h["PRODUCT/latitude"]
        n_scan, n_pix = lat_ds.shape[1], lat_ds.shape[2]
        cr, cc = lat_ds.chunks[1], lat_ds.chunks[2]
        meta.update(n_scan=int(n_scan), n_pix=int(n_pix), satir_yigin=int(cr))

        gecerli = (np.isfinite(sat_lat) & np.isfinite(sat_lon) & (np.abs(sat_lat) <= 90)
                   & (np.abs(sat_lon) <= 180))
        # 40 K enlemine geçiş (önsüzgeç kalibrasyonu için)
        ix = np.where(gecerli[:-1] & gecerli[1:] & (sat_lat[:-1] < 40.0) & (sat_lat[1:] >= 40.0))[0]
        gec = None
        if len(ix):
            i = int(ix[0])
            w = (40.0 - sat_lat[i]) / (sat_lat[i + 1] - sat_lat[i])
            dl = (sat_lon[i + 1] - sat_lon[i] + 180) % 360 - 180
            gec = dict(tarama=round(float(i + w), 1), lon=round(float(sat_lon[i] + w * dl), 3))
        meta["gecis40"] = gec

        # --- aşama 0: bölgeye yaklaşan tarama satırları (alt-uydu izinden)
        yakin = (gecerli & (sat_lat >= kutu[1] - ENLEM_PAYI) & (sat_lat <= kutu[3] + ENLEM_PAYI)
                 & (lon_mesafe(sat_lon, kutu[0], kutu[2]) <= YARI_SWATH_DERECE))
        sat_idx = np.where(yakin)[0]
        meta["aday_tarama"] = [int(sat_idx.min()), int(sat_idx.max())] if len(sat_idx) else None
        meta["aday_izlon"] = ([round(float(sat_lon[sat_idx].min()), 2), round(float(sat_lon[sat_idx].max()), 2)]
                              if len(sat_idx) else None)

        bno_l, scan_l, col_l, la_l, lo_l, no2_l, qa_l = [], [], [], [], [], [], []
        if len(sat_idx):
            lon_ds = h["PRODUCT/longitude"]
            no2_ds = h["PRODUCT/nitrogendioxide_tropospheric_column"]
            qa_ds = h["PRODUCT/qa_value"]
            Y = {"lat": Yiginlar(lat_ds), "lon": Yiginlar(lon_ds), "no2": Yiginlar(no2_ds),
                 "qa": Yiginlar(qa_ds)}
            qa_olcek = float(np.ravel(qa_ds.attrs["scale_factor"])[0])
            if abs(qa_olcek - 0.01) > 1e-9:
                raise RuntimeError(f"qa_value ölçeği beklenmedik: {qa_olcek}")
            meta["meta_bayt"] = int(f.bayt)
            meta["meta_istek"] = int(f.istek)

            def indir(ad, anah):
                a, b = Y[ad].aralik(anah)
                return ad, anah, http_al(url, aralik=(a, a + b - 1))

            def toplu(istekler, tamponlar):
                if not istekler:
                    return
                with ThreadPoolExecutor(max_workers=istek_par) as ex:
                    for ad, anah, veri in ex.map(lambda t: indir(*t), istekler):
                        Y[ad].yerlestir(tamponlar[ad], anah, veri)
                        veri_bayt[0] += len(veri)

            lat_t = np.full((n_scan, n_pix), np.nan, dtype=np.float32)
            lon_t = np.full((n_scan, n_pix), np.nan, dtype=np.float32)
            no2_t = np.full((n_scan, n_pix), np.nan, dtype=np.float32)
            qa_t = np.zeros((n_scan, n_pix), dtype=np.uint8)
            araliklar = {(r * cr, (r + 1) * cr) for r in set((sat_idx // cr).tolist())}
            n_sutun = (n_pix + cc - 1) // cc

            # hangi sütun yığınları (batı/doğu yarı) gerekli: bölge, alt-uydu izinin hangi tarafında
            def sutun_secimi(tum: bool) -> set[int]:
                if tum or n_sutun != 2:
                    return set(range(n_sutun))
                sec = set()
                kl = sat_lon[sat_idx]
                if kutu[0] < kl.max() + SUTUN_PAYI:     # bölgenin batı ucu izin batısında kalabilir
                    sec.add(0)
                if kutu[2] > kl.min() - SUTUN_PAYI:     # doğu ucu izin doğusunda kalabilir
                    sec.add(1)
                return sec or set(range(n_sutun))

            secili_sutun = sutun_secimi(ayar.get("tum_sutunlar", False))
            okunan: set[int] = set()
            kimlik = None
            while True:
                yeni = sorted(secili_sutun - okunan)
                ist = []
                for ad in ("lat", "lon"):
                    ist += [(ad, k) for k in Y[ad].anahtarlar_satir(araliklar) if k[1] // cc in yeni]
                if "qa_okundu" not in meta:
                    # qa_value tek yığın (tüm yörünge); aday satırları kesenleri çek
                    ist += [("qa", k) for k in Y["qa"].anahtarlar_satir(araliklar)]
                    meta["qa_okundu"] = True
                gruplar = {"lat": lat_t, "lon": lon_t, "qa": qa_t}
                toplu(ist, gruplar)
                okunan |= set(yeni)
                maske = (np.isfinite(lat_t) & np.isfinite(lon_t) & (np.abs(lat_t) < 100) & (np.abs(lon_t) < 200)
                         & (lat_t >= kutu[1] - 0.02) & (lat_t <= kutu[3] + 0.02)
                         & (lon_t >= kutu[0] - 0.02) & (lon_t <= kutu[2] + 0.02))
                ri, ci = np.nonzero(maske)
                bno = np.zeros(0, dtype=np.int8)
                if len(ri):
                    x, y = lon_t[ri, ci].astype(np.float64), lat_t[ri, ci].astype(np.float64)
                    bno = np.full(len(ri), -1, dtype=np.int8)
                    for k, g in enumerate(geoms.values()):
                        bno[shapely.contains_xy(g, x, y) & (bno < 0)] = k
                    tut = bno >= 0
                    ri, ci, bno = ri[tut], ci[tut], bno[tut]
                # güvenlik: izin yakınındaki piksel bulunduysa ve diğer yarı okunmadıysa onu da çek
                if len(ri) and len(okunan) < n_sutun and np.any(np.abs(ci - n_pix / 2) < SUTUN_YAKIN):
                    secili_sutun = set(range(n_sutun))
                    meta["yari_eklendi"] = True
                    continue
                break
            meta["okunan_sutun"] = sorted(okunan)
            if len(ri):
                # 2. tur: yalnız geçerli (qa>=0,75) bölge pikseli bulunan yığınların NO2'si
                qa_pix = qa_t[ri, ci]
                gv = qa_pix >= QA_ESIK_HAM
                cr_n, cc_n = Y["no2"].chunks[1], Y["no2"].chunks[2]
                gerekli = sorted(set(zip(((ri[gv] // cr_n) * cr_n).tolist(), ((ci[gv] // cc_n) * cc_n).tolist())))
                toplu([("no2", k) for k in gerekli], {"no2": no2_t})
                v = no2_t[ri, ci]
                v = np.where(np.isfinite(v) & (np.abs(v) < DOLGU), v, np.float32(np.nan))
                bno_l, scan_l, col_l = [bno], [ri], [ci]
                la_l, lo_l, no2_l, qa_l = [lat_t[ri, ci]], [lon_t[ri, ci]], [v], [qa_pix]
        h.close()
        h = None
        cat = lambda l, d: np.concatenate(l).astype(d) if l else np.zeros(0, d)  # noqa: E731
        bno, scan, col = cat(bno_l, np.int8), cat(scan_l, np.int32), cat(col_l, np.int16)
        la, lo, no2, qa = cat(la_l, np.float32), cat(lo_l, np.float32), cat(no2_l, np.float32), cat(qa_l, np.uint8)
        meta.update(bayt=int(f.bayt + veri_bayt[0]), istek=int(f.istek), sure=round(time.time() - t0, 2))
        hedef.parent.mkdir(parents=True, exist_ok=True)
        gecici = hedef.with_name(hedef.name[:-4] + ".tmp.npz")
        np.savez_compressed(gecici, bolge=bno, scan=scan, col=col, lat=la, lon=lo, no2=no2, qa=qa,
                            meta=np.array(json.dumps(meta, ensure_ascii=False)))
        os.replace(gecici, hedef)
        return dict(ok=True, ad=girdi["ad"], bayt=meta["bayt"], sure=meta["sure"], n=int(len(bno)),
                    istek=meta["istek"])
    except Exception as e:  # noqa: BLE001
        return dict(ok=False, ad=girdi["ad"], hata=f"{type(e).__name__}: {e}"[:300],
                    sure=round(time.time() - t0, 2))
    finally:
        try:
            if h is not None:
                h.close()
        except Exception:  # noqa: BLE001
            pass


def _s(x):
    if x is None:
        return None
    return x.decode() if isinstance(x, bytes) else str(x)


_AYAR: dict = {}


def _isci_baslat(istek_par: int, tum_sutunlar: bool = False):
    geoms, kutu = bolge_poligonlari()
    _AYAR.update(geoms=geoms, kutu=kutu, istek_par=istek_par, tum_sutunlar=tum_sutunlar)


def _isci(girdi: dict) -> dict:
    return dosya_isle(girdi, _AYAR)


# ------------------------------------------------------------------ indirme aşaması
def npz_yolu(ham_dizin: Path, d: dict) -> Path:
    return ham_dizin / "piksel" / d["akis"] / f"{d['tarih']:%Y}" / f"{d['tarih']:%m}" / (d["ad"][:-3] + ".npz")


def liste_hazirla(bas: dt.date, bit: dt.date, ham_dizin: Path):
    """Aylık kova listesi -> seçili dosyalar, kovada eksik yörünge kestirimi."""
    gorevler = [(akis, y, m) for y, m in ay_listesi(bas, bit) for akis in akis_ay_icin(y, m)]

    def liste(g):
        akis, y, m = g
        return g, kova_listele(f"{akis}/{URUN}/{y:04d}/{m:02d}/")

    secili, dislanan = [], defaultdict(int)
    son_gun = {"RPRO": None, "OFFL": None}
    with ThreadPoolExecutor(max_workers=6) as ex:
        for (akis, y, m), ogeler in ex.map(liste, gorevler):
            for anahtar, boyut in ogeler:
                d = dosya_coz(anahtar)
                if d is None:
                    dislanan["ad_tanimsiz"] += 1
                    continue
                d["boyut"] = boyut
                if not (bas <= d["tarih"] <= bit):
                    continue
                neden = secim_kurali(d)
                if neden:
                    dislanan[f"{akis}:{neden}:{d['surum']}"] += 1
                    continue
                if son_gun[akis] is None or d["tarih"] > son_gun[akis]:
                    son_gun[akis] = d["tarih"]
                secili.append(d)
    # aynı yörünge birden fazlaysa en yeni üretimi al
    en_iyi = {}
    for d in secili:
        k = (d["akis"], d["orbit"])
        if k not in en_iyi or d["uretim"] > en_iyi[k]["uretim"]:
            en_iyi[k] = d
    mukerrer = len(secili) - len(en_iyi)
    secili = sorted(en_iyi.values(), key=lambda d: (d["bas"], d["orbit"]))
    for d in secili:
        d["aday"], d["lon40_tahmin"] = onsuzgec_adayi(d["bas"])
        d["npz"] = str(npz_yolu(ham_dizin, d))
    # kovada eksik yörünge (numara boşlukları); bunlardan hangileri önsüzgece göre aday olurdu
    eksik = []
    for a, b in zip(secili[:-1], secili[1:]):
        fark = b["orbit"] - a["orbit"]
        if 1 < fark <= 40:
            for k in range(1, fark):
                bas_k = a["bas"] + (b["bas"] - a["bas"]) * k / fark
                eksik.append(dict(orbit=a["orbit"] + k, bas=bas_k, aday=onsuzgec_adayi(bas_k)[0],
                                  tarih=bas_k.date()))
    return secili, dict(dislanan), son_gun, eksik, mukerrer


def indir_asamasi(args, bas, bit):
    ham_dizin = Path(args.ham_dizin)
    geoms, kutu = bolge_poligonlari()
    log("bölge kutusu (lon_min, lat_min, lon_max, lat_max):", [round(v, 3) for v in kutu])
    log("kova listeleniyor...")
    secili, dislanan, son_gun, eksik, mukerrer = liste_hazirla(bas, bit, ham_dizin)
    log(f"seçili dosya: {len(secili)}  (mükerrer yörünge ayıklanan: {mukerrer})  son gün: "
        f"RPRO={son_gun['RPRO']} OFFL={son_gun['OFFL']}")
    if dislanan:
        log("dışlananlar:", dict(sorted(dislanan.items())))
    ham_dizin.mkdir(parents=True, exist_ok=True)

    # günlük liste özeti (kapsam raporu için)
    gun = defaultdict(lambda: dict(akis="", dosya=0, aday=0, surum=set(), eksik_aday=0))
    for d in secili:
        g = gun[d["tarih"]]
        g["akis"] = d["akis"]
        g["dosya"] += 1
        g["aday"] += int(bool(d["aday"] or args.tum_yorungeler))
        g["surum"].add(d["surum"])
    for e in eksik:
        if e["aday"]:
            gun[e["tarih"]]["eksik_aday"] += 1
    gun_yol = ham_dizin / "gun_listesi.csv"
    onceki = {}
    if gun_yol.exists():
        with open(gun_yol, newline="") as fh:
            onceki = {r["tarih"]: r for r in csv.DictReader(fh)}
    for t, g in gun.items():
        onceki[t.isoformat()] = dict(tarih=t.isoformat(), akis=g["akis"], listedeki_dosya=g["dosya"],
                                     aday_dosya=g["aday"], kovada_eksik_aday_yorunge=g["eksik_aday"],
                                     surum=";".join(sorted(g["surum"])))
    with open(gun_yol, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["tarih", "akis", "listedeki_dosya", "aday_dosya",
                                            "kovada_eksik_aday_yorunge", "surum"])
        w.writeheader()
        for k in sorted(onceki):
            w.writerow(onceki[k])
    ozet_yol = ham_dizin / "liste_ozeti.json"
    eski = json.loads(ozet_yol.read_text()) if ozet_yol.exists() else {}
    sg = {k: (v.isoformat() if v else None) for k, v in son_gun.items()}
    for k in sg:   # farklı aralıklarla çalıştırmada daha ileri tarihi koru
        if eski.get("son_gun", {}).get(k) and (sg[k] is None or eski["son_gun"][k] > sg[k]):
            sg[k] = eski["son_gun"][k]
    ozet_yol.write_text(json.dumps(dict(
        olusturma=dt.datetime.now().isoformat(timespec="seconds"), son_calistirma_aralik=[bas.isoformat(), bit.isoformat()],
        son_gun=sg, secili=len(secili), dislanan=dislanan), ensure_ascii=False, indent=1))

    isler = [d for d in secili if (d["aday"] or args.tum_yorungeler) and not Path(d["npz"]).exists()]
    if args.sinir:
        isler = isler[: args.sinir]
    aday_say = sum(1 for d in secili if d["aday"] or args.tum_yorungeler)
    log(f"aday dosya: {aday_say}  yapılacak: {len(isler)}  (tam boyutları toplamı "
        f"{sum(d['boyut'] for d in isler) / 1e9:.0f} GB; okunacak ~%1-2)")
    if args.sadece_listele or not isler:
        return
    t0 = time.time()
    tamam = 0
    bayt = 0
    hatalar: list = []
    kalan = [dict(anahtar=d["anahtar"], boyut=d["boyut"], ad=d["ad"], akis=d["akis"], surum=d["surum"],
                  npz=d["npz"]) for d in isler]
    toplam = len(kalan)
    islenen = 0
    for tur in range(1, 4):           # hatalı dosyalar için en çok 3 geçiş
        if not kalan:
            break
        hatalar = []
        try:
            with ProcessPoolExecutor(max_workers=args.is_sayisi, initializer=_isci_baslat,
                                     initargs=(args.istek_par, args.tum_sutunlar)) as ex:
                fut = [ex.submit(_isci, g) for g in kalan]
                for fu in as_completed(fut):
                    r = fu.result()
                    islenen += 1
                    if r["ok"]:
                        tamam += 1
                        bayt += r["bayt"]
                    else:
                        hatalar.append(r)
                    if islenen % args.ilerleme == 0 or islenen == toplam:
                        hiz = tamam / (time.time() - t0)
                        log(f"{islenen}/{toplam}  hata={len(hatalar)}  {bayt / 1e6:.0f} MB  {hiz * 60:.1f} dosya/dk  "
                            f"kalan ~{(toplam - islenen) / max(hiz, 1e-9) / 60:.1f} dk")
        except KeyboardInterrupt:
            log("kesildi; tamamlanan dosyalar kayıtlı, tekrar çalıştırınca kaldığı yerden devam eder")
            raise
        except Exception as e:  # noqa: BLE001  (örn. BrokenProcessPool)
            log(f"işçi havuzu çöktü ({type(e).__name__}); kalanlar için yeniden denenecek")
        kalan = [g for g in kalan if not Path(g["npz"]).exists()]
        if kalan and tur < 3:
            log(f"{len(kalan)} dosya tamamlanmadı; geçiş {tur + 1}/3 başlıyor")
            islenen = toplam - len(kalan)
            time.sleep(10)
    if kalan:
        with open(ham_dizin / "hatalar.csv", "a", newline="") as fh:
            w = csv.writer(fh)
            for r in hatalar:
                w.writerow([dt.datetime.now().isoformat(timespec="seconds"), r["ad"], r["hata"]])
        log(f"UYARI: {len(kalan)} dosya tamamlanamadı (hatalar.csv). Aynı komutu yeniden çalıştırın; "
            "yalnız eksikler denenir. İlk örnekler:")
        for r in hatalar[:5]:
            log("  ", r["ad"], r["hata"])
    log(f"indirme aşaması bitti: {tamam} dosya, {bayt / 1e6:.0f} MB, {(time.time() - t0) / 60:.1f} dk")


# ------------------------------------------------------------------ birleştirme aşaması
def birlestir_asamasi(args, bas, bit):
    ham_dizin = Path(args.ham_dizin)
    cikti = Path(args.cikti_dizin)
    cikti.mkdir(parents=True, exist_ok=True)
    bolge_adlari = list(BOLGELER.keys())
    ozet_yol = ham_dizin / "liste_ozeti.json"
    liste_ozeti = json.loads(ozet_yol.read_text()) if ozet_yol.exists() else {}
    npzler = sorted((ham_dizin / "piksel").rglob("*.npz")) if (ham_dizin / "piksel").exists() else []

    satirlar = []
    uyumsuz = []
    for yol in npzler:
        if yol.name.endswith(".tmp.npz"):
            continue
        m = SATIR_DOSYA_RE.match(yol.name[:-4] + ".nc")
        if not m:
            continue
        z = np.load(yol, allow_pickle=False)
        meta = json.loads(str(z["meta"]))
        p = meta["anahtar"].split("/")
        tarih = dt.date(int(p[2]), int(p[3]), int(p[4]))
        if not (bas <= tarih <= bit):
            continue
        surum = m.group(6)
        if surum_sayi(meta.get("surum_icerik")) != surum_sayi(surum_noktali(surum)):
            uyumsuz.append((yol.name, meta.get("surum_icerik")))
        bn, no2, qa = z["bolge"], z["no2"].astype(np.float64), z["qa"]
        gec = (qa >= QA_ESIK_HAM) & np.isfinite(no2)
        for k, ad in enumerate(meta["bolge_adlari"]):
            s = bn == k
            g = s & gec
            satirlar.append(dict(bolge=ad, tarih=tarih, akis=m.group(1), surum=surum,
                                 n_in=int(s.sum()), n_gec=int(g.sum()),
                                 top=float(no2[g].sum()), orbit=int(m.group(4))))
    if not satirlar:
        log("npz bulunamadı; önce 'indir' aşaması çalışmalı")
        return
    gunluk = defaultdict(lambda: dict(n_in=0, n_gec=0, top=0.0, dosya=0, dosya_gec=0, akis=set(), surum=set()))
    for r in satirlar:
        g = gunluk[(r["bolge"], r["tarih"])]
        g["n_in"] += r["n_in"]
        g["n_gec"] += r["n_gec"]
        g["top"] += r["top"]
        g["dosya"] += 1
        g["akis"].add(r["akis"])
        if r["n_gec"] > 0:
            g["dosya_gec"] += 1
            g["surum"].add(r["surum"])
    gun_cikti = ham_dizin / "gunluk_ozet.csv"
    with open(gun_cikti, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["bolge", "tarih", "akis", "surum", "dosya_sayisi", "dosya_gecerli", "gozlenen_piksel",
                    "gecerli_piksel", "ortalama_mol_m2"])
        for (b, t) in sorted(gunluk):
            g = gunluk[(b, t)]
            ort = f"{g['top'] / g['n_gec']:.6e}" if g["n_gec"] else ""
            w.writerow([b, t.isoformat(), "+".join(sorted(g["akis"])), "+".join(sorted(g["surum"])), g["dosya"],
                        g["dosya_gec"], g["n_in"], g["n_gec"], ort])
    log("günlük özet yazıldı:", gun_cikti)

    gl = {}
    if (ham_dizin / "gun_listesi.csv").exists():
        with open(ham_dizin / "gun_listesi.csv", newline="") as fh:
            gl = {r["tarih"]: r for r in csv.DictReader(fh)}
    son_gun = [dt.date.fromisoformat(v) for v in liste_ozeti.get("son_gun", {}).values() if v]
    son_gozlem = max(son_gun) if son_gun else None
    npz_gun = defaultdict(int)       # gün -> işlenmiş dosya sayısı
    for (bb, t), g in gunluk.items():
        if bb == bolge_adlari[0]:
            npz_gun[t.isoformat()] = g["dosya"]
    eksik_dosya_ay = defaultdict(int)   # (yıl, ay) -> listede aday olup npz'si olmayan dosya sayısı
    for t_s, r in gl.items():
        t = dt.date.fromisoformat(t_s)
        if bas <= t <= bit:
            eksik_dosya_ay[(t.year, t.month)] += max(int(r["aday_dosya"]) - npz_gun.get(t_s, 0), 0)

    for b in bolge_adlari:
        ana, kap = [], []
        for (y, m) in sorted({(t.year, t.month) for (bb, t) in gunluk if bb == b}):
            ilk, son = dt.date(y, m, 1), dt.date(y, m, ay_gun_sayisi(y, m))
            islenmemis = eksik_dosya_ay.get((y, m), 0)
            tam_ay = (ilk >= bas and son <= bit and (son_gozlem is None or son <= son_gozlem)
                      and islenmemis == 0)
            gnl = [g for (bb, t), g in gunluk.items() if bb == b and t.year == y and t.month == m]
            gecgun = [g for g in gnl if g["n_gec"] > 0]
            n_gec = sum(g["n_gec"] for g in gecgun)
            top = sum(g["top"] for g in gecgun)
            gun_rpro = sum(1 for g in gecgun if g["akis"] == {"RPRO"})
            gun_offl = sum(1 for g in gecgun if g["akis"] == {"OFFL"})
            sv = defaultdict(int)
            for g in gecgun:
                for s_ in g["surum"]:
                    sv[s_] += 1
            gunler = [(ilk + dt.timedelta(days=i)).isoformat() for i in range(ay_gun_sayisi(y, m))]
            deger = top / n_gec if (len(gecgun) >= MIN_GECERLI_GUN and n_gec > 0) else None
            if tam_ay:
                ana.append((ilk.isoformat(), "" if deger is None else f"{deger:.6e}"))
            kap.append(dict(
                tarih=ilk.isoformat(), gecerli_gun=len(gecgun), gecerli_piksel=n_gec,
                gozlenen_piksel=sum(g["n_in"] for g in gnl),
                kaynak_klasor="+".join(k for k, v in (("RPRO", gun_rpro), ("OFFL", gun_offl)) if v),
                rpro_gun=gun_rpro, offl_gun=gun_offl,
                surum=";".join(f"{k}:{v}" for k, v in sorted(sv.items())),
                kovada_listeli_gun=sum(1 for t in gunler if t in gl),
                kovada_eksik_aday_yorunge=sum(int(gl.get(t, {}).get("kovada_eksik_aday_yorunge", 0) or 0) for t in gunler),
                islenmemis_aday_dosya=islenmemis,
                nan_ay=int(deger is None), kismi_ay=int(not tam_ay), min_gecerli_gun=MIN_GECERLI_GUN))
        yol_ana = cikti / f"s5p_no2_{b}_aylik.csv"
        yol_kap = cikti / f"s5p_no2_{b}_aylik_kapsam.csv"
        with open(yol_ana, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["tarih", "deger"])
            w.writerows(ana)
        with open(yol_kap, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(kap[0].keys()))
            w.writeheader()
            w.writerows(kap)
        nan_say = sum(1 for _, v in ana if v == "")
        log(f"{yol_ana}: {len(ana)} ay ({ana[0][0] if ana else '-'} .. {ana[-1][0] if ana else '-'}), "
            f"NaN ay: {nan_say}")
    eksikler = {f"{y}-{m:02d}": n for (y, m), n in sorted(eksik_dosya_ay.items()) if n}
    if eksikler:
        log(f"UYARI: işlenmemiş aday dosyası olan aylar (ana CSV'ye YAZILMADI; 'indir' aşamasını yeniden "
            f"çalıştırın): {eksikler}")
    if uyumsuz:
        log(f"UYARI: {len(uyumsuz)} dosyada ad sürümü ile HDF5 processor_version uyuşmuyor: {uyumsuz[:3]}")


# ------------------------------------------------------------------ CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bas", default="2018-05-01", help="başlangıç tarihi (YYYY-MM-DD)")
    ap.add_argument("--bit", default=None, help="bitiş tarihi (varsayılan: bugün)")
    ap.add_argument("--ham-dizin", default=str(HAM), help="ara ürünlerin dizini")
    ap.add_argument("--cikti-dizin", default=str(ISLENMIS), help="aylık CSV çıktılarının dizini")
    ap.add_argument("--asama", choices=["indir", "birlestir", "hepsi"], default="hepsi")
    ap.add_argument("--is-sayisi", type=int, default=8, help="paralel işlem sayısı")
    ap.add_argument("--istek-par", type=int, default=2, help="işlem başına eşzamanlı yığın isteği")
    ap.add_argument("--tum-sutunlar", action="store_true", help="batı/doğu yarı seçimini kapat (doğrulama)")
    ap.add_argument("--tum-yorungeler", action="store_true", help="önsüzgeci kapat (kalibrasyon)")
    ap.add_argument("--sinir", type=int, default=0, help="en fazla N dosya işle (deneme)")
    ap.add_argument("--sadece-listele", action="store_true")
    ap.add_argument("--ilerleme", type=int, default=100)
    args = ap.parse_args()
    bas = dt.date.fromisoformat(args.bas)
    bit = dt.date.fromisoformat(args.bit) if args.bit else dt.date.today()
    if args.is_sayisi * args.istek_par > 16:
        log("UYARI: eşzamanlı istek üst sınırı ~16 önerilir (is-sayisi x istek-par)")
    if args.asama in ("indir", "hepsi"):
        indir_asamasi(args, bas, bit)
    if args.asama in ("birlestir", "hepsi") and not args.sadece_listele:
        birlestir_asamasi(args, bas, bit)


if __name__ == "__main__":
    main()
