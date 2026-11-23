"""TCMB haftalik banka ve kredi karti harcamasi (toplam) -> reel, aylik gunluk ortalama (H-002 gostergesi).

Kaynak: EVDS3 veri grubu bie_kkhartut, TOPLAM seri TP.KKHARTUT.KT1 (bin TL, haftalik, Cuma).

Islem sirasi
    1. bie_kkhartut grubunun tum serilerini indirir, ham JSON'u data/ham/tcmb_kart/ altina
       tarih damgali yazar (gecmis baskilari sonradan karsilastirmak icin silinmez).
    2. Toplam tanimini dogrular: KT1 = KT2..KT26 + KT49 (bilgi amacli KT50/KT51 haric).
    3. Haftalik tutar, haftanin 7 gunune (Cumartesi..Cuma; Cuma tarihi haftanin son gunudur)
       esit dagitilir. Aylik deger = o aya dusen gunlerin gunluk ortalamasi
       (aylik toplam / ayin gun sayisi). Ay ancak TUM gunleri veriyle kapliysa "tam" sayilir.
    4. TUFE (tcmb_tufe.py'nin zincirlenmis 2003=100 serisi) ile bolunur:
       reel = nominal_gunluk_ortalama / TUFE * 100  (2003 fiyatlariyla, bin TL/gun).
    5. Yazar:
         data/islenmis/tcmb_kartharcamareel_turkiye_aylik.csv         tarih,deger (yalniz tam aylar)
         data/islenmis/tcmb_kartharcamareel_turkiye_aylik_kapsam.csv  tum aylar, gecerli gun sayisi

Kullanim:  python src/veri/tcmb_kart_harcama.py [--tufe-yenileme-yok]
Kasa tarihinde KESME YAPILMAZ; kesmeyi test motoru yapar.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evds3_istemci as ev  # noqa: E402
import tcmb_tufe  # noqa: E402

KOK = ev.KOK
GRUP = "bie_kkhartut"
TOPLAM = "TP.KKHARTUT.KT1"
HAM = KOK / "data" / "ham" / "tcmb_kart"
CIKTI = KOK / "data" / "islenmis" / "tcmb_kartharcamareel_turkiye_aylik.csv"
KAPSAM = KOK / "data" / "islenmis" / "tcmb_kartharcamareel_turkiye_aylik_kapsam.csv"
BASLANGIC = "01-01-2014"  # veri grubu 07-03-2014'ten (Mart 2014) baslar; oncesi bos doner
TOPLAM_TOLERANS_BIN_TL = 20.0  # bilesenlerin bin TL'ye yuvarlanmasindan kaynaklanir


def indir() -> tuple[list, dict]:
    HAM.mkdir(parents=True, exist_ok=True)
    damga = date.today().strftime("%Y%m%d")
    liste = ev.seri_listesi(GRUP)
    yanit = {}
    for s in liste:
        kod = s["SERIE_CODE"]
        yanit[kod] = ev.seri_ham(kod, BASLANGIC)
        time.sleep(0.25)
    (HAM / f"{GRUP}_serilistesi_{damga}.json").write_text(json.dumps(liste, ensure_ascii=False), encoding="utf-8")
    (HAM / f"{GRUP}_ham_{damga}.json").write_text(json.dumps(yanit, ensure_ascii=False), encoding="utf-8")
    return liste, yanit


def genis_tablo(yanit: dict) -> pd.DataFrame:
    seriler = {k: ev.ham_to_seri(v, k, "H") for k, v in yanit.items()}
    return pd.DataFrame(seriler).sort_index()


def toplam_dogrula(df: pd.DataFrame, liste: list) -> dict:
    ad = {s["SERIE_CODE"]: s["SERIE_NAME"] for s in liste}
    if not ad[TOPLAM].upper().startswith("TOPLAM"):
        raise SystemExit(f"{TOPLAM} adi 'TOPLAM' ile baslamiyor: {ad[TOPLAM]!r}; seri secimi gozden gecirilmeli")
    bilgi_kodlari = [k for k, a in ad.items() if a.startswith("Bilgi için")]
    bilesen = [k for k in ad if k != TOPLAM and k not in bilgi_kodlari]
    gecerli = df[TOPLAM].dropna().index
    fark = (df.loc[gecerli, TOPLAM] - df.loc[gecerli, bilesen].sum(axis=1, min_count=1)).abs()
    if fark.max() > TOPLAM_TOLERANS_BIN_TL:
        raise SystemExit(f"UYARI: {TOPLAM} bilesen toplamindan sapiyor (maks {fark.max():.0f} bin TL)")
    dahil_olsaydi = (df.loc[gecerli, bilgi_kodlari].sum(axis=1) / df.loc[gecerli, TOPLAM]).median()
    return {"toplam_adi": ad[TOPLAM], "bilesen_sayisi": len(bilesen), "bilgi_kodlari": bilgi_kodlari,
            "maks_fark_bin_tl": float(fark.max()), "bilgi_kalemi_payi_medyan": float(dahil_olsaydi)}


def haftalik_kontrol(s: pd.Series) -> dict:
    s = s.dropna()
    if not (s.index.dayofweek == 4).all():
        raise SystemExit("Haftalik tarihler Cuma degil; gun dagitim varsayimi gecersiz")
    aralik = pd.Series(s.index[1:] - s.index[:-1])
    if not (aralik == pd.Timedelta(days=7)).all():
        raise SystemExit(f"Haftalik seride bosluk var: {s.index[1:][aralik != pd.Timedelta(days=7)][:5].tolist()}")
    if (s <= 0).any():
        raise SystemExit("Haftalik toplamda sifir/negatif deger var")
    return {"ilk": s.index.min(), "son": s.index.max(), "hafta": len(s)}


def aylik_nominal(haftalik: pd.Series) -> pd.DataFrame:
    """Haftalik -> gunluk (esit dagitim) -> aylik gunluk ortalama + kapsam."""
    h = haftalik.dropna()
    gunler, degerler = [], []
    for cuma, tutar in h.items():
        for geri in range(7):  # Cumartesi .. Cuma
            gunler.append(cuma - pd.Timedelta(days=geri))
            degerler.append(tutar / 7.0)
    gunluk = pd.Series(degerler, index=pd.DatetimeIndex(gunler)).sort_index()
    if not gunluk.index.is_unique:
        raise SystemExit("Gunluk dagitimda cakisan gun var")
    ay = gunluk.index.to_period("M")
    g = gunluk.groupby(ay)
    tablo = pd.DataFrame({"gun_sayisi": g.size(), "nominal_gunluk_ort_bin_tl": g.mean()})
    tablo["ay_gun_sayisi"] = [p.days_in_month for p in tablo.index]
    tablo["tam_ay"] = (tablo["gun_sayisi"] == tablo["ay_gun_sayisi"]).astype(int)
    tablo.index = tablo.index.to_timestamp()
    tablo.index.name = "tarih"
    return tablo


def kaynak_yaz(liste, dog, hk, tablo, tufe_son) -> None:
    tam = tablo[tablo["tam_ay"] == 1]
    kismi = tablo[tablo["tam_ay"] == 0]
    kismi_metin = ", ".join(f"{t:%Y-%m} ({int(r.gun_sayisi)}/{int(r.ay_gun_sayisi)} gun)" for t, r in kismi.iterrows()) or "yok"
    metin = f"""TCMB Banka ve Kredi Karti Sektorel Harcama Istatistikleri - haftalik harcama tutari
