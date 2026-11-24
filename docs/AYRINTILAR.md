# Ayrıntılar

README'nin kısa tuttuğu her şey: ajan rolleri ve kurallar, test motoru, tüm sonuçlar, kasa dönemi, sınırlar, yeniden üretme ve veri kaynakları.

## Araştırma disiplini

### Roller

Ana Claude Code oturumu **araştırma yönetmeni** rolündedir. Bir tur `/tur` komutuyla başlar ve iş dört alt ajana dağıtılır. Tanımlar `.claude/agents/` altında düz metindir.

| Ajan | Görevi |
|---|---|
| `hipotez` | Mekanizması olan hipotez önerir ve test öncesi kayda geçirir |
| `veri` | Veriyi bulur, indirir, temizler ve standart CSV'ye çevirir |
| `analist` | Test motorunu çalıştırır, sonucu karttaki ölçütle karşılaştırır |
| `supheci` | Ölçütü geçen hipotezi çürütmeye çalışır. Hüküm: `ELE`, `ADAY` ya da `EK-IS` |

### Kurallar (`CLAUDE.md`)

1. **Önce kayıt, sonra test.** Mekanizma, beklenen öncülük ve başarı ölçütü teste başlamadan `hipotezler/H-XXX.md` kartına ve `kayit/hipotezler.csv` dosyasına yazılır. Test sonrası ölçüt değişmez; değişmesi gerekirse yeni hipotez açılır.
2. **Tek yetkili test motoru.** Performans yalnız `src/analiz/test_et.py` ile ölçülür. Motor her çalıştırmayı, başarısız olsa bile, `kayit/denemeler.csv` dosyasına yazar.
3. **Üreten değerlendirmez.** Ölçütü geçen her hipotez şüpheciden geçer.
4. **Karar insanındır.** Sistem öneri üretir, işlem yapmaz.

### Test motoru (`src/analiz/test_et.py`)

- Referans: basit AR modeli, `y_t = a + b·y_(t−h)`. `h`, hedef serinin yayın gecikmesidir.
- Model: referansa gösterge eklenir, `y_t = a + b·y_(t−h) + c·x_(t−g)`. Çoklu gösterge (köprü regresyonu) ve Minnesota BVAR modları da var (`src/analiz/bvar.py`).
- Genişleyen pencere: son %40 örneklem dışıdır. Her ay yalnız o anda yayımlanmış olabilecek veriyle tahmin yapılır.
- Diebold-Mariano testi: kare kayıp, Newey-West varyansı (h−1 gecikme), Harvey-Leybourne-Newbold küçük örneklem düzeltmesi, tek yönlü.
- Bonferroni: anlamlılık eşiği 0,05 / projedeki toplam deneme sayısıdır. Deneme biriktikçe eşik sıkılaşır (11. denemede 0,0045).
- Ortak başarı ölçütü: RMSE oranı (model / AR) < 0,90, yön isabeti ≥ %60 ve referanstan yüksek, DM p < Bonferroni eşiği. Üçü birlikte sağlanmalı.

### Kasa ve koruma kancası

- Kasa dönemi: 2025-04 ve sonrası (`ayarlar.json`). Motor bu dönemi otomatik keser. Kasa yalnız son doğrulama için, tek sefer ve insan tarafından açılır (proje kökünde `.kasa_acik` dosyası).
- Koruma kancası (`.claude/hooks/koruma.py`): ajanların kasayı açmasını, kasa tarihini değiştirmesini ve deneme günlüğüne elle yazmasını engeller. Bu bir emniyet kemeridir, kasa değil; kararlı bir ajan başka yol bulabilir.

## Sonuç tablosu

Bütün sayılar `kayit/denemeler.csv`, `kayit/hipotezler.csv` ve `kayit/sonuclar/` dosyalarındadır. Örneklem dışı dönemler kasa öncesidir (en geç 2025-03).

