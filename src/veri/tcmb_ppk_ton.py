"""H-005: etiketlerden PPK oncu-enflasyon ton serilerini kurar.

Girdi : data/ara/tcmb_ppk/{etiket/A_*.json,B_*.json, parti/*.json, cumleler.csv, belgeler.csv}
Cikti : data/islenmis/tcmb_ppkoncuenflasyon[A|B]_turkiye_aylik.csv, tcmb_ppkkural_turkiye_aylik.csv,
        ..._kapsam.csv, data/ara/tcmb_ppk/belge_skorlari.csv
Kart  : hipotezler/H-005.md "Puanlama ve seri kurma" ve "Kural tabanli kontrol" (birebir).
Eksik/gecersiz etiket DOLDURULMAZ; varsa seri kurulmaz, sayilar raporlanir.
Hedef/surpriz/TUFE dosyalarina dokunmaz.
"""
import json, re, sys, unicodedata
from collections import Counter
from pathlib import Path
import pandas as pd

KOK = Path(__file__).resolve().parents[2]
ARA = KOK / "data/ara/tcmb_ppk"
ISL = KOK / "data/islenmis"
KASA = pd.Timestamp("2025-04-01")
SON_AY = pd.Timestamp("2025-03-01")
TUR = {"tekrar", "oncu", "yonlendirme", "diger"}
KONU = {"enflasyon", "aktivite", "dis", "finansal", "diger"}


def tr_lower(s):
    s = s.replace("İ", "i").replace("I", "ı").lower()
    return unicodedata.normalize("NFC", s)


def dogrula(gecis, cum):
    """Dondurur: etiket dict(cid->(tur,konu,yon)), rapor dict."""
    cids_kasa_oncesi = set(cum.cid)
    rapor = dict(gecersiz_parti=[], eksik=0, fazla=0, tekrar=0, gecersiz_deger=0)
    et, sayac = {}, Counter()
    for f in sorted((ARA / "etiket").glob(f"{gecis}_*.json")):
        ad = f.stem
        beklenen = {x["cid"] for b in json.load(open(ARA / "parti" / f.name))["belgeler"] for x in b["cumleler"]}
        gecerli, neden = True, []
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            rapor["gecersiz_parti"].append((ad, "json: %s" % e)); continue
        if d.get("parti") != ad or d.get("rubrik") != "v1":
            gecerli = False; neden.append("parti/rubrik")
        yerel, c = [], Counter()
        for x in d.get("etiketler", []):
            c[x.get("cid")] += 1
            y = x.get("yon")
            ok = (x.get("tur") in TUR and x.get("konu") in KONU
                  and isinstance(y, int) and not isinstance(y, bool) and y in (-1, 0, 1)
                  and (x.get("konu") == "enflasyon" or y == 0))
            if not ok:
                rapor["gecersiz_deger"] += 1; gecerli = False
            yerel.append((x.get("cid"), x.get("tur"), x.get("konu"), y))
        kume = set(c)
        e, fz, tk = len(beklenen - kume), len(kume - beklenen), sum(v - 1 for v in c.values() if v > 1)
        if e or fz or tk:
            gecerli = False; neden.append("eksik=%d fazla=%d tekrar=%d" % (e, fz, tk))
            rapor["eksik"] += e; rapor["fazla"] += fz; rapor["tekrar"] += tk
        if not gecerli:
            rapor["gecersiz_parti"].append((ad, ";".join(neden) or "deger"))
            continue
        for cid, t, k, y in yerel:
            et[cid] = (t, k, y)
    rapor["etiketli"] = len(et)
    rapor["beklenen"] = len(cids_kasa_oncesi)
    rapor["kapsam_disi"] = len(set(et) - cids_kasa_oncesi)
    rapor["etiketsiz_cid"] = len(cids_kasa_oncesi - set(et))
    return et, rapor


def kappa(a, b):
    n = len(a)
    ca, cb, co = Counter(a), Counter(b), sum(1 for x, y in zip(a, b) if x == y)
    po = co / n
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / n ** 2
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def ata(p):
    return (p.to_period("M") if p.day >= 3 else (p.to_period("M") - 1)).to_timestamp()