==================================================================================
Indirme tarihi : {date.today().isoformat()}
Kaynak         : TCMB EVDS3 web servisi, taban adres https://evds3.tcmb.gov.tr/igmevdsms-dis/
                 veri grubu {GRUP}, {len(liste)} seri (anahtar HTTP basliginda 'key'; bu dosyada ve kodda yer almaz)
Kullanilan seri: {TOPLAM}  "{dog['toplam_adi']}"  (haftalik, Cuma; birim bin TL; kumulatif/akim)
Ham dosyalar   : {GRUP}_ham_<YYYYMMDD>.json (29 serinin API yaniti, degistirilmeden), {GRUP}_serilistesi_<YYYYMMDD>.json
                 Tarih damgali kopyalar silinmez: TCMB haftalik veriyi gecici yayimlar ve gecmis haftalari revize eder
                 (Revizyon Politikasi); sonradan eski kopya ile yeni indirme karsilastirilabilir.
Isleme betigi  : src/veri/tcmb_kart_harcama.py  (TUFE icin src/veri/tcmb_tufe.py)
Metaveri       : https://www.tcmb.gov.tr/wps/wcm/connect/93b6354a-1da9-46a6-a4fc-1b133d91d28a/Metaveri_Banka+Kart%C4%B1+ve+Kredi+Kartlar%C4%B1+Harcama+Tutar%C4%B1.pdf (Mart 2022 surumu)

Kapsam (metaveriden)
  - Turkiye'deki bankalarin POS cihazlarindan (sanal POS dahil) yerli VE yabanci kredi/banka kartlariyla yapilan harcama.
  - Nakit avans ve nakit cekim HARIC.
  - Sektorler MCC kodlarina gore; bilgi amacli kalemler (internet, mektup/telefon [KT50, KT51], gumruk vergisi) toplama dahil degil.
  - Mevsimsel duzeltme yok. Referans donemi bir onceki hafta; yayin: her Persembe 14:30 (referans doneminin bitiminden 4 is gunu sonra).
  - Hafta Cumartesi-Cuma'dir (cikarim: veri 07-03-2014 Cuma ile baslar, Mart 2014 = 1 Mart 2014 Cumartesi; 4 is gunu gecikme Persembe'ye denk gelir).
    Metaveri hafta gunlerini acikca yazmaz.