| Hipotez | Soru | Ölçüt | Sonuç (ana deneme) | Durum |
|---|---|---|---|---|
| H-001 | EPİAŞ iş günü elektrik tüketimi → imalat sanayi üretimi (ilk açıklanan, yıllık) | Ortak ölçüt | Deneme 6: RMSE oranı 1,193, yön %66 (AR %69), DM p 0,90. 32 ay | **elendi** |
| H-002 | TCMB kartlı harcama (reel) → perakende satış hacmi | Ortak ölçüt | Deneme 1: RMSE oranı 0,649, yön %77,5 (AR %57,5), DM p 0,0116 < 0,05. Ölçüt geçildi. Şüpheci (deneme 2-5 ve inceleme): **ELE** | **elendi** |
| H-003 | Sentinel-5P NO2, Marmara sanayi kuşağı → imalat sanayi üretimi | Ortak ölçüt, plasebo bölge | Test edilmedi. Veri hattı yazıldı, örnek aylar doğrulandı; tam seri çıkarılmadı (~22 GB okuma) | **önerildi** |
| H-004 | Minnesota BVAR (SÜE, USD/TRY, TÜFE, AOFM) → aylık TÜFE | Ortak ölçüt + bant kalibrasyonu (ikincil) | Deneme 8: RMSE oranı 0,807, yön %77 (AR %61), DM p 0,067 > Bonferroni 0,00625. 64 ay | **elendi** |
| H-005 | TCMB PPK özetlerinin enflasyon tonu → TÜFE sürprizi (beklentiye göre) | Ortak ölçüt | Deneme 7: RMSE oranı 0,986, yön %71 (AR %75), DM p 0,247 > 0,0071. 52 ay | **elendi** |
| H-006 | Ay içi göstergeli (İTO, Brent, akaryakıt), stokastik oynaklıklı BVAR → aylık TÜFE | Kasada ortak ölçüt (2025-04 → 2026-10) | Kasa çalıştırılmadı. Şüpheci: `EK-IS` | **test-ediliyor** (dondurulmuş, kasa bekliyor) |
| H-007 | İTO + akaryakıt + kur köprü regresyonu → aylık TÜFE | Kasada ortak ölçüt | Kasa çalıştırılmadı. Şüpheci: `EK-IS` | **test-ediliyor** (dondurulmuş, kasa bekliyor) |

**H-006 ve H-007 hakkında.** İkisi de, H-004'ün nerede başarısız olduğu görüldükten sonra aynı kasa öncesi dönemde geliştirildi. Bu yüzden durumlarını yalnız kasa belirler. Kasa öncesi yapılan resmi çalıştırmalar (H-006 deneme 11: RMSE oranı 0,532, DM p 0,013; H-007 deneme 10: 0,496, DM p 0,036) **kanıt değildir**: modeller bu dönemde seçildi. İki p değeri de kendi Bonferroni eşiğinin üstündedir. Bu modelleri seçmek için yapılan keşif koşuları (`kesif/bvar/`) günlüğe yazılmadı, yani Bonferroni sayımında yoktur. Bunlar bulgu değil, **bekleyen bir sınavdır.**

Şüphecinin kasa öncesi denetiminde üç sorun çıktı ve kasa açılmadı:
1. **Ölçütün gücü sıfıra yakın.** Geliştirme döneminin kendisinde, 19 aylık kayan pencerelerin hiçbiri Bonferroni eşiğini geçmiyor (H-006'da 0/46, H-007'de 0/50). Model iyi olsa bile kasada büyük olasılıkla "kaldı" çıkar.
2. **Akaryakıt verisinde delik.** TPPD arşivinde 2025-12-17 → 2026-04-28 arasında kayıt yok.
3. **Zamanlama doğrulanmadı.** İTO verisinin kasa döneminde TÜİK'ten önce yayımlandığı kontrol edilmedi.

Kural gereği bu kartların ölçütü değiştirilmez. Düzeltilmiş ölçüt ve yamalı veri ancak yeni hipotezlerle (H-008/H-009) kullanılabilir.

### Dondurulmuş tanımlar ve zaman damgası

