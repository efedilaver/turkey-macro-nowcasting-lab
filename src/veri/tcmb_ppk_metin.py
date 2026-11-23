"""TCMB PPK toplanti ozetlerini indirir (H-005).

Kaynak: arsiv sayfasi (yalnizca bu sayfada listelenen belgeler).
Ham HTML: data/ham/tcmb_ppk/<DUY kodu>.html ; liste sayfasi: _arsiv_listesi.html
Meta: data/ara/tcmb_ppk/belgeler.csv
Yeniden calistirilabilir: mevcut ham dosyalar tekrar indirilmez (--yenile ile indirilir).
"""
import csv, re, sys, time, html as htmlmod
from pathlib import Path
import requests

KOK = Path(__file__).resolve().parents[2]
HAM = KOK / "data/ham/tcmb_ppk"
ARA = KOK / "data/ara/tcmb_ppk"
BASE = "https://www.tcmb.gov.tr"
YOL = "/wps/wcm/connect/TR/TCMB+TR/PPK/PPK+Toplanti+Ozetleri"
ARSIV = BASE + YOL
UA = {"User-Agent": "altveri-lab"}
INDIRME = "2026-11-07"
AYLAR = {"ocak": 1, "şubat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "haziran": 6, "temmuz": 7,
         "ağustos": 8, "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12}


def tr_lower(s):
    return s.replace("İ", "i").replace("I", "ı").lower()


def get(url):
    for deneme in range(5):
        try:
            r = requests.get(url, headers=UA, timeout=60)
            r.raise_for_status()
            if len(r.content) < 2000:
                raise requests.RequestException("bos/kisa yanit")
            break
        except requests.RequestException as e:
            if deneme == 4:
                raise
            time.sleep(5 * (deneme + 1))
    time.sleep(1.0)
    r.encoding = "utf-8"
    return r.text


def tarih_ayikla(metin):
    """Metindeki ilk 'g Ay yyyy' veya gg/mm/yyyy ya da gg.mm.yyyy tarihini ISO dondurur."""
    m = re.search(r"(\d{1,2})\s+(" + "|".join(AYLAR) + r")\s+(\d{4})", tr_lower(metin))
    if m:
        return "%s-%02d-%02d" % (m.group(3), AYLAR[m.group(2)], int(m.group(1)))
    m = re.search(r"(\d{1,2})[/.](\d{1,2})[/.](\d{4})", metin)
    if m:
        return "%s-%02d-%02d" % (m.group(3), int(m.group(2)), int(m.group(1)))
    return ""


def duz_metin(parca):
    parca = re.sub(r"<[^>]+>", " ", parca)
    parca = htmlmod.unescape(parca).replace("\xa0", " ")
    return re.sub(r"\s+", " ", parca).strip()


def sayfa_meta(h):
    from bs4 import BeautifulSoup
    s = BeautifulSoup(h, "html.parser")
    ana = s.find(id="tcmbMainContent") or s
    h1 = s.find("h1")
    baslik = duz_metin(str(h1)) if h1 else ""
    sayi = ""
    yayin = ""
    toplanti = ""
    ilk_bloklar = [duz_metin(str(p)) for p in ana.find_all(["p", "h2", "h3", "div"])][:12]
    for t in ilk_bloklar:
        m = re.match(r"Sayı\s*:\s*(\d{4}-\d+)", t)
        if m and not sayi:
            sayi = m.group(1)
    # toplanti tarihi
    for p in ana.find_all(["p", "div"]):
        t = duz_metin(str(p))
        if re.match(r"Toplantı Tarihi\s*:", t) and not toplanti:
            toplanti = tarih_ayikla(t.split(":", 1)[1])
            break
    # yayin tarihi: Sayi satirindan sonraki, 'Toplanti Tarihi' oncesi kisa blok
    for t in ilk_bloklar:
        if t.startswith("Toplantı Tarihi") or len(t) > 40:
            continue
        if re.match(r"Sayı", t):
            continue
        d = tarih_ayikla(t)
        if d:
            yayin = d
            break
    return baslik, sayi, yayin, toplanti


def main():
    yenile = "--yenile" in sys.argv
    HAM.mkdir(parents=True, exist_ok=True)
    ARA.mkdir(parents=True, exist_ok=True)
    lf = HAM / "_arsiv_listesi.html"
    if yenile or not lf.exists():
        lf.write_text(get(ARSIV), encoding="utf-8")
    lh = lf.read_text(encoding="utf-8")
    liste = {}
    for kod, baslik in re.findall(r'href="' + re.escape(YOL) + r'/((?:DUY|ANO)\d{4}-\d+)"[^>]*>([^<]*)', lh):
        liste.setdefault(kod, duz_metin(baslik))
    print("listelenen belge:", len(liste))
    (HAM / "KAYNAK.txt").write_text(
        "Kaynak: TCMB PPK Toplanti Ozetleri arsivi\n"
        "URL: %s (belgeler: %s/<DUY kodu>)\n"
        "Indirme tarihi: %s\n"
        "Betik: src/veri/tcmb_ppk_metin.py (User-Agent: altveri-lab)\n"
        "Lisans notu: Kamuya acik TCMB duyurulari; TCMB site Kullanim Sartlari gecerlidir. "
        "Arastirma amacli, yeniden dagitilmaz. Ham HTML elle degistirilmez.\n"
        "Kapsam: yalnizca arsiv sayfasinda listelenen belgeler (2014 sonrasi). "
        "Web arsivi / ucuncu taraf kullanilmadi.\n" % (ARSIV, ARSIV, INDIRME), encoding="utf-8")
    satirlar = []
    for kod, lbaslik in liste.items():
        url = "%s/%s" % (ARSIV, kod)
        f = HAM / (kod + ".html")
        if yenile or not f.exists() or f.stat().st_size < 2000:
            f.write_text(get(url), encoding="utf-8")
            print("indirildi", kod)
        h = f.read_text(encoding="utf-8")
        baslik, sayi, yayin, toplanti = sayfa_meta(h)
        liste_tarih = tarih_ayikla(lbaslik)
        notlar = []
        if liste_tarih and yayin and liste_tarih != yayin:
            notlar.append("liste_tarihi_farkli:" + liste_tarih)
            yayin = max(yayin, liste_tarih)
        if not yayin and liste_tarih:
            yayin = liste_tarih
            notlar.append("yayin_tarihi_listeden")
        ara = int("ara toplantı" in tr_lower(baslik + " " + lbaslik))
        satirlar.append(dict(belge=kod, baslik=baslik or lbaslik, sayi=sayi or kod[3:], yayin_tarihi=yayin,
                             toplanti_tarihi=toplanti, ara_toplanti=ara, url=url, indirme_tarihi=INDIRME,
                             not_=";".join(notlar)))
    satirlar.sort(key=lambda r: (r["yayin_tarihi"], r["belge"]))
    with open(ARA / "belgeler.csv", "w", newline="", encoding="utf-8") as fo:
        w = csv.writer(fo)
        w.writerow(["belge", "baslik", "sayi", "yayin_tarihi", "toplanti_tarihi", "ara_toplanti", "url", "indirme_tarihi", "not"])
        for r in satirlar:
            w.writerow([r["belge"], r["baslik"], r["sayi"], r["yayin_tarihi"], r["toplanti_tarihi"], r["ara_toplanti"], r["url"], r["indirme_tarihi"], r["not_"]])
    eksik = [r["belge"] for r in satirlar if not r["yayin_tarihi"]]
    print("belge:", len(satirlar), "yayin tarihi ayristirilamayan:", eksik)


if __name__ == "__main__":
    main()
