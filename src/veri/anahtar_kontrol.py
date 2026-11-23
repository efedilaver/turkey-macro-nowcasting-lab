"""Anahtar kontrolü: .env içindeki kimlik bilgilerinin tanımlı olup olmadığını
ve (--baglan ile) A grubu kaynakların bunları kabul edip etmediğini küçük birer
istekle sınar. Değerleri, biletleri veya belirteçleri asla yazdırmaz; veri
indirmez, dosya yazmaz.

A grubu (H-001..H-003): EVDS3, EPİAŞ; Earthdata ve CDSE yalnız H-003 için
yedek (NO2 dosyaları AWS meeo-s5p kovasından anahtarsız alınır).
B grubu (sonraki turlar): yalnızca tanımlı mı diye bakılır; GEE kuruluysa
oturum da denenir.

Kullanım:
    python src/veri/anahtar_kontrol.py [--baglan]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests
from dotenv import dotenv_values

KOK = Path(__file__).resolve().parents[2]
ZAMAN_ASIMI = 30
BASLIK = {"User-Agent": "altveri-lab/anahtar-kontrol"}

A_GRUBU = {
    "EVDS3": ["EVDS_API_KEY"],
    "EPİAŞ": ["EPIAS_KULLANICI", "EPIAS_SIFRE"],
    "Earthdata": ["EARTHDATA_TOKEN"],
    "CDSE": ["CDSE_KULLANICI", "CDSE_SIFRE"],
}
B_GRUBU = {
    "GEE": ["GEE_PROJECT"],
    "FIRMS": ["FIRMS_MAP_KEY"],
    "USGS": ["USGS_KULLANICI", "USGS_TOKEN"],
    "OpenSky": ["OPENSKY_CLIENT_ID", "OPENSKY_CLIENT_SECRET"],
    "ENTSO-E": ["ENTSOE_TOKEN"],
}


def evds3(e: dict) -> str:
    # Kartlı harcama veri grubunun seri listesi: küçük, anahtar ister.
    r = requests.get(
        "https://evds3.tcmb.gov.tr/igmevdsms-dis/serieList/type=json&code=bie_kkhartut",
        headers={**BASLIK, "key": e["EVDS_API_KEY"]}, timeout=ZAMAN_ASIMI)
    if r.status_code != 200:
        return f"HATA: HTTP {r.status_code}"
    return f"TAMAM (bie_kkhartut grubunda {len(r.json())} seri)"


def epias(e: dict) -> str:
    # TGT bileti alınabiliyorsa kimlik geçerli; bilet yazdırılmaz.
    r = requests.post(
        "https://giris.epias.com.tr/cas/v1/tickets",
        data={"username": e["EPIAS_KULLANICI"], "password": e["EPIAS_SIFRE"]},
        headers={**BASLIK, "Accept": "text/plain"}, timeout=ZAMAN_ASIMI)
    if r.status_code == 201 and r.text.startswith("TGT-"):
        return "TAMAM (TGT bileti alındı)"
    return f"HATA: HTTP {r.status_code}"


def earthdata(e: dict) -> str:
    # En son S5P NO2 dosyasının ilk 8 baytını GES DISC'ten iste.
    cmr = requests.get(
        "https://cmr.earthdata.nasa.gov/search/granules.json",
        params={"short_name": "S5P_L2__NO2____HiR", "page_size": 1, "sort_key": "-start_date"},
        headers=BASLIK, timeout=ZAMAN_ASIMI).json()
    linkler = [l["href"] for l in cmr["feed"]["entry"][0]["links"]
               if l.get("rel", "").endswith("data#") and l["href"].endswith(".nc")]
    r = requests.get(
        linkler[0],
        headers={**BASLIK, "Authorization": f"Bearer {e['EARTHDATA_TOKEN']}", "Range": "bytes=0-7"},
        timeout=ZAMAN_ASIMI, allow_redirects=False)
    if r.status_code in (200, 206) and r.content[:4] == b"\x89HDF":
        return "TAMAM (GES DISC S5P NO2 dosyası okunabiliyor)"
    if r.status_code == 302:
        return ("HATA: giriş sayfasına yönlendirildi (belirteç geçersiz/süresi dolmuş "
                "ya da profilde 'NASA GESDISC DATA ARCHIVE' uygulaması onaylanmamış)")
    return f"HATA: HTTP {r.status_code}"


def cdse(e: dict) -> str:
    r = requests.post(
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": "cdse-public",
              "username": e["CDSE_KULLANICI"], "password": e["CDSE_SIFRE"]},
        headers=BASLIK, timeout=ZAMAN_ASIMI)
    if r.status_code == 200 and "access_token" in r.json():
        return "TAMAM (erişim belirteci alındı)"
    try:
        aciklama = r.json().get("error_description", "")
    except ValueError:
        aciklama = ""
    return f"HATA: HTTP {r.status_code} {aciklama}".rstrip()


def gee(e: dict) -> str:
    try:
        import ee
    except ImportError:
        return "denenmedi: earthengine-api kurulu değil"
    try:
        ee.Initialize(project=e["GEE_PROJECT"])
        ee.Number(1).getInfo()
    except Exception as hata:
        return f"HATA: {type(hata).__name__} (earthengine authenticate yapıldı mı?)"
    return "TAMAM (oturum açıldı)"


DENEMELER = {"EVDS3": evds3, "EPİAŞ": epias, "Earthdata": earthdata, "CDSE": cdse, "GEE": gee}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--baglan", action="store_true",
                    help="A grubu ve GEE için kimlik doğrulama isteği gönder")
    args = ap.parse_args()

    yol = KOK / ".env"
    if not yol.exists():
        print(f"{yol} yok. .env.example dosyasını .env adıyla kopyalayıp doldurun.")
        return 1
    e = {k: v for k, v in dotenv_values(yol).items() if v and v.strip()}

    durum = {}
    for grup_adi, grup in (("A", A_GRUBU), ("B", B_GRUBU)):
        print(f"--- {grup_adi} grubu")
        for kaynak, adlar in grup.items():
            eksik = [a for a in adlar if a not in e]
            if eksik:
                sonuc = "eksik: " + ", ".join(eksik)
            elif args.baglan and kaynak in DENEMELER:
                try:
                    sonuc = DENEMELER[kaynak](e)
                except requests.RequestException as hata:
                    sonuc = f"HATA: bağlantı ({type(hata).__name__})"
            else:
                sonuc = "tanımlı"
            durum[kaynak] = sonuc
            print(f"  {kaynak:<10} {sonuc}")

    def hazir(k: str) -> bool:
        return durum[k].startswith("TAMAM" if args.baglan else "tanımlı")

    # Hedef seriler (SÜE imalat, perakende, TÜFE) için EVDS3 her kartta yedek yoldur.
    # H-003'ün NO2 dosyaları anahtarsız AWS kovasından gelir (kart, erişim notu).
    eksik_kart = [kart for kart, kosul in (
        ("H-001", hazir("EPİAŞ") and hazir("EVDS3")),
        ("H-002", hazir("EVDS3")),
        ("H-003", hazir("EVDS3")),
    ) if not kosul]
    print("Hazır olmayan kartlar: " + (", ".join(eksik_kart) if eksik_kart else "yok"))
    return 1 if eksik_kart else 0


if __name__ == "__main__":
    sys.exit(main())