`hipotezler/H-006_H-007.sha256`, H-006/H-007'nin dondurulduğu andaki model tanımının, test motorunun ve verinin SHA-256 parmak izlerini tutar. Bu depo GitHub'da herkese açık yayımlandığında bu dosya ve kartlar, **kasa çalıştırılmadan önceki halleriyle** herkesin görebileceği bir tarih kazanır. Üç sınırı var:

- Dışarıdan doğrulanabilen yalnız 3 dosya. On parmak izinin üçü depoda: `src/analiz/test_et.py`, `src/analiz/bvar.py`, `hipotezler/H-006_bvar.json`. Yedisi yayımlanmayan veri dosyalarına ait; `shasum -a 256 -c` bu satırlarda "dosya yok" hatası verir.
- Kasa verisi zaten kamuya açık. 2025-04 → 2026-10 TÜFE değerleri yayımlanmış durumda. Damga, tanımların kasa çalıştırmasından önce yazıldığını gösterir, verinin hiç görülmediğini değil. Kartlar bunu açıkça belirtir: modeli tasarlayan Claude'un eğitim verisi 2026 ortasına kadar uzanır.
- Önceki tarihler kendi beyanıdır. Çalışma klasörü git ile izlenmedi. Kayıtlardaki 2026-10-28 → 2026-11-07 tarihleri sistemin kendi yazdığı tarihlerdir; dışarıdan doğrulanamaz. Bu depo araştırma bittikten sonra oluşturuldu.

## Neyin işe yaramadığı ve neden

- H-001, elektrik tüketimi. Eğitim döneminde eşzamanlı korelasyon yüksekti (0,875), ama örneklem dışında AR referansına bilgi eklemedi. 2017-2019'da 0,62 olan korelasyon, 2022-04 → 2025-03'te −0,27'ye döndü. Olası nedenler (öz tüketim güneş santralleri, 2022 enerji şoku, hava kaynaklı tüketim) doğrulanmadı.
- H-002, kartlı harcama. Ölçütü geçti ama sağlam değildi:
  - En iyi 5 ay (2022-23 şok ve baz etkisi ayları) kazancın %75'ini taşıyordu. Bu aylar çıkınca oran 0,83, DM p 0,10.
  - Kasa öncesi son 10 ayda model her ayarda AR'dan kötüydü (oran 1,11-1,22).
  - Hedef, 2024'te yeniden kurulmuş revize bir seriydi. Örneklenen aylarda ilk açıklanan değerle farkı (RMSE 4,2 puan), modelin hatası kadardı.
  - Anlamlılık, HAC gecikme sayısına ve hariç tutulan dönemlere duyarlıydı.
- H-004, BVAR. RMSE oranı 0,807 ile eşiği geçti, ama DM testi anlamlı değildi. En iyi 5 ay kazancın %113'ünü taşıyordu; bu aylar çıkınca BVAR, AR'den kötüydü (1,07). Sabit varyans varsayımı yüzünden kriz aylarında bantlar dardı.
- H-005, PPK metin tonu. Üç koşulun hiçbiri sağlanmadı. Etiketleme Claude alt ajanlarıyla iki bağımsız geçişte yapıldı (Cohen kappa ≈ 0,9). Test sonrası bir protokol sapması kayda geçti: etiketleyiciler kartta istenenin aksine belge bağlamını gördü, yani etiketler kör değildi. Bu yanlılık hipotezin lehine çalışır; hipotez buna rağmen elendi.
- Ortak örüntü: "İşe yarıyor" görünen her sonuçta kazanç birkaç şok ayında toplanıyordu. Olağan aylarda alternatif verinin basit AR modeline katkısı küçük ya da negatifti.

### Keşif: `kesif/bvar/` (bulgu değildir)

H-004 elendikten sonra yazar, modeli geliştirmek için kayıt kuralından bilerek feragat etti. `kesif/bvar/` bu çalışmanın günlüğüdür:

- Aynı örneklem dışı dönemde stokastik oynaklık ve ay içi göstergeler eklendi. En iyi varyant (V4) RMSE oranı 0,53 verdi.
- Basit bir köprü regresyonu (İTO + akaryakıt + kur + gecikmeli TÜFE) aynı aylarda 0,50 verdi. Yani nokta tahmindeki kazanç BVAR'dan değil, ay içi veriden geliyor.

Bu rakamlar **sonuç değildir.** Modeller H-004'ün hatalarına bakılarak, aynı dönemde seçildi. 5 tamamlanmış BVAR koşusu (ayrıca sonuç vermeyen 3 deneme) ve 5 köprü tanımı denendi, en iyisi seçildi. Bonferroni'ye göre hiçbiri anlamlı değil. Bu çalışmanın tek temiz sınavı kasa dönemidir; H-006 ve H-007 bunun için donduruldu.

## Sınırlar

- Referans çıtası düşük. AR modeli ay içi bilgiyi kullanmaz. Piyasa beklentisi (PKA anketi) gibi daha güçlü rakiplere karşı test yapılmadı (H-005 hariç).
- Örneklemler küçük. Örneklem dışı dönemler 32-68 ay. Bonferroni düzeltmesi bu boyutta gücü ciddi biçimde düşürür (H-006/H-007 bulgusu).
- Revize veriler. Çoğu hedef, revize ya da mevsimsellikten arındırılmış güncel seridir. Revize olan hedeflerde ilk açıklanan değer yalnız H-001'de kullanılabildi.
- Kasa tam kör değil. Kasa dönemi verileri yayımlanmış durumda ve modelleri tasarlayan dil modelinin genel bilgisinde var.
- Koruma kancası bir emniyet kemeridir; kurallar teknik olarak tam zorlanmaz.
- Ajanlar hata yapabilir. Kartlar, betikler ve şüpheci incelemeleri büyük ölçüde Claude ajanları tarafından yazıldı. Sayıların tutarlılığı kayıt dosyalarıyla kontrol edildi, ama her hesap insan tarafından tek tek yeniden yapılmadı.
- Birebir yeniden üretim mümkün değil. Veri depoda yok ve sağlayıcılar geçmişi revize ediyor.
- Yayın kopyası çalışma klasöründen birkaç noktada farklı (2026-11-23):
  - `katalog/RAPOR.md` §1, §6.1 ve §12.2: yazarın ayrı bir araştırma deposuna ait yerel yol ve iç ayrıntılar çıkarıldı.
  - `katalog/tesisler.csv`: aynı depoya ait `research_repo_kapsami` sütunu çıkarıldı.
  - `src/analiz/dogrulama/bvar_dogrulama.py`: sabit yerel yol, göreli yolla değiştirildi.
  - `requirements.txt`: eksik `scipy` ve `beautifulsoup4` eklendi.
  - `ogrenme/bvar/README.md`: depoda olmayan veri dosyaları işaretlendi.
  - `hipotezler/H-006.md`: H-006 kartında kullanıcı alıntıları nötr ifadeyle değiştirildi; içerik ve kararlar aynı.
  - `LICENSE` eklendi (kod için MIT).

  Diğer hipotez kartları, `kayit/` dosyaları ve parmak izi alınan üç dosya değiştirilmedi. `H-006.md` parmak izi dosyasında yer almıyor.

## Repo yapısı

