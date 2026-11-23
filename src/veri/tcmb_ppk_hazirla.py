"""H-005: PPK ozetlerini cumlelere boler, maskeler, etiketleme partilerini uretir.

Girdi : data/ham/tcmb_ppk/*.html, data/ara/tcmb_ppk/belgeler.csv
Cikti : data/ara/tcmb_ppk/cumleler.csv, anahtar/esleme.csv, parti/{A,B}_NN.json, etiket/ (bos)
Kasa  : yayin_tarihi >= 2025-04-01 belgeleri ISLENMEZ (icerikleri okunmaz).
Kural kaynagi: hipotezler/H-005.md "Puanlama ve seri kurma" (madde 2, 3, 5) ve gorev tanimi.
"""
import csv, hashlib, json, re, shutil, unicodedata
from pathlib import Path
import numpy as np
from bs4 import BeautifulSoup

KOK = Path(__file__).resolve().parents[2]
HAM = KOK / "data/ham/tcmb_ppk"
ARA = KOK / "data/ara/tcmb_ppk"
KASA = "2025-04-01"
PARTI_MAX = 300
TOHUM = {"A": 2026051, "B": 2026052}
KOD_TOHUM = 2026050

AYLAR = "ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık"
MASKE = [
    (re.compile(r"(?i)\b(?:%s)\w*(?:'\w+)?" % AYLAR), "<AY>"),
    (re.compile(r"(?<![\w.,])(?:19|20)\d{2}(?!\d|[.,]\d)(?:'\w+|[^\W\d_]+)?"), "<YIL>"),
    (re.compile(r"(?<!\w)\d+(?:[.,]\d+)*(?:'\w+|[^\W\d_]+)?"), "<SAYI>"),
    (re.compile(r"(?i)\b(?:iki|üç|dört|beş|altı|yedi|sekiz|dokuz|on|yirmi|otuz|kırk|elli|altmış|yetmiş|seksen|doksan|yüz|bin|milyon|milyar|trilyon|birinci|ikinci|üçüncü|dördüncü|beşinci|altıncı|yedinci|sekizinci|dokuzuncu|onuncu)\b"), "<SAYI>"),
    (re.compile(r"(?i)\b(?:ilk|son)(?=\s+(?:çeyre|yarı))"), "<SAYI>"),
]
KISALTMA = {"vb", "vs", "örn", "bkz", "yak", "krş", "dr", "prof", "doç", "no", "t.c", "a.ş"}
ACILIS = "\"'“«(["
KAPANIS = "\"'”»)]"
SON_KARAKTER = ".!?…:;"
BLOK_ETIKET = ["p", "li", "div", "table", "h1", "h2", "h3", "h4", "h5", "h6"]


def tr_lower(s):
    s = s.replace("İ", "i").replace("I", "ı")
    return unicodedata.normalize("NFC", s.lower())


def normalize(s):
    s = unicodedata.normalize("NFC", s)
    s = s.replace("­", "")
    s = re.sub(r"\s+", " ", s)
    for c in "’‘ʼ`´":
        s = s.replace(c, "'")
    return s.strip()


def maskele(s):
    for rx, m in MASKE:
        s = rx.sub(m, s)
    return s


def bloklar(h):
    """(tur, metin) listesi: tur 'g' govde adayi, 'b' baslik adayi (h3-h6)."""
    soup = BeautifulSoup(h, "html.parser")
    ana = soup.find(id="tcmbMainContent")
    if ana is None:
        return None
    for sp in ana.find_all("sup"):
        sp.decompose()
    for br in ana.find_all("br"):
        br.replace_with("@@BR@@")
    adaylar = []
    for el in ana.find_all(["p", "li", "div", "h3", "h4", "h5", "h6"]):
        if el.find_parent(["table"]) is not None or el.find_parent(["h1", "h2", "h3", "h4", "h5", "h6"]) is not None:
            continue
        if el.name == "div" and el.find(["p", "li", "div", "table", "h1", "h2", "h3", "h4", "h5", "h6"]):
            continue
        if el.name in ("p", "li") and el.find(["p", "li"]):
            continue
        adaylar.append(el)
    cikti = []
    for el in adaylar:
        ham = el.get_text(" ")
        # <br> sonrasi numarali paragraf basi ise ayri blok; degilse bosluk (kart: br -> bosluk)
        parcalar = re.split(r"@@BR@@\s*(?=\d{1,3}\s*[.)]\s)", ham)
        for pc in parcalar:
            t = normalize(pc.replace("@@BR@@", " "))
            if t:
                cikti.append(("b" if el.name.startswith("h") else "g", t))
    return cikti