Toplam tanimi dogrulamasi
  - {TOPLAM} = diger {dog['bilesen_sayisi']} sektor serisinin toplami (maks fark {dog['maks_fark_bin_tl']:.0f} bin TL; yuvarlama).
  - Bilgi amacli kalemler ({', '.join(dog['bilgi_kodlari'])}) toplama dahil degil (dahil olsaydi oran uyusmazdi).
  - Mart 2015'te KT25 (Kamu/Vergi) ve KT26 (Bireysel Emeklilik) KT11'den (Hizmet) ayrildi; toplam etkilenmez.
  - Toplam; Kamu/Vergi odemeleri, sigorta, bireysel emeklilik, havayolu, konaklama, egitim, saglik gibi perakende disi kalemleri de icerir.

Veri kapsami
  - Haftalik gozlem: {hk['hafta']} ({hk['ilk']:%Y-%m-%d} .. {hk['son']:%Y-%m-%d}); hafta boslugu yok.
  - Aylik: tam kapsanan ay {len(tam)} ({tam.index.min():%Y-%m}..{tam.index.max():%Y-%m}); eksik kapsanan ay: {kismi_metin} (ana dosyaya alinmaz).
  - Reel seri icin son TUFE ayi: {tufe_son:%Y-%m}.

Lisans/kosul: TCMB/EVDS veri kullanim kosullari gecerlidir, kaynak gosterilmelidir (kosul metni ayrica dogrulanmadi).
"""
    (HAM / "KAYNAK.txt").write_text(metin, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tufe-yenileme-yok", action="store_true",
                    help="TUFE'yi yeniden indirme; data/islenmis/tcmb_tufe_turkiye_aylik.csv mevcut olmali")
    a = ap.parse_args()

    tufe = tcmb_tufe.oku() if a.tufe_yenileme_yok else tcmb_tufe.calistir()

    liste, yanit = indir()
    df = genis_tablo(yanit)
    dog = toplam_dogrula(df, liste)
    haftalik = df[TOPLAM]
    hk = haftalik_kontrol(haftalik)
    tablo = aylik_nominal(haftalik)

    tablo["tufe_2003_100"] = tufe.reindex(tablo.index)
    tablo["reel_gunluk_ort"] = tablo["nominal_gunluk_ort_bin_tl"] / tablo["tufe_2003_100"] * 100.0
    ana = tablo[(tablo["tam_ay"] == 1) & tablo["reel_gunluk_ort"].notna()]

    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"tarih": ana.index.strftime("%Y-%m-%d"), "deger": ana["reel_gunluk_ort"].round(6).values}).to_csv(CIKTI, index=False)
    kap = tablo.reset_index()
    kap["tarih"] = kap["tarih"].dt.strftime("%Y-%m-%d")
    kap["nominal_gunluk_ort_bin_tl"] = kap["nominal_gunluk_ort_bin_tl"].round(3)
    kap["reel_gunluk_ort"] = kap["reel_gunluk_ort"].round(6)
    kap["tufe_2003_100"] = kap["tufe_2003_100"].round(4)
    kap[["tarih", "gun_sayisi", "ay_gun_sayisi", "tam_ay", "nominal_gunluk_ort_bin_tl", "tufe_2003_100", "reel_gunluk_ort"]].to_csv(KAPSAM, index=False)
    kaynak_yaz(liste, dog, hk, tablo, tufe.index.max())

    print(f"haftalik: {hk['hafta']} gozlem, {hk['ilk']:%Y-%m-%d}..{hk['son']:%Y-%m-%d}; {TOPLAM} '{dog['toplam_adi']}' = {dog['bilesen_sayisi']} sektorun toplami (maks fark {dog['maks_fark_bin_tl']:.0f} bin TL)")
    print(f"aylik ana dosya: {CIKTI.relative_to(KOK)}  ({len(ana)} ay, {ana.index.min():%Y-%m}..{ana.index.max():%Y-%m})")
    print(f"kapsam dosyasi : {KAPSAM.relative_to(KOK)}  ({len(tablo)} ay; tam olmayan: {int((tablo['tam_ay'] == 0).sum())})")
    kismi = tablo[tablo["tam_ay"] == 0]
    for t, r in kismi.iterrows():
        print(f"  kismi ay (ana dosyada yok): {t:%Y-%m}  {int(r.gun_sayisi)}/{int(r.ay_gun_sayisi)} gun")
    tufesiz = tablo[(tablo["tam_ay"] == 1) & tablo["reel_gunluk_ort"].isna()]
    for t in tufesiz.index:
        print(f"  TUFE'si olmayan tam ay (ana dosyada yok): {t:%Y-%m}")


if __name__ == "__main__":
    main()