```
.claude/
  agents/            hipotez, veri, analist, supheci ajan tanımları
  commands/tur.md    /tur komutu: bir araştırma turu
  hooks/koruma.py    kasa ve günlük koruma kancası
  settings.json      kancanın bağlanması
docs/AYRINTILAR.md   bu dosya
docs/figures/        README grafiği (scripts/grafikler.py üretir)
CLAUDE.md            değişmez kurallar (ajanlar her oturumda okur)
ayarlar.json         kasa başlangıcı (2025-04-01), örneklem dışı oran, anlamlılık
hipotezler/          H-001 … H-007 kartları, BVAR tanımları, parmak izi dosyası, SABLON.md
kayit/
  hipotezler.csv     her hipotezin durumu ve özeti
  denemeler.csv      test motorunun otomatik günlüğü (11 satır)
  sonuclar/          çalıştırmaların ayrıntılı JSON çıktıları (ay ay tahmin tabloları dahil);
                     deneme 4'ün dosyası yok. Deneme 3 ile aynı saniyede kaydedildi; dosya adı
                     saniye çözünürlüklü olduğu için büyük olasılıkla çakıştı. Günlükteki satırı duruyor.
katalog/
  RAPOR.md           Tur 0 fizibilite raporu
  veri_kaynaklari.csv  83 kaynak: puan, erişim, gecikme, lisans, doğrulama linkleri
  hedef_seriler.csv    21 resmi hedef serinin yayın gecikmesi ve kodu
  tesisler.csv         15 BIST şirketinin 29 tesisi (koordinat, sinyal önerisi)
src/
  analiz/test_et.py  tek yetkili test motoru
  analiz/bvar.py     Minnesota BVAR ve stokastik oynaklık
  analiz/dogrulama/  BVAR kodunun yapay veriyle doğrulanması
  veri/              veri çekme ve işleme betikleri
kesif/bvar/          H-004 sonrası keşif günlüğü (bulgu değil)
ogrenme/bvar/        BVAR ders defteri
bulgular/            şüpheciden geçen bulgu kartları (boş)
data/                yayımlanmaz, bkz. data/README.md
```

### Öğrenme: `ogrenme/bvar/`

`bvar_ders.ipynb`, araştırma hattının parçası olmayan bir ders defteridir. VAR'dan başlayıp Bayesçi çıkarım ve Minnesota prior'ı üzerinden sıfırdan bir BVAR kurar. λ ayarının etkisini ve kur geçişkenliğini dört EVDS serisiyle (2011-01 → 2025-03) inceler. Sonuçları `kayit/`'a girmez ve bulgu olarak kullanılmaz. Defterin kullandığı veri depoda yok; `ogrenme/bvar/veri_cek.py` ile yeniden çekilir.

## Yeniden üretme