def son_karakter_ok(t):
    t2 = t.rstrip()
    while t2 and t2[-1] in KAPANIS:
        t2 = t2[:-1].rstrip()
    return bool(t2) and t2[-1] in SON_KARAKTER


def bol(blok):
    """Kural tabanli cumle bolme (kart madde 3)."""
    rx = re.compile(r"([.!?…])([\"'”»)\]]*)\s+")
    parcalar, bas = [], 0
    for m in rx.finditer(blok):
        j = m.end()
        if j >= len(blok):
            continue
        k = j
        if blok[k] in ACILIS and k + 1 < len(blok):
            k += 1
        c = blok[k]
        if not (c.isupper() or c.isdigit()):
            continue
        if m.group(1) == "." and re.fullmatch(r"\d{1,3}", blok[bas:m.start()].strip()):
            continue  # satir ici paragraf numarasi ("... . 18. Maliye"); bolme, numara sonra silinir
        if m.group(1) == ".":
            # onceki sozcuk: onceki bosluktan noktaya (blok genelinde)
            onceki = blok[:m.start()].split(" ")[-1].lstrip(ACILIS)
            w = tr_lower(onceki)
            if w in KISALTMA or (len(w) == 1 and w.isalpha()):
                continue
        parcalar.append(blok[bas:m.end(2)])
        bas = m.end()
    parcalar.append(blok[bas:])
    return [p.strip() for p in parcalar if p.strip() and re.search(r"[^\W_]", p)]


def belge_isle(kod, h):
    bl = bloklar(h)
    if bl is None:
        return None, "govde_yok"
    bolum = ""
    cikti = []
    bidx = 0
    for tur, t in bl:
        # dipnot bloklari
        if t.startswith("*") or re.match(r"^\(\d+\)", t):
            continue
        if tur == "b" or not son_karakter_ok(t):
            # baslik adayi
            if (len(t) < 120 and not re.match(r"(Sayı|No)\s*:", t) and not re.match(r"Toplantı Tarihi", t)
                    and "TOPLANTI ÖZET" not in t.upper().replace("İ", "I").replace("ı", "I") + "" and not re.search(r"\d{4}", t)
                    and "ÖZETİ" not in t.upper()):
                bolum = t
            continue
        bidx += 1
        m = re.match(r"^\s*(\d{1,3})\s*(?:[.)]\s+|[.)](?=[^\W\d_])|[.)](?=(?:19|20)\d{2}\b)|[-\u2013]\s+)", t)
        if m:
            pno = m.group(1)
            t = t[m.end():]
        else:
            pno = "u%d" % bidx
        for i, c in enumerate(bol(t), 1):
            if i > 1:
                c = re.sub(r"^\d{1,3}\s*[.)]\s+(?=[^\W\d_])", "", c) if re.match(r"^\d{1,3}\s*[.)]\s+[A-ZÇĞİÖŞÜ]", c) else c
            cikti.append((bolum, pno, i, c))
    return cikti, ""