def seri_yaz(ad, s):
    out = ISL / ad
    pd.DataFrame({"tarih": s.index.strftime("%Y-%m-%d"), "deger": s.values}).to_csv(out, index=False)
    return out


def main():
    cum = pd.read_csv(ARA / "cumleler.csv")
    bel = pd.read_csv(ARA / "belgeler.csv")
    bel["yayin"] = pd.to_datetime(bel.yayin_tarihi)
    bel = bel[bel.yayin < KASA].copy()
    cum = cum[pd.to_datetime(cum.yayin_tarihi) < KASA].copy()
    assert cum.cid.is_unique
    print("belge (kasa oncesi): %d | cumle: %d | cumlesi olan belge: %d" % (len(bel), len(cum), cum.belge.nunique()))

    # 1) dogrulama
    et, rap = {}, {}
    for g in "AB":
        et[g], rap[g] = dogrula(g, cum)
        print("[dogrulama %s]" % g, json.dumps(rap[g], ensure_ascii=False))
    gecersiz = any(rap[g]["gecersiz_parti"] or rap[g]["etiketsiz_cid"] or rap[g]["kapsam_disi"] for g in "AB")
    if gecersiz:
        print("HATA: eksik/gecersiz etiket var; seri KURULMADI (doldurma yok)."); sys.exit(2)

    cum["tA"], cum["kA"], cum["yA"] = zip(*cum.cid.map(et["A"]))
    cum["tB"], cum["kB"], cum["yB"] = zip(*cum.cid.map(et["B"]))

    # 2) uyum
    print("[kappa] tur=%.4f konu=%.4f" % (kappa(list(cum.tA), list(cum.tB)), kappa(list(cum.kA), list(cum.kB))))
    m = (cum.tA == "oncu") & (cum.tB == "oncu") & (cum.kA == "enflasyon") & (cum.kB == "enflasyon")
    print("[kappa] yon (iki gecista oncu+enflasyon, n=%d) = %.4f" % (m.sum(), kappa(list(cum.yA[m]), list(cum.yB[m]))))
    sA = set(cum.cid[(cum.tA == "oncu") & (cum.kA == "enflasyon")])
    sB = set(cum.cid[(cum.tB == "oncu") & (cum.kB == "enflasyon")])
    print("[jaccard] oncu+enflasyon A=%d B=%d kesisim=%d birlesim=%d J=%.4f"
          % (len(sA), len(sB), len(sA & sB), len(sA | sB), len(sA & sB) / len(sA | sB)))

    # 3) belge skorlari
    cum["mA"] = (cum.tA == "oncu") & (cum.kA == "enflasyon")
    cum["mB"] = (cum.tB == "oncu") & (cum.kB == "enflasyon")
    cum["kmet"] = cum.metin.map(tr_lower)
    aday = cum.kmet.map(lambda t: any(k in t for k in ("öncü veri", "öncü gösterge", "ana eğilim")))
    asag = re.compile(r"\b(geril|yavaşla|düş|azal|iyileş)")
    yuk = re.compile(r"\b(yüksel|art(ış|m|an|tı)|hızlan|bozul)")

    def kyon(t):
        a, y = bool(asag.search(t)), bool(yuk.search(t))
        return 0 if a == y else (-1 if a else 1)
    cum["aday"] = aday
    cum["yK"] = [kyon(t) if a else 0 for t, a in zip(cum.kmet, aday)]

    satir = []
    for _, b in bel.sort_values(["yayin", "belge"]).iterrows():
        g = cum[cum.belge == b.belge]
        sa = g.yA[g.mA].mean() if g.mA.any() else 0.0
        sb = g.yB[g.mB].mean() if g.mB.any() else 0.0
        sk = g.yK[g.aday].mean() if g.aday.any() else 0.0
        satir.append(dict(belge=b.belge, yayin_tarihi=b.yayin.strftime("%Y-%m-%d"), atanan_ay=ata(b.yayin).strftime("%Y-%m-%d"),
                          S_A=sa, S_B=sb, S_birincil=(sa + sb) / 2, S_kural=sk,
                          n_oncu_enf_A=int(g.mA.sum()), n_oncu_enf_B=int(g.mB.sum()), n_kural_aday=int(g.aday.sum())))
    bs = pd.DataFrame(satir)
    bs[["belge", "yayin_tarihi", "atanan_ay", "S_A", "S_B", "S_birincil", "S_kural"]].to_csv(ARA / "belge_skorlari.csv", index=False)
    bs["ay"] = pd.to_datetime(bs.atanan_ay)
    assert bs.ay.max() <= SON_AY, "kasa oncesi son aydan sonraya atanan belge var"
    idx = pd.date_range(bs.ay.min(), SON_AY, freq="MS")
    ay_ort = bs.groupby("ay")[["S_A", "S_B", "S_birincil", "S_kural"]].mean().reindex(idx).fillna(0.0)
    ay_say = bs.groupby("ay")[["n_oncu_enf_A", "n_oncu_enf_B", "n_kural_aday"]].sum().reindex(idx).fillna(0).astype(int)
    ay_say["n_belge"] = bs.groupby("ay").size().reindex(idx).fillna(0).astype(int)
    ISL.mkdir(exist_ok=True)
    yol = [seri_yaz("tcmb_ppkoncuenflasyon_turkiye_aylik.csv", ay_ort.S_birincil),
           seri_yaz("tcmb_ppkoncuenflasyonA_turkiye_aylik.csv", ay_ort.S_A),
           seri_yaz("tcmb_ppkoncuenflasyonB_turkiye_aylik.csv", ay_ort.S_B),
           seri_yaz("tcmb_ppkkural_turkiye_aylik.csv", ay_ort.S_kural)]
    kap = pd.DataFrame({"tarih": idx.strftime("%Y-%m-%d"), "n_belge": ay_say.n_belge.values,
                        "n_oncu_enf_A": ay_say.n_oncu_enf_A.values, "n_oncu_enf_B": ay_say.n_oncu_enf_B.values,
                        "n_kural_aday": ay_say.n_kural_aday.values})
    kap.to_csv(ISL / "tcmb_ppkoncuenflasyon_turkiye_aylik_kapsam.csv", index=False)
    print("[seri] %d ay, %s .. %s; belgesiz ay: %d" % (len(idx), idx[0].date(), idx[-1].date(), (ay_say.n_belge == 0).sum()))
    for n, c in (("birincil", "S_birincil"), ("A", "S_A"), ("B", "S_B"), ("kural", "S_kural")):
        print("  sifir olmayan ay %s: %d" % (n, (ay_ort[c] != 0).sum()))

    # 4) zaman kontrolu
    bs["gun"] = pd.to_datetime(bs.yayin_tarihi).dt.day
    erken = bs[(bs.gun <= 2)]
    print("[zaman] belge=%d; gun<=2 olan=%d (onceki aya atanan=%d, hepsi: %s)" % (
        len(bs), len(erken), (erken.atanan_ay != erken.yayin_tarihi.str[:7] + "-01").sum(),
        ",".join(erken.belge + "@" + erken.yayin_tarihi)))
    print("[zaman] yayin gunu dagilimi:", dict(sorted(Counter(bs.gun).items())))
    print("[zaman] ilk eslenmis ay: %s (ilk belge %s %s)" % (idx[0].date(), bs.belge.iloc[0], bs.yayin_tarihi.iloc[0]))

    # 5) betimsel
    yil = pd.to_datetime(bs.yayin_tarihi).dt.year
    d = pd.DataFrame({"yil": yil, "A": bs.n_oncu_enf_A, "B": bs.n_oncu_enf_B}).groupby("yil").sum()
    d["sifir_olmayan_ay_birincil"] = (ay_ort.S_birincil != 0).groupby(ay_ort.index.year).sum().reindex(d.index).fillna(0).astype(int)
    d["n_ay"] = pd.Series(1, idx).groupby(idx.year).sum().reindex(d.index).fillna(0).astype(int)
    print("[yillik oncu+enflasyon cumle sayisi (yayin yili) ve sifir olmayan ay]\n" + d.to_string())
    for y in yol:
        print("YAZILDI", y)


if __name__ == "__main__":
    main()