Betikler Python 3.9-3.10 ile yazıldı ve çalıştırıldı. Bu depo hazırlanırken yeniden çalıştırılmadı.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # anahtarları yaz; .env git'e girmez
python src/veri/anahtar_kontrol.py --baglan    # anahtarları dener, değerleri yazdırmaz
```

Gerekli hesaplar `.env.example` ve `katalog/RAPOR.md` §10'da: TCMB EVDS3 anahtarı, EPİAŞ Şeffaflık kaydı. Sentinel-5P dosyaları AWS açık veri kovasından anahtarsız alınır.

| Hipotez | Veri betikleri (`src/veri/`) |
|---|---|
| H-001 | `epias_tuketim.py`, `tuik_sue_imalat.py` |
| H-002 | `tcmb_kart_harcama.py`, `tcmb_tufe.py`, `tuik_perakende.py`, `supheci_h002.py` (şüpheci denemeleri) |
| H-003 | `s5p_no2_bolge.py` |
| H-004 | `tcmb_bvar_seriler.py` |
| H-005 | `tcmb_ppk_metin.py`, `tcmb_ppk_hazirla.py`, `tcmb_ppk_ton.py`, `tcmb_tufe_surpriz.py` (etiketleme Claude alt ajanlarıyla yapıldı, betikle değil; rubrik `hipotezler/H-005_rubrik.md`) |
| H-006 / H-007 | `tcmb_ayici_seriler.py`, `tppd_akaryakit.py`, `akaryakit_usd.py`, `tppd_yama.py` (akaryakıt deliği yaması; yeni hipotez içindir) |

Her kartın "Test ayarları" bölümünde motor komutu birebir yazılıdır. **Test motorunu çalıştırmak deneme günlüğüne bir satır ekler** ve sonraki bütün Bonferroni eşiklerini değiştirir. Bu tasarım gereğidir. Kasa modunu (`--kasa`) çalıştırmak kasayı harcar.

Claude Code ile çalıştırmak için proje kökünde `claude` açılır ve `/tur <odak>` yazılır.

## Veri kaynakları ve lisanslar

**Kod lisansı:** Bu depodaki kod ve belgeler [MIT lisansı](../LICENSE) ile yayımlanır. MIT lisansı veriyi kapsamaz; aşağıdaki kaynakların verisi için her kaynağın kendi kullanım koşulları geçerlidir.

Veri bu depoda yeniden dağıtılmaz. Koşullar, katalogda satırı olan kaynaklar için `katalog/veri_kaynaklari.csv` içindeki `lisans` ve `dogrulama_linkleri` sütunlarından (2026-10-28 itibarıyla), diğerleri için hipotez kartlarından alındı. "Doğrulanmadı" yazanların koşulu kontrol edilmedi. `kayit/sonuclar/` altındaki JSON dosyaları, her ay için gerçekleşen hedef değerini (ör. resmi TÜFE) ve tahminleri içerir.

| Kaynak | Kullanıldığı yer | Koşul |
|---|---|---|
| TCMB EVDS (kartlı harcama, TÜFE, USD/TRY, AOFM, SÜE, Brent, PKA beklentisi) | H-002, H-004 – H-007 | [EVDS Kullanım Şartları](https://evds3.tcmb.gov.tr/igmevdsms-dis/documents/showDocument?docId=18): kaynak gösterilmeli |
| İTO İstanbul geçinme endeksi (EVDS üzerinden çekildi) | H-006, H-007 | İTO'nun kendi koşulu doğrulanmadı (katalog DGR-15) |
| TÜİK (bültenlerden ilk açıklanan imalat SÜE) | H-001 | Koşullar doğrulanmadı |
| OECD Data Explorer (TÜİK perakende hacim endeksinin OECD aynası, `DF_INDSERV`) | H-002 | Koşullar doğrulanmadı |
| EPİAŞ Şeffaflık Platformu | H-001 | Yeniden dağıtım koşulu resmi sayfalarda bulunamadı (katalog notu) |
| Copernicus Sentinel-5P TROPOMI (AWS `meeo-s5p` kovası) | H-003 | [Sentinel veri yasal notu](https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice): açık erişim, atıf "Copernicus Sentinel data [yıl]" |
| geoBoundaries TUR ADM1 | H-003 (il sınırları) | H-003 kartında: kaynak OSM, CC BY-SA 2.0 (doğrulanmadı) |
| TCMB PPK toplantı özetleri | H-005 | Koşullar doğrulanmadı |
| TPPD akaryakıt fiyat arşivi, Petrol Ofisi fiyat arşivi | H-006, H-007 | Koşullar doğrulanmadı |

**TCMB notu.** EVDS verisinin sağlayıcısı TCMB'dir. Bu depodaki yorumlar ve analizler yazara ve kullanılan yapay zekâ araçlarına aittir; TCMB'yi bağlamaz.

**Yatırım tavsiyesi değildir.** Bu depo bir araştırma sürecinin kaydıdır. Hiçbir sonuç alım satım kararına dayanak olarak sunulmaz.

## Araçlar ve yapay zekâ beyanı

Claude Code araştırma asistanı olarak kullanıldı; tasarım kararları ve yorum yazara ait.

Ayrıntı, kayıtlarla tutarlı olsun diye:
- Sistemin kendisi Claude Code üzerinde kurulu. Kayıtlarda "yönetmen" diye geçen rol, yazarın yönlendirmesiyle çalışan ana Claude Code oturumudur. Kartlardaki bazı test öncesi ayrıntı kararlarını bu oturum yazdı.
- Hipotez kartları, veri betikleri, test raporları ve şüpheci incelemeleri büyük ölçüde Claude ajanları tarafından yazıldı.
- H-005'teki cümle etiketleri Claude alt ajanlarınca üretildi; insan denetimi yapılmadı.
- Kasayı açma, kayıt kuralından feragat (kesif/bvar) ve hangi sonucun bulgu sayılmayacağı gibi kararlar yazarındır.

Kullanılan araçlar: Python (pandas, numpy, scipy, h5py, shapely), Jupyter, Claude Code.