def main():
    belgeler = list(csv.DictReader(open(ARA / "belgeler.csv", encoding="utf-8")))
    onceki = [b for b in belgeler if b["yayin_tarihi"] and b["yayin_tarihi"] < KASA]
    onceki.sort(key=lambda b: (b["yayin_tarihi"], b["url"]))
    satirlar, sorun = [], []
    for b in onceki:
        h = (HAM / (b["belge"] + ".html")).read_text(encoding="utf-8")
        c, hata = belge_isle(b["belge"], h)
        if c is None or not c:
            sorun.append((b["belge"], hata or "cumle_yok"))
            continue
        for bolum, pno, no, metin in c:
            cid = hashlib.sha1(("%s:%s:%d" % (b["belge"], pno, no)).encode()).hexdigest()[:10]
            satirlar.append(dict(cid=cid, belge=b["belge"], yayin_tarihi=b["yayin_tarihi"], bolum=maskele(bolum),
                                 paragraf_no=pno, cumle_no=no, metin=metin, maskeli_metin=maskele(metin)))
    cids = [s["cid"] for s in satirlar]
    assert len(cids) == len(set(cids)), "cid cakismasi"
    ARA.mkdir(parents=True, exist_ok=True)
    alanlar = ["cid", "belge", "yayin_tarihi", "bolum", "paragraf_no", "cumle_no", "metin", "maskeli_metin"]
    with open(ARA / "cumleler.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alanlar)
        w.writeheader()
        w.writerows(satirlar)

    # anonim kodlar (kronolojik degil)
    kodlar = [b["belge"] for b in onceki if b["belge"] not in {s[0] for s in sorun}]
    perm = np.random.RandomState(KOD_TOHUM).permutation(len(kodlar))
    esleme = {kodlar[i]: "P%03d" % (r + 1) for r, i in enumerate(perm)}
    (ARA / "anahtar").mkdir(exist_ok=True)
    with open(ARA / "anahtar/esleme.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["belge_kodu", "belge", "yayin_tarihi"])
        for k, v in sorted(esleme.items(), key=lambda kv: kv[1]):
            yt = next(b["yayin_tarihi"] for b in onceki if b["belge"] == k)
            w.writerow([v, k, yt])

    # partiler
    pdir = ARA / "parti"
    if pdir.exists():
        shutil.rmtree(pdir)
    pdir.mkdir()
    (ARA / "etiket").mkdir(exist_ok=True)
    belge_cum = {}
    for s in satirlar:
        belge_cum.setdefault(s["belge"], []).append(s)
    sirali = [k for k in kodlar]  # kanonik: yayin tarihi, url
    ozet = []
    for gecis, tohum in TOHUM.items():
        p = np.random.RandomState(tohum).permutation(len(sirali))
        partiler, mevcut, n = [], [], 0
        for i in p:
            bk = sirali[i]
            k = len(belge_cum[bk])
            if mevcut and n + k > PARTI_MAX:
                partiler.append(mevcut)
                mevcut, n = [], 0
            mevcut.append(bk)
            n += k
        if mevcut:
            partiler.append(mevcut)
        for pi, bks in enumerate(partiler, 1):
            ad = "%s_%02d" % (gecis, pi)
            d = {"parti": ad, "rubrik": "v1", "belgeler": [
                {"belge_kodu": esleme[bk], "cumleler": [{"cid": s["cid"], "bolum": s["bolum"], "metin": s["maskeli_metin"]} for s in belge_cum[bk]]}
                for bk in bks]}
            (pdir / (ad + ".json")).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            ozet.append((gecis, ad, sum(len(belge_cum[bk]) for bk in bks)))

    # sizinti kontrolu
    yasak = [re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)"), re.compile(r"(?i)\b(?:%s)" % AYLAR), re.compile(r"DUY|ANO\d|https?:|www\.|tcmb\.gov"),
             re.compile(r"\d{1,2}[./]\d{1,2}[./]\d{2,4}")]
    ihlal = 0
    for f in sorted(pdir.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for b in d["belgeler"]:
            for c in b["cumleler"]:
                for alan in (c["metin"], c["bolum"]):
                    if any(r.search(alan) for r in yasak):
                        ihlal += 1
                        print("SIZINTI?", f.name, c["cid"], alan[:80])
    toplam = sum(n for _, _, n in ozet if _ == "A")
    print("kasa oncesi belge:", len(kodlar), "cumle:", len(satirlar), "sorunlu belge:", sorun, "sizinti ihlali:", ihlal)
    assert all(sum(n for g, _, n in ozet if g == x) == len(satirlar) for x in TOHUM)
    for g, ad, n in ozet:
        print(g, ad, n)


if __name__ == "__main__":
    main()
