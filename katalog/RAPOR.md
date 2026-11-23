# Alternatif Veri Fizibilite Raporu: Tur 0 (keşif)

> **Yayın notu (2026-11-23):** Bu kopyada §1, §6.1 ve §12.2'den yazarın ayrı bir araştırma deposuna ait yerel yol ve iç ayrıntılar çıkarıldı. `tesisler.csv`'den aynı depoya ait `research_repo_kapsami` sütunu kaldırıldı. Raporun geri kalanı değiştirilmedi.

- **Tarih:** 2026-10-28
- **Hazırlayan:** araştırma yönetmeni (ana oturum), dört alt ajanın web doğrulamasıyla
- **Kapsam:** Kaynak kataloğu, fizibilite puanları ve hipotez kaydı. **Bu turda hiçbir hipotez test edilmedi, hiçbir veri indirilmedi**, `kayit/denemeler.csv` dosyasına dokunulmadı.

Dosyalar:

| Dosya | İçerik |
|---|---|
| `katalog/veri_kaynaklari.csv` | 83 kaynak satırı (kaynak/erişim yolu başına bir satır), puanlar ve her alanın doğrulama linkleri |
| `katalog/hedef_seriler.csv` | 21 resmi hedef/kıyas serisinin yayın gecikmesi, EVDS kodu ve ilk açıklanan değer kaynağı |
| `katalog/tesisler.csv` | 15 BIST şirketinin 29 tesisi: konum, koordinat kaynağı, karışma riski ve önerilen sinyal |
| `hipotezler/H-001.md` … `H-003.md` | Test öncesi kayda geçirilen kartlar (`onerildi`) |

---

## Özet

1. **En yüksek puanlı kaynaklar uydu değil, hızlı idari verilerdir.**
   - EPİAŞ gerçek zamanlı elektrik tüketimi (16/20) ve TCMB haftalık kartlı harcama (16/20).
   - Ardından EPİAŞ santral bazlı üretim, kartlı işlem adedi ve DHMİ havalimanı istatistikleri (15/20).
   - En iyi uydu kaynakları B sınıfındadır: NASA FIRMS 14/20; Sentinel-5P NO2 ve Sentinel-1 12/20.
2. **Öncülük için asıl kısıt hedef tarafındadır.** Alternatif veriye en çok yer bırakan hedefler:
   - perakende satış hacmi (T+42), sanayi üretimi (T+40), ihracat birim değer/miktar endeksleri (T+43)
   - TCMB aylık turizm geliri (T+43), GSYH (T+62)

   Pencerenin dar olduğu hedefler:
   - TÜFE (T+3) ve Ticaret Bakanlığı öncü dış ticaret (T+3): alan yalnız ay içi tahminde.
   - KKO ve reel kesim güven endeksi referans ay bitmeden (≈T−10) yayımlanıyor. Bunlar hedef değil, alternatif verinin geçmesi gereken çıtadır.
3. **Şirket düzeyi fikirler mevcut test motoruyla test edilemez.**
   - Motor yalnız aylık seri alıyor ve kasa (2025-04) öncesinde en az 36 gözlem istiyor.
   - Çeyreklik şirket finansalları 2018'den beri uydu verisiyle ≈27 çeyrek eder. Yeterli değil.
   - Çözüm ya aylık operasyonel hedefler (OSD üretici bazlı üretim, EPİAŞ santral üretimi) ya da motorun genişletilmesidir. İkincisi insan kararıdır.
4. **Zamana duyarlı uyarılar:**
   - Suomi NPP veri teslimi **1 Kasım 2026'da (4 gün sonra) duruyor**.
   - EOG gece ışıklarına programatik erişim 1 Haziran 2026'dan beri ücretli.
   - EVDS Ocak 2026'da `evds3`'e taşındı; README'deki `evds2` talimatı eskidi.
   - EPİAŞ API'si kullanıcı girişi istiyor.
   - İBB saatlik veri setleri 2024 sonundan beri güncellenmiyor.
   - Indeed Hiring Lab'da Türkiye yok.

   Ayrıntılar §5'te.
5. **Kayda geçenler (test edilmedi):**
   - H-001: elektrik tüketimi → imalat sanayi üretimi
   - H-002: reel kartlı harcama → perakende satış hacmi
   - H-003: Sentinel-5P NO2 (Marmara) → imalat sanayi üretimi

   H-003 seçiminde puan sırasından saptım; gerekçe §7'de. İsterseniz turizm fikriyle değiştirilebilir.

   Kartlar, hipotez ajanının işaretlediği sorunlar üzerine test öncesinde düzeltildi (§8). Bu kuralla uyumludur, çünkü hiçbir kart test edilmedi.

---

## 1. Yöntem

- **Dağıtım:** Dört alt ajan paralel çalıştı:
  - uydu
  - enerji ve lojistik
  - dijital, harcama ve hedef serilerin yayın takvimi
  - şirket/tesis ve ayrı bir şirket finansalları veri setinin salt okunur incelemesi
- **Doğrulama kuralları:**
  - Her alan web'de resmi kaynaktan doğrulandı. Linkler `veri_kaynaklari.csv` içindeki `dogrulama_linkleri` sütununda.
  - Doğrulanamayan alanlar "doğrulanamadı" olarak bırakıldı; tahminle doldurulmadı.
  - `dogrulama_notu` sütunu her satırın durumunu verir: doğrulandı / kısmen / doğrulanamadı.
- **Yönetmen kontrolü:** En kritik dört iddiayı ayrıca kendim kontrol ettim:
  - SNPP kesintisi ([NASA Earthdata uyarısı](https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-data-product-delivery-cease-november-1-2026))
  - GEE ticari olmayan kota katmanları ([GEE rehberi](https://developers.google.com/earth-engine/guides/noncommercial_tiers))
  - EOG'nin ücretli programatik erişimi ([EOG kayıt sayfası](https://eogdata.mines.edu/products/register/): "Effective June 1 2026 EOG is limiting programmatic access via OpenID Client to paid subscribers.")
  - EVDS3 geçişi ([basın duyurusu aktarımı](https://www.alomaliye.com/2026/01/26/tcmb-elektronik-veri-dagitim-sisteminin-yenilenmesine-iliskin-basin-duyurusu/))
- **Sınırlar:**
  - Hiçbir hesap açılmadı, kimlik bilgisi girilmedi.
  - Anahtarsız uç noktalara yalnızca küçük yoklama istekleri atıldı (ayrıntı §12).
- **Gecikme değerleri:** Çoğu, 28 Ekim 2026'daki tek bir gözleme dayanır. Kalıcı ortalama gecikme değildir.

## 2. Puanlama yöntemi

Her kaynak dört ölçüte göre 1-5 arası puanlandı. Toplam en fazla 20'dir; ağırlıklar eşittir.

| Ölçüt | 5 | 3 | 1 |
|---|---|---|---|
| **E: Erişim kolaylığı** | Anahtarsız, ücretsiz, makine okunur | Ücretsiz ama ağır işleme, platform koşulu gri alanı, PDF ya da kopya biriktirme gerekir | Ücretli, teklif usulü, kapsam yok veya bulunamadı |
| **G: Geçmiş uzunluğu** (kasa 2025-04 öncesi aylık gözlem) | ≤2012'den başlar | 2017-2019 (yoy ile ~60-70 gözlem) | 2022 sonrası, geçmiş yok veya başlangıç doğrulanamadı |
| **O: Öncülük potansiyeli** (zamanlılık × hedefle mekanizma bağı) | Günlük/haftalık, ≤1 hafta gecikme; ≥5 hafta gecikmeli bir hedefe mekanizmayla bağlı | 1-3 hafta öncülük ya da yalnız ay içi | Hedeften sonra gelir, güncel değil ya da veri akışı bitiyor |
| **R: Gürültü / yanıltıcı sinyal riski** (5 = düşük risk) | Doğrudan fiziksel/idari ölçüm, karıştırıcılar düzeltilebilir | Meteoroloji, mevsimsellik, örnekleme gibi ciddi karıştırıcılar | Zayıf mekanizma, normalize edilmiş/örneklemeli veri, yapısal kayma |

Puanlar yönetmenin yargısıdır. Gerekçeler CSV'deki `puan_gerekcesi` sütununda.

**Öncelik sınıfları:**

| Sınıf | Koşul |
|---|---|
| **A** | ≥15 |
| **B** | 12-14 |
| **C** | ≤11 |
| **C (öncü değil veya güncel değil)** | O = 1; toplamı ne olursa olsun |
| **D (erişilemez)** | E = 1; ücretli, kapsam yok veya bulunamadı |

**Rol sütunu (`rol`):** Bir kaynağın ne işe yaradığını ayırır.

| Rol | Ne anlama gelir |
|---|---|
| `alternatif` | Uydu, AIS, ADS-B, arama, haber vb. |
| `yuksek-frekans-idari` | EPİAŞ, TCMB kartlı harcama, EUROCONTROL gibi hızlı idari veri |
| `resmi-erken-kiyas` | Resmi istatistiğin erken sürümü ya da doğrulama serisi. Alternatif verinin yenmesi gereken çıtadır. |
| `altyapi` | Erişim altyapısı (EVDS API) |

## 3. Hedef serilerin yayın gecikmesi (öncülük penceresi)

Kaynak: `katalog/hedef_seriler.csv`. Gecikme, referans dönem sonundan yayına kadar geçen gündür; negatif değer, dönem bitmeden yayımlandığı anlamına gelir.

| Hedef | Kurum | Gecikme | Alternatif veriye yer | İlk açıklanan değer |
|---|---|---|---|---|
| Sanayi üretim endeksi | TÜİK | T+40 | Geniş, ama PMI (T+1..3) ve KKO/RKGE (T−10) çıtası yüksek | EVDS vintage tutmuyor → OECD STES Revisions (Türkiye kapsamı doğrulanmadı) ya da bülten arşivi |
| Perakende satış hacmi | TÜİK | T+42 | Çok geniş (kartlı harcama T+4 iş günü) | Aynı |
| İhracat birim değer/miktar endeksleri | TÜİK | T+43 | Orta-geniş (miktar/fiyat ayrışımı) | Bülten arşivi |
| Dış ticaret (kesin) | TÜİK | T+30 | Öncü veri T+3'te çıktığı için dar | Bülten arşivi |
| Dış ticaret (öncü) | Ticaret Bakanlığı | T+3 | Yalnız ay içi | Bülten |
| TÜFE | TÜİK | T+3 | Yalnız ay içi | Endeksler genelde revize edilmez (doğrulanamadı) |
| Yabancı ziyaretçi | KTB | T+25 | Orta | Geçici veri, sonradan güncellenir |
| Turizm geliri (aylık) | TCMB ödemeler dengesi | T+43 | Geniş | EVDS vintage tutmuyor |
| GSYH | TÜİK | T+62 | Geniş, ama çeyreklik örneklem küçük | OECD STES Revisions |
| KKO, RKGE, PMI, güven endeksleri | TCMB, İSO, TÜİK | T−10..T+3 | Yok: bunlar kıyas çıtası | KKO/RKGE revize edilmez |

Not: TÜİK 2026 takvimi birincil sayfa dinamik olduğu için ikincil bir aktarımdan alındı. Ekim 2026 yayınlarıyla (TÜFE 5 Ekim, SÜE 9 Ekim) tutarlı çıktı.

## 4. Kaynak puanları

Her satırın erişim yolu, ücret, geçmiş, frekans, gecikme, çözünürlük, lisans, hedef eşleşmeleri ve doğrulama linkleri `veri_kaynaklari.csv` içindedir. Tablo kategoriye ve puana göre sıralıdır.

#### Uydu (19)

| ID | Kaynak | Rol | E | G | O | R | Top. | Öncelik | Gerekçe |
|---|---|---|---|---|---|---|---|---|---|
| UYD-16 | NASA FIRMS aktif yangın / termal anomali (VIIRS 375 m + MODIS 1 km) | alternatif | 4 | 5 | 3 | 2 | 14 | B | Ücretsiz MAP_KEY, basit CSV, NRT ≤3 saat; demir-çelik/rafineri ısı izi; SNPP sonrası NOAA-20/21'e geçiş, sabit kaynak etiketi yalnız standart üründe |
| UYD-01 | Sentinel-5P TROPOMI NO2 — Google Earth Engine (OFFL) | alternatif | 3 | 3 | 4 | 2 | 12 | B | GEE kurulumu ve ticari olmayan kullanım gri alanı; 2018-06'dan; GEE'de ~10 gün gecikme, SÜE T+40'a karşı ~4 hafta; meteoroloji/trafik/ısınma karıştırıcı |
| UYD-02 | Sentinel-5P TROPOMI NO2 — Google Earth Engine (NRTI, near-real-time) | alternatif | 3 | 3 | 4 | 2 | 12 | B | Aynı gün hazır ama NRTI sürümleri arası tutarsızlık; öncülük OFFL'den pratikte fazla değil |
| UYD-03 | Sentinel-5P TROPOMI NO2 — Copernicus Data Space Ecosystem (CDSE) | alternatif | 3 | 3 | 4 | 2 | 12 | B | Ücretsiz hesap ama L2 dosya işleme ağır; GEE'siz yol (ticari kullanım açısından daha temiz) |
| UYD-14 | Sentinel-1 SAR GRD — Copernicus Data Space Ecosystem (CDSE) | alternatif | 3 | 4 | 3 | 2 | 12 | B | Bulut bağımsız, liman/gemi sayımı; S1B arızası (2021-12) ve S1C/S1D ile tekrar sıklığı değişti → seri kırılması |
| UYD-15 | Sentinel-1 SAR GRD — Google Earth Engine | alternatif | 3 | 4 | 3 | 2 | 12 | B | UYD-14 ile aynı; GEE kolaylığı |
| UYD-17 | EOG VIIRS Nightfire (VNF) — gaz flare / endüstriyel ısı kaynakları | alternatif | 1 | 5 | 3 | 3 | 12 | D | Isı gücünü doğrudan ölçer ama 10 Oca 2025'ten beri lisanslı: akademik değilsen ücretli |
| UYD-04 | Sentinel-5P TROPOMI NO2 — NASA GES DISC | alternatif | 3 | 3 | 3 | 2 | 11 | C | Earthdata ile ücretsiz; OFFL gecikmesi doğrulanamadı |
| UYD-07 | NASA Black Marble — LAADS DAAC (VNP46 / VJ146) | alternatif | 3 | 5 | 2 | 1 | 11 | C | Günlük ve uzun geçmiş ama gece ışığı aylık sanayi dalgalanmasını zayıf izler; SNPP→NOAA-20 geçişinde kalibrasyon kırılması |
| UYD-10 | Sentinel-2 MSI L2A — Copernicus Data Space Ecosystem (CDSE) | alternatif | 3 | 3 | 3 | 2 | 11 | C | Tesis düzeyi (stok sahası, otopark) için uygun; bulut ve yorum belirsizliği (stok artışı = üretim mi satılamayan mal mı?) |
| UYD-11 | Sentinel-2 MSI L2A — Google Earth Engine | alternatif | 3 | 3 | 3 | 2 | 11 | C | UYD-10 ile aynı; GEE kolaylığı, GEE koşulları |
| UYD-12 | Landsat 8 / Landsat 9 (OLI/TIRS) — USGS EarthExplorer/M2M ve GEE | alternatif | 3 | 4 | 2 | 2 | 11 | C | Termal 100 m yüksek fırın izi için yeterli; 8 günlük birleşik tekrar + bulut; L8 işlemesi 14-16 gün |
| UYD-13 | Landsat 5 TM ve Landsat 7 ETM+ (uzun geçmiş) — USGS ve GEE | alternatif | 3 | 5 | 1 | 2 | 11 | C (öncü değil veya güncel değil) | Yalnız tarihsel (görevler bitti); kalibrasyon/arka plan için |
| UYD-06 | VIIRS gece ışıkları VNL — EOG / Colorado School of Mines | alternatif | 2 | 5 | 1 | 2 | 10 | C (öncü değil veya güncel değil) | 1 Haz 2026'dan beri programatik erişim ücretli; aylık kompozit gecikmeli; SNPP 1 Kas 2026'da duruyor |
| UYD-08 | VIIRS VNL aylık — Google Earth Engine aynası (EOG) | alternatif | 3 | 5 | 1 | 1 | 10 | C (öncü değil veya güncel değil) | GEE aynası 2-3 ay geride; aylık makro için zayıf mekanizma |
| UYD-09 | NASA Black Marble VNP46A2 — Google Earth Engine aynası | alternatif | 3 | 5 | 1 | 1 | 10 | C (öncü değil veya güncel değil) | VNP46A2 SNPP ürünü 1 Kas 2026'da duruyor, GEE'de NOAA-20 muadili bulunamadı |
| UYD-05 | Sentinel-5P TROPOMI SO2, CO, CH4 (+HCHO) — GEE ve CDSE | alternatif | 3 | 3 | 2 | 1 | 9 | C | SO2 düşük kolonda çok gürültülü, CO/CH4 sanayiye özgü değil |
| UYD-18 | Planet PlanetScope (ticari) — Eğitim ve Araştırma programı / ticari a… | alternatif | 1 | 3 | 2 | 3 | 9 | D | Ticari; E&R programı üniversite şartlı ve 30 gün gecikmeli |
| UYD-19 | SkyFi (ticari uydu görüntü pazaryeri; uygun fiyatlı seçenek) | alternatif | 1 | 1 | 2 | 3 | 7 | D | km² başına ücretli; zaman serisi kurmak pahalı |

#### Enerji (11)

| ID | Kaynak | Rol | E | G | O | R | Top. | Öncelik | Gerekçe |
|---|---|---|---|---|---|---|---|---|---|
| ENR-01 | EPİAŞ Şeffaflık Platformu: Gerçek zamanlı tüketim | yuksek-frekans-idari | 4 | 3 | 5 | 4 | 16 | A | Ücretsiz kayıt + TGT; saatlik, ~2 saat gecikme; SÜE T+40'a karşı 5-6 hafta; sıcaklık/bayram düzeltilebilir; geçmiş birincil kaynakta doğrulanamadı (ikincil ≥2015); lisanssız GES kayması |
| ENR-04 | EPİAŞ Şeffaflık Platformu: Gerçek zamanlı üretim | yuksek-frekans-idari | 4 | 2 | 5 | 4 | 15 | A | Santral bazlı saatlik üretim G+1; şirket düzeyi (AKSEN vb.) için en doğrudan sinyal; geçmiş doğrulanamadı; hasılat = hacim × fiyat |
| ENR-09 | EPDK Petrol Piyasası Aylık Sektör Raporu (akaryakıt) | resmi-erken-kiyas | 3 | 5 | 1 | 4 | 13 | C (öncü değil veya güncel değil) | Akaryakıt satışları il bazında ama ~6 hafta gecikme |
| ENR-02 | EPİAŞ Şeffaflık Platformu: UEÇM | resmi-erken-kiyas | 4 | 2 | 1 | 5 | 12 | C (öncü değil veya güncel değil) | Uzlaştırma verisi A+1: öncü değil, doğrulama serisi |
| ENR-05 | EPİAŞ Şeffaflık Platformu: UEVM | resmi-erken-kiyas | 4 | 2 | 1 | 5 | 12 | C (öncü değil veya güncel değil) | Uzlaştırma, A+1; doğrulama serisi |
| ENR-06 | EPİAŞ Doğal Gaz Şeffaflık Platformu (natural-gas-service) | yuksek-frekans-idari | 4 | 2 | 3 | 3 | 12 | B | Günlük ulusal gaz giriş/çıkış; sanayi kırılımı yok, ısınma baskın; gecikme/geçmiş doğrulanamadı |
| ENR-07 | EPDK Doğal Gaz Piyasası Aylık Sektör Raporu | resmi-erken-kiyas | 3 | 4 | 1 | 4 | 12 | C (öncü değil veya güncel değil) | Sanayi alt kırılımlı gaz tüketimi ama ~6 hafta gecikme: hedeften sonra gelir |
| ENR-11 | EPDK Elektrik Piyasası Aylık Sektör Raporu | resmi-erken-kiyas | 3 | 4 | 1 | 4 | 12 | C (öncü değil veya güncel değil) | Şirket bazlı lisanslı üretim tabloları; ~6 hafta gecikme |
| ENR-03 | EPİAŞ Şeffaflık Platformu: İl bazlı aylık tüketim | resmi-erken-kiyas | 4 | 2 | 1 | 4 | 11 | C (öncü değil veya güncel değil) | İl × sektör kırılımı değerli ama A+1; bölgesel doğrulama için |
| ENR-10 | ENTSO-E Transparency Platform | alternatif | 2 | 1 | 3 | 4 | 10 | C | Türkiye veri setleri token olmadan görülemedi; EPİAŞ zaten birincil |
| ENR-08 | BOTAŞ | resmi-erken-kiyas | 1 | 1 | 1 | 3 | 6 | D | Günlük veri sayfası bulunamadı |

#### Lojistik (19)

| ID | Kaynak | Rol | E | G | O | R | Top. | Öncelik | Gerekçe |
|---|---|---|---|---|---|---|---|---|---|
| LOJ-16 | DHMİ Havalimanı İstatistikleri | resmi-erken-kiyas | 3 | 5 | 3 | 4 | 15 | A | 2008'den havalimanı bazında aylık; ~12 gün; KTB ziyaretçiye (T+25) karşı ~2 hafta; dış hat yolcu transfer ve giden vatandaşı da içerir |
| LOJ-13 | FlightAware AeroAPI | alternatif | 2 | 5 | 4 | 3 | 14 | B | Tarihsel veri Standard planda (aylık ≥100 USD); 2011'den |
| LOJ-05 | Spire Maritime | alternatif | 1 | 5 | 4 | 3 | 13 | D | Ticari teklif; uzun geçmiş var ama erişim pahalı |
| LOJ-15 | EUROCONTROL Daily Traffic Variation (Aviation Intelligence) | yuksek-frekans-idari | 4 | 2 | 4 | 3 | 13 | B | Anahtarsız, ~1 gün gecikme; Türkiye/havalimanı/THY/Pegasus günlük uçuş; JSON'da yalnız cari yıl + 2019/2025 referansı → günlük kopya biriktirilmeli |
| LOJ-01 | IMF PortWatch: Daily Port Activity and Trade Estimates | alternatif | 3 | 3 | 4 | 2 | 12 | B | Anahtarsız API ama IMF sistematik indirmede izin istiyor; 2019'dan; 5-11 gün gecikme; geçmiş revize ediliyor → geriye dönük testte ileriye bakma riski, anlık kopya şart |
| LOJ-08 | UAB Denizcilik Genel Müdürlüğü aylık haber bültenleri | resmi-erken-kiyas | 3 | 2 | 3 | 4 | 12 | B | Resmi konteyner sayıları ~10 gün; TÜİK kesin dış ticaret (T+30) ve miktar endeksine (T+43) karşı 3-4 hafta; PDF |
| LOJ-11 | OpenSky Network: Trino tarihsel veritabanı | alternatif | 2 | 4 | 4 | 2 | 12 | B | Tarihsel Trino yalnız akademik/kamu; Türkiye üzerinde alıcı kapsaması değişken |
| LOJ-12 | ADS-B Exchange | alternatif | 1 | 4 | 4 | 3 | 12 | D | Kurumsal teklif, asgari yıllık taahhüt |
| LOJ-17 | İBB Açık Veri Portalı (İstanbul trafik) | yuksek-frekans-idari | 5 | 4 | 1 | 2 | 12 | C (öncü değil veya güncel değil) | GÜNCEL DEĞİL: indeks kayıtları 2024-10'da bitiyor |
| LOJ-10 | OpenSky Network: REST API | alternatif | 3 | 1 | 4 | 3 | 11 | C | OAuth2 ile ücretsiz ama REST'te geçmiş yok; biriktirme gerekir |
| LOJ-02 | IMF PortWatch: Daily Chokepoint Transit Calls and Trade Volume Estima… | alternatif | 3 | 3 | 2 | 1 | 9 | C | Boğaz geçişleri çoğunlukla transit ticaret; Türkiye ticaretiyle bağı zayıf |
| LOJ-04 | MarineTraffic / Kpler | alternatif | 1 | 1 | 4 | 3 | 9 | D | Ticari sözleşme; fiyat yayımlanmıyor |
| LOJ-06 | VesselFinder API | alternatif | 2 | 1 | 3 | 3 | 9 | C | Kredi satın alımı; tarihsel uç yok |
| LOJ-14 | Flightradar24 API | alternatif | 1 | 1 | 4 | 3 | 9 | D | Fiyat doğrulanamadı |
| LOJ-18 | KGM (Karayolları Genel Müdürlüğü) trafik ve geçiş istatistikleri | resmi-erken-kiyas | 3 | 1 | 1 | 4 | 9 | C (öncü değil veya güncel değil) | Yalnız yıllık PDF; aylık seri yok |
| LOJ-07 | Global Fishing Watch API | alternatif | 3 | 2 | 1 | 1 | 7 | C (öncü değil veya güncel değil) | Balıkçılık odaklı, ticari olmayan şart; makro hedefle ilgisiz |
| LOJ-03 | AISHub | alternatif | 1 | 1 | 2 | 2 | 6 | D | AIS alıcısı işletmek şart, tarihsel arşiv yok |
| LOJ-09 | UAB Denizcilik Genel Müdürlüğü / Türk Boğazları Gemi Geçiş İstatistik… | resmi-erken-kiyas | 1 | 1 | 2 | 2 | 6 | D | Resmi site açılamadı |
| LOJ-19 | TCDD Taşımacılık / demiryolu yük istatistikleri | resmi-erken-kiyas | 1 | 1 | 1 | 3 | 6 | D | Aylık resmi seri bulunamadı |

#### Dijital (14)

| ID | Kaynak | Rol | E | G | O | R | Top. | Öncelik | Gerekçe |
|---|---|---|---|---|---|---|---|---|---|
| DIJ-11 | Wikimedia Pageviews API (Wikipedia sayfa görüntüleme) | alternatif | 5 | 4 | 3 | 1 | 13 | B | Anahtarsız, 2015-07'den; turizm için zayıf ve yapısal olarak düşen trafik (bot, arama/YZ özetleri) |
| DIJ-01 | Google Trends (Explore web arayüzü, elle CSV) | alternatif | 3 | 5 | 3 | 1 | 12 | B | 2004'ten ama örneklemeli ve her istekte yeniden 0-100 ölçekli; sahte korelasyon riski en yüksek kaynaklardan |
| DIJ-12 | GDELT (haber olay ve ton veritabanı) | alternatif | 4 | 5 | 2 | 1 | 12 | B | Erişim kolay, ama haber tonu ile makro hedef arasındaki mekanizma zayıf |
| DIJ-03 | Google Trends - resmi olmayan istemciler (pytrends, trendspy, trendsp… | alternatif | 2 | 5 | 3 | 1 | 11 | C | pytrends 2025'te arşivlendi; resmi olmayan uçlar, tekrar üretilemez |
| DIJ-05 | İŞKUR Aylık İstatistik Bülteni (açık iş, kayıtlı iş arayan) | resmi-erken-kiyas | 2 | 2 | 3 | 3 | 10 | C | İdari kayıt, T+13-14; otomatik erişim engelli (PDF/tarayıcı) |
| DIJ-13 | CEFIS / İstanbul Bilgi Üniversitesi günlük çevrimiçi gıda fiyat endek… | alternatif | 1 | 3 | 3 | 3 | 10 | D | Yayımlanan seri yok; kendi kazımamız kullanım koşulu riski taşır |
| DIJ-14 | PriceStats (State Street) çevrimiçi fiyat enflasyonu | alternatif | 1 | 1 | 4 | 3 | 9 | D | Ticari; Türkiye kapsamı doğrulanamadı |
| DIJ-02 | Google Trends API (alfa, resmi) | alternatif | 2 | 1 | 3 | 2 | 8 | C | Alfa, başvurulu; yalnız son 1800 gün → test motorunun 36 gözlem şartını kasa öncesinde karşılamaz |
| DIJ-04 | Google Trends BigQuery veri seti (bigquery-public-data.google_trends) | alternatif | 3 | 1 | 2 | 1 | 7 | C | Yalnız top-25 sorgular ve kayan pencere |
| DIJ-08 | Kariyer.net İstihdam Endeksi (basın bültenleri) | alternatif | 2 | 1 | 2 | 2 | 7 | C | Basın bültenleri düzensiz; 2026 yayını doğrulanamadı |
| DIJ-07 | LinkedIn Economic Graph (Hiring Rate / Workforce Report) | alternatif | 1 | 1 | 2 | 2 | 6 | D | Türkiye serisi kamuya açık değil |
| DIJ-06 | Indeed Hiring Lab - Job Postings Index (GitHub) | alternatif | 1 | 1 | 1 | 2 | 5 | D | Türkiye kapsanmıyor (11 ülke klasörü) |
| DIJ-09 | Adzuna API / iş ilanı verisi | alternatif | 1 | 1 | 1 | 2 | 5 | D | Türkiye kapsamı görünmüyor |
| DIJ-10 | Secretcv (yerli kariyer sitesi ilan endeksi/rapor) | alternatif | 1 | 1 | 1 | 1 | 4 | D | Yayımlanan endeks bulunamadı |

#### Harcama (4)

| ID | Kaynak | Rol | E | G | O | R | Top. | Öncelik | Gerekçe |
|---|---|---|---|---|---|---|---|---|---|
| HRC-01 | TCMB Banka ve Kredi Kartı Sektörel Harcama İstatistikleri - harcama t… | yuksek-frekans-idari | 4 | 4 | 5 | 3 | 16 | A | EVDS anahtarı; 2014-03'ten haftalık, T+4 iş günü; perakende hacmine (T+42) karşı ~5 hafta; nominal TL → reelleştirme ve karta yapısal kayma riski |
| HRC-02 | TCMB Banka ve Kredi Kartı İşlem Adedi (haftalık) | yuksek-frekans-idari | 4 | 4 | 4 | 3 | 15 | A | İşlem adedi enflasyondan bağımsız ama ortalama sepet değişimini kaçırır |
| HRC-04 | TCMB kartlı harcama - internet üzerinden yapılan alışveriş kalemi (bi… | yuksek-frekans-idari | 4 | 4 | 3 | 2 | 13 | B | İnternet alışverişi bilgi kalemi; kanal kayması trendi baskın |
| HRC-03 | BKM (Bankalararası Kart Merkezi) aylık kartlı ödeme istatistikleri | yuksek-frekans-idari | 3 | 3 | 3 | 3 | 12 | B | Aylık, T+17; il kırılımı görünmüyor; nominal |

#### Diğer (16)

| ID | Kaynak | Rol | E | G | O | R | Top. | Öncelik | Gerekçe |
|---|---|---|---|---|---|---|---|---|---|
| DGR-04 | Ticaret Bakanlığı geçici (öncü) dış ticaret verileri + TİM ihracat ra… | resmi-erken-kiyas | 4 | 2 | 3 | 5 | 14 | B | Hedefin kendisinin öncü sürümü (T+3); alternatif veri bunun önüne ancak ay içinde geçebilir |
| DGR-09 | Kültür ve Turizm Bakanlığı sınır giriş istatistikleri (yabancı ziyare… | resmi-erken-kiyas | 4 | 2 | 2 | 5 | 13 | B | Turizm hedefinin kendisi (T+25) |
| DGR-10 | TÜİK Motorlu Kara Taşıtları (trafiğe kayıt) bülteni | resmi-erken-kiyas | 4 | 2 | 2 | 5 | 13 | B | Resmi; ODMD daha erken |
| DGR-11 | TCMB Konut Fiyat Endeksi (KFE) | resmi-erken-kiyas | 4 | 2 | 2 | 5 | 13 | B | Resmi konut fiyat endeksi; T+16 |
| DGR-03 | OSD (Otomotiv Sanayii Derneği) üretim, ihracat ve iç pazar istatistik… | resmi-erken-kiyas | 3 | 2 | 3 | 4 | 12 | B | Üretici bazlı aylık üretim T+10-12: FROTO/TOASO için aylık şirket hedefi; SÜE otomotiv alt kalemine ~4 hafta |
| DGR-02 | ODMD otomobil ve hafif ticari araç pazarı satışları | resmi-erken-kiyas | 3 | 2 | 2 | 4 | 11 | C | Satışlar T+2 ile çok erken ama hedefle (SÜE) bağı dar; geçmiş doğrulanamadı |
| DGR-05 | Türk Çimento (eski adıyla Türkiye Çimento Müstahsilleri Birliği, TÇMB… | resmi-erken-kiyas | 2 | 2 | 3 | 4 | 11 | C | Çimento üretim/satış; site JS ile yükleniyor, gecikme doğrulanamadı |
| DGR-08 | İBB Trafik İndeksi Web Servisi (canlı) | yuksek-frekans-idari | 5 | 1 | 3 | 2 | 11 | C | Canlı ama geçmişi yok; biriktirmeden test edilemez |
| DGR-15 | İTO İstanbul Tüketici Fiyat İndeksi (perakende) ve toptan fiyat indek… | resmi-erken-kiyas | 3 | 2 | 2 | 4 | 11 | C | İstanbul TÜFE'si ayın 1'inde (TÜFE T+3'ten 2 gün önce) |
| DGR-06 | İBB Açık Veri - Saatlik Trafik Yoğunluğu Veri Seti | yuksek-frekans-idari | 5 | 2 | 1 | 2 | 10 | C (öncü değil veya güncel değil) | GÜNCEL DEĞİL: Ocak 2025'te bitiyor |
| DGR-07 | İBB Açık Veri - Saatlik Toplu Ulaşım Veri Seti | yuksek-frekans-idari | 5 | 2 | 1 | 2 | 10 | C (öncü değil veya güncel değil) | GÜNCEL DEĞİL: Aralık 2024'te bitiyor |
| DGR-12 | REIDIN Emlak Endeks (aylık rapor) | alternatif | 2 | 2 | 2 | 3 | 9 | C | Aylık PDF; ticari veri koşulları belirsiz |
| DGR-16 | ETBİS e-ticaret istatistikleri (Ticaret Bakanlığı) | resmi-erken-kiyas | 3 | 1 | 1 | 4 | 9 | C (öncü değil veya güncel değil) | Yıllık, 4-5 ay gecikme |
| DGR-13 | Endeksa konut m2 fiyat ve endeks verisi | alternatif | 1 | 1 | 2 | 2 | 6 | D | Erişim doğrulanamadı |
| DGR-14 | sahibinden.com Emlak Endeksi | alternatif | 1 | 1 | 1 | 2 | 5 | D | Yayımlanmış endeks bulunamadı |
| DGR-01 | TCMB EVDS web servisi / API (EVDS 3, beta) | altyapi |  |  |  |  | - | puanlanmadı | Erişim altyapısı (EVDS3); puanlanmadı. Ocak 2026'da evds3'e taşındı, anahtar başlıkta |

### 4.1 Kaynak grubu → hedef eşleşmesi (özet)

| Kaynak grubu | Makro hedef adayları | Şirket düzeyi adaylar (BIST) |
|---|---|---|
| EPİAŞ gerçek zamanlı tüketim | Sanayi üretimi, GSYH | (dolaylı) elektrik-yoğun sektörler |
| EPİAŞ santral bazlı üretim | Elektrik üretim karması | AKSEN, GWIND, ODAS vb. üreticiler. Santral ↔ şirket eşlemesi API'den (`powerplant-list`, `organization-list`). |
| TCMB haftalık kartlı harcama | Perakende satış hacmi, özel tüketim, turizm (yabancı kart) | Perakende (BIMAS, MGROS vb.); sektör MCC kırılımıyla |
| Sentinel-5P NO2/SO2 | Sanayi üretimi (bölgesel), ısınma/trafik ayrıştırması | İzole tesisler: Erdemir Ereğli, Kardemir Karabük, AKSEN Göynük, Tüpraş Kırıkkale. Aliağa ve İzmit Körfezi'nde ayrıştırılamaz. |
| FIRMS / Landsat termal / VIIRS Nightfire | Ham çelik üretimi (TÇÜD), rafineri faaliyeti | EREGL, ISDMR, KRDMD (yüksek fırın), TUPRS (flare), NUHCM (döner fırın) |
| Sentinel-2 optik | İnşaat, stok sahaları | FROTO, TOASO stok araç sahası; SASA inşaat/devreye alma |
| Sentinel-1 SAR + AIS (PortWatch) | Dış ticaret miktarı, liman faaliyeti | Şirket iskeleleri: Ford Otosan Ro-Ro, Tüpraş tanker, Gübretaş |
| DHMİ / EUROCONTROL / ADS-B | Yabancı ziyaretçi, turizm geliri | PGSUS, THYAO (çağrı koduyla), TAVHL (havalimanı bazında) |
| Google Trends / Wikipedia / GDELT | Turizm, tüketici talebi (zayıf mekanizma) | Marka/ürün ilgisi (yüksek sahte korelasyon riski) |
| EPDK aylık raporlar, UAB, OSD, ODMD | Doğrulama ve sektör kırılımı | Tüpraş/STAR rafineri üretimi; OSD üretici bazlı aylık üretim (FROTO, TOASO) |

## 5. Zamana duyarlı bulgular ve erişim değişiklikleri

| Konu | Bulgu | Etki |
|---|---|---|
| **Suomi NPP** | NASA/NOAA: veri teslimi 1 Kasım 2026, 13:00 UTC'de duruyor (tarih değişebilir) | Black Marble VNP46, GEE'deki VNP46A2, FIRMS SNPP, EOG VNL/VNF'nin SNPP girdisi kesilir. Gece ışığı kullanılacaksa NOAA-20 (VJ146, 2018'den) ile başlanmalı. Sensör geçişinde kalibrasyon kırılması beklenmeli. |
| **EOG VNL** | 1 Haziran 2026'dan beri programatik erişim yalnız ücretli abonelere; ücretsiz hesapla yalnız tarayıcıdan indirme | Otomatik veri hattı ücret gerektirir. Lisans CC BY 4.0 olarak kalıyor. |
| **EOG VNF** | 10 Ocak 2025'ten beri CC BY değil; akademik lisans ücretsiz, ticari ücretli | Akademik bağlantı yoksa pratikte erişilemez. |
| **Google Earth Engine** | 27 Nisan 2026'dan beri ticari olmayan katmanlar: Community 150, Contributor 1.000, Partner 100.000 EECU-saat/ay. Proje kaydı ve yıllık doğrulama zorunlu. | Kişisel yatırım araştırmasının "ticari olmayan" sayılıp sayılmadığı şartlarda açık değil (gri alan). GEE'siz yol var: CDSE, USGS, NASA. |
| **EVDS** | Ocak 2026'da EVDS3 beta açıldı. 28 Ekim'de `evds2` adresi `evds3`'e yönlendiriyordu. Yeni API tabanı `https://evds3.tcmb.gov.tr/igmevdsms-dis/`, anahtar `key` başlığında. | README ve `.env.example` talimatı güncellenmeli. Eski kütüphaneler bozulmuş olabilir. |
| **EVDS vintage** | EVDS geçmiş sürüm (as-of) tutmuyor | "İlk açıklanan değer" kuralı için OECD STES Revisions, TÜİK bülten arşivi ya da yayın günü kopyası gerekir. |
| **EPİAŞ** | API'de oturum zorunlu (TGT, 2 saat geçerli). Anonim istek 401 döndü. | Ücretsiz kayıt gerekir. Kayıt formunun alanları ve onay süresi doğrulanamadı. |
| **OpenSky** | REST'te basic auth 18 Mart 2026'da kaldırıldı (OAuth2). Tarihsel Trino yalnız akademik/kamu için ücretsiz. | Ticari olmayan bireysel kullanımın kategorisi netleştirilmeli. |
| **IMF PortWatch** | 36 Türk limanı, 2019'dan günlük. Haftalık güncelleme, 5-11 gün gecikme. Geçmiş revize ediliyor. | Geriye dönük testte ileriye bakma riski var; haftalık anlık kopya şart. Sistematik indirme için IMF koşulları yazılı izin istiyor. |
| **İBB Açık Veri** | Trafik indeksi 2024-10'da, saatlik yoğunluk 2025-01'de, toplu ulaşım 2024-12'de bitiyor | Güncel nowcast için kullanılamaz. Canlı trafik indeksi API'sinin geçmişi yok. |
| **İş ilanları** | Indeed Hiring Lab'da Türkiye yok; Adzuna ve LinkedIn'de Türkiye serisi bulunamadı | Türkiye'de kamuya açık iş ilanı endeksi pratikte yok. Kalan kaynak İŞKUR bülteni. |
| **Google Trends** | Resmi API hâlâ alfa ve başvurulu, yalnız son 1800 gün. pytrends 2025'te arşivlendi. | Kasa öncesinde 36 gözlemi API ile sağlamak mümkün değil. Web CSV'si örneklemeli. |
| **MarineTraffic** | Ek paket/kredi satışı durduruldu (Ocak 2025) | Ücretsiz/ucuz AIS geçmişi için tek pratik yol PortWatch. |

## 6. Şirket düzeyi fizibilite

### 6.1 Şirket finansalları (ayrı bir veri seti)

Yazarın ayrı bir BIST faktör araştırma projesindeki çeyreklik finansallar, günlük fiyatlar ve KAP rapor tarihleri salt okunur incelendi. Bu veri bu depoda yok.

**Uyarılar:**
- Çeyreklik finansallar yılbaşından kümülatiftir (YTD); satış miktarı, üretim, kapasite kullanımı ve tesis kırılımı içermez.
- Finansal seriler **ilk açıklanan değer değildir.** Bazı eski dönemler yeniden düzenlenmiş değerle yazılmış. 2023 sonundan itibaren TMS 29 enflasyon muhasebesi birimleri kırıyor. Hedef olarak kullanılırsa kartta not edilmeli.
- 2021 sonrası medyan KAP açıklama gecikmesi: Q1 40, Q2 44, Q3 37, Q4 63 gün.

### 6.2 Tesis kataloğu

- **Kapsam:** 15 şirket, 29 tesis.
- **Koordinatlar:** 25 tesisin koordinatı OSM way/relation kimliğinden alındı. Craiova ve Galata Wind'in 3 rüzgâr santralinde koordinat kaynakta bulunamadı; tahmin edilmeden boş bırakıldı.
- **Doğrulama:** 7 satır tam doğrulandı. Örnek: Erdemir 2024 entegre raporu, Ereğli %38,2 ve İskenderun %61,8 sıvı çelik payı.
- **Kısmen doğrulananlar:** 21 satırda tesis payı eski veya ikincil kaynaktan geliyor (ör. Tüpraş rafineri kapasiteleri 2019).
- **Doğrulanamayan:** 1 satır.

| Şirket | Tesis | İl / ilçe | Enlem, boylam | Doğrulama | Karışma riski | Önerilen sinyal |
|---|---|---|---|---|---|---|
| TUPRS | İzmit Rafinerisi (A ve B sahaları) | Kocaeli / Körfez (Tütünçiftlik) | 40.74953, 29.76709 | kısmen | ÇOK YÜKSEK: Gübretaş Yarımca ~5 km, Ford Otosan Gölcük ~7,6 km (körfezin karşı kıyısı), Nuh Çimento Hereke ~1… | AIS |
| TUPRS | İzmir (Aliağa) Rafinerisi | İzmir / Aliağa | 38.81394, 26.93525 | kısmen | ÇOK YÜKSEK: STAR Rafinerisi (SOCAR) ~2,0 km, Petkim ~3,0 km, Habaş demir-çelik + DGKÇ ~8,3 km, Aliağa ark oca… | AIS |
| TUPRS | Kırıkkale Rafinerisi | Kırıkkale / Merkez (Hacılar) | 39.74418, 33.46093 | kısmen | ORTA-DÜŞÜK: MKE fabrikaları ~10,6 km, Kırıkkale kent merkezi ~10 km; Ankara ~60 km. Görece izole, ancak kents… | S5P NO2 |
| TUPRS | Batman Rafinerisi | Batman / Merkez | 37.87890, 41.13765 | kısmen | YÜKSEK (flare için): Batman çevresi TPAO petrol sahaları flare'leri ve BOTAŞ tesisleri bitişik (OSM'de BOTAŞ… | Öncelik dışı |
| EREGL | Erdemir Ereğli entegre tesisi + Erdemir Limanı | Zonguldak / Karadeniz Ereğli (Gülü… | 41.26077, 31.41956 | doğrulandı | DÜŞÜK-ORTA: en yakın büyük kaynaklar Çatalağzı termik santralleri ~49 km doğuda; Ereğli ilçe merkezi bitişik… | Landsat 8/9 TIRS + VIIRS Nightfire |
| EREGL | İsdemir İskenderun entegre tesisi (EREGL konsolide bağ… | Hatay / Payas (İskenderun körfezi) | 36.73702, 36.20580 | doğrulandı (konum v… | ÇOK YÜKSEK: İskenderun Atlas kömür santrali ~5,3 km, Gübretaş İskenderun ~8 km, Erzin DGKÇ ~25 km, İSKEN Sugö… | Landsat TIRS / VIIRS |
| ISDMR | İsdemir İskenderun entegre tesisi | Hatay / Payas (İskenderun körfezi) | 36.73702, 36.20580 | doğrulandı (EREGL i… | ÇOK YÜKSEK: Atlas kömür santrali ~5,3 km, Gübretaş İskenderun ~8 km, Erzin DGKÇ ~25 km, Sugözü ~31 km; bölged… | Landsat TIRS / VIIRS termal |
| KRDMD | Kardemir Karabük entegre tesisi | Karabük / Merkez | 41.18157, 32.63536 | kısmen | DÜŞÜK-ORTA: Karabük kent merkezi bitişik (kışın kömürle ısınma NO2/SO2 kaynağı), Çatalağzı ~72 km, Erdemir ~1… | S5P NO2 |
| PETKM | Aliağa Petrokimya Kompleksi (+ Petlim limanı) | İzmir / Aliağa (Siteler Mah.) | 38.78736, 26.93641 | kısmen | ÇOK YÜKSEK: STAR Rafinerisi ~1,1 km, Tüpraş İzmir ~3,0 km, Habaş ~8 km, Aliağa çelik tesisleri/gemi söküm — S… | VIIRS Nightfire |
| SASA | Adana Sarıhamzalı entegre tesisi (polyester, PET cips,… | Adana / Seyhan (Sarıhamzalı Mah.,… | 36.98813, 35.20001 | kısmen | YÜKSEK: Adana kent merkezi ~10 km doğuda (yaklaşık, ölçülmedi; büyükşehir trafiği); çevre OSB'ler; tesis piks… | Sentinel-2 |
| AKSA | Yalova Taşköprü tesisi (akrilik elyaf + tesis-içi ener… | Yalova / Çiftlikköy (Taşköprü) | 40.68979, 29.40395 | kısmen | ORTA: tesisin kendi kojenerasyon santrali aynı sahada (şirket içi, sorun değil); Yalova kent merkezi batıda (… | S5P NO2 |
| FROTO | Kocaeli kampüsü: Gölcük (Transit) + Yeniköy (Custom) f… | Kocaeli / Gölcük–Başiskele (Yenikö… | 40.72020, 29.84902 | doğrulandı | ÇOK YÜKSEK (NO2 için): Gölcük Donanma Tersanesi bitişik, Tüpraş İzmit ~7,6 km, körfez sanayi kuşağı. Sentinel… | Sentinel-2 |
| FROTO | Eskişehir İnönü fabrikası (Ford Trucks) | Eskişehir / İnönü | 39.83876, 30.12144 | doğrulandı | DÜŞÜK karışma (İnönü kırsal) ama tesis küçük emisyon kaynağı — NO2 sinyali zayıf | Sentinel-2 |
| FROTO | Craiova fabrikası (Romanya; Temmuz 2022'den beri Ford… | Romanya / Dolj / Craiova | (kaynakta yok) | kısmen | Belirsiz (bu çalışmada incelenmedi) | Sentinel-2 stok sahası |
| TOASO | Tofaş Bursa fabrikası (+ test pisti) | Bursa / Osmangazi (Demirtaş Dumlup… | 40.26308, 29.06910 | kısmen | YÜKSEK (NO2): Oyak Renault ~10,2 km, Bursa kent merkezi, Demirtaş OSB; Sentinel-2 için orta (komşu fabrika pa… | Sentinel-2 |
| GUBRF | Yarımca tesisleri (+ iskele) | Kocaeli / Körfez (Atalar Mah.) | 40.77287, 29.71702 | kısmen | ÇOK YÜKSEK: Tüpraş İzmit ~5 km, Nuh Çimento ~9,7 km, Dilovası OSB, Körfez limanları | AIS + Sentinel-1 |
| GUBRF | İskenderun tesisi ve Gübretaş Limanı | Hatay / İskenderun (Sarıseki) | 36.66544, 36.21146 | kısmen | ÇOK YÜKSEK: Atlas kömür santrali ~2,7 km, İsdemir ~8 km | AIS |
| GUBRF | Razi Petrochemical Co. (İran, %48,88 iştirak) | İran / Huzistan / Bandar Imam Khom… | 30.42989, 49.09642 | doğrulanamadı | YÜKSEK: Bandar Imam petrokimya bölgesinde onlarca tesis bitişik | Önerilmez |
| NUHCM | Hereke çimento fabrikası (klinker fırınları) | Kocaeli / Körfez (Hereke, Hacı Aki… | 40.78245, 29.60292 | kısmen | ÇOK YÜKSEK: Diler Demir Çelik (Dilovası) ~3,6 km, Dilovası OSB, Gübretaş ~9,7 km, Tüpraş İzmit ~14 km | Landsat TIRS |
| AKSEN | Antalya 900 MW DGKÇ santrali | Antalya / Döşemealtı (Selimiye) | 37.12289, 30.60058 | doğrulandı | ORTA (NO2 için): Antalya kenti güneyde, AYT havalimanı ~30 km; EPİAŞ verisiyle karışma riski yok | EPİAŞ Şeffaflık |
| AKSEN | Bolu Göynük 270 MW linyit santrali (2×135 MW) | Bolu / Göynük | 40.25198, 30.81112 | doğrulandı | DÜŞÜK: kırsal, yakınında başka büyük kaynak yok — S5P NO2 ve SO2 için ülkedeki en temiz test sahalarından biri | EPİAŞ santral bazlı üretim |
| GWIND | Şah RES (35×Vestas V90 3 MW) | Balıkesir / Bandırma | (kaynakta yok) | kısmen | Yok (uzamsal sinyal kullanılmıyor) | EPİAŞ santral bazlı gerçek zamanlı üretim |
| GWIND | Mersin RES (14×V90 + 6×V112 + 6×V162) | Mersin / Mut | (kaynakta yok) | kısmen | Yok (uzamsal sinyal kullanılmıyor) | EPİAŞ santral bazlı gerçek zamanlı üretim |
| GWIND | Taşpınar RES + hibrit GES | Bursa / Nilüfer | (kaynakta yok) | kısmen | Yok (uzamsal sinyal kullanılmıyor) | EPİAŞ santral bazlı gerçek zamanlı üretim |
| PGSUS | İstanbul Sabiha Gökçen Havalimanı (ana üs) | İstanbul / Pendik–Tuzla | 40.89433, 29.31181 | kısmen | Uydu için YÜKSEK (SAW'da THY/AJet de üslü); ADS-B için yok (çağrı kodu PGT ile ayrışır) | ADS-B |
| TAVHL | Antalya Havalimanı (AYT) — Fraport-TAV ortak girişimi | Antalya / Muratpaşa–Aksu | 36.89994, 30.79819 | kısmen | Yok (uçuş verisi havalimanına özgü) | ADS-B sefer sayısı |
| TAVHL | İzmir Adnan Menderes Havalimanı (ADB) | İzmir / Gaziemir | 38.28954, 27.15884 | kısmen | Yok (uçuş verisi havalimanına özgü) | ADS-B sefer sayısı |
| TAVHL | Ankara Esenboğa Havalimanı (ESB) | Ankara / Akyurt | 40.12306, 32.99872 | kısmen | Yok (uçuş verisi havalimanına özgü) | ADS-B sefer sayısı |
| TAVHL | Milas-Bodrum Havalimanı (BJV) | Muğla / Milas | 37.24953, 27.67213 | kısmen | Yok (uçuş verisi havalimanına özgü) | ADS-B sefer sayısı |

### 6.3 Şirket düzeyi için kısıtlar

1. **Öncülüğü KAP'a göre değil, en hızlı kaynağa göre ölçmek gerekir.** KAP finansalları dönem sonundan 3-9 hafta sonra gelir. Ama aşağıdaki kaynaklar daha erken çıkar:
   - OSD aylık üretici bazlı üretim (T+10-12)
   - EPİAŞ santral üretimi (G+1)
   - DHMİ (T+12) ve TAV'ın aylık trafik açıklamaları

   Uydu sinyalinin katkısı bunların üstüne ne eklediğidir.
2. **NO2 ile şirket ayrıştırması yalnız izole tesislerde mümkün.** Uygun sahalar: Erdemir Ereğli, Kardemir Karabük, AKSEN Göynük ve kısmen Tüpraş Kırıkkale.
   - Aliağa'da Tüpraş, STAR, Petkim ve Habaş 1-8 km aralıkla yan yana.
   - İzmit Körfezi'nde Tüpraş, Gübretaş, Nuh ve Ford Gölcük 5-14 km arayla.
   - İskenderun'da İsdemir'in 5 km yakınında Atlas kömür santrali var.

   Bu kümelerde ancak rıhtım bazlı AIS veya yüksek çözünürlüklü termal anlamlıdır.
3. **Hacim ≠ hasılat.**
   - Elektrik üreticisinde hasılat PTF fiyatıyla, çelikte fiyat ve kurla, rafineride crack marjıyla sürülür.
   - AKSEN'de FAVÖK'ün %73'ü yurtdışından gelir.

   Hedef, operasyonel hacim olarak seçilmeli.
4. **Test motoru aylık çalışıyor, çeyreklik hedefi işlemez** (bkz. §9).

## 7. En umut verici 5 fikir

Fikir puanı, kaynak-hedef çifti için aynı dört ölçütle verildi.

| # | Fikir | E | G | O | R | Toplam | Durum |
|---|---|---|---|---|---|---|---|
| 1 | EPİAŞ elektrik tüketimi → imalat sanayi üretimi | 4 | 3 | 5 | 4 | **16** | H-001 |
| 2 | Reel haftalık kartlı harcama → perakende satış hacmi | 4 | 4 | 5 | 3 | **16** | H-002 |
| 3 | Hava trafiği (DHMİ aylık; ileride EUROCONTROL günlük) → yabancı ziyaretçi / turizm geliri | 3 | 5 | 3 | 3 | **14** | Kayıt bekliyor (H-004 adayı) |
| 4 | Sentinel-5P NO2, Marmara sanayi kuşağı → imalat sanayi üretimi | 3 | 3 | 4 | 2 | **12** | H-003 |
| 5 | Pozitif kontrol: AKSEN Göynük santrali, EPİAŞ santral üretimi ↔ S5P NO2 (şirket düzeyine geçiş kapısı) | 4 | 3 | 3 | 4 | **14** | Yöntem doğrulaması, hipotez değil |

### 1. Elektrik tüketimi → imalat sanayi üretimi (H-001)

- **Mekanizma:** Fabrika üretimi motor, fırın ve elektrik ark ocağı yüküdür. Faturalanan elektrik tüketiminin ~%40'ı sanayidedir (EPDK raporlarını aktaran ikincil kaynaklar; birincil doğrulanmalı).
- **Hedef:** İmalat (C) alt endeksi. Toplam SÜE'deki elektrik-gaz bölümü elektrik tüketimiyle tanımsal olarak bağlı olduğu için kullanılmadı.
- **Veri:** EPİAŞ saatlik veri ~2 saat gecikmeyle geliyor. Geçmiş birincil kaynakta doğrulanamadı; ikincil kaynağa göre ≥2015. Yedek yol EVDS `bie_elektuketim`.
- **Öncülük:** Ay biter bitmez hazır. SÜE T+40 olduğu için ~5-6 hafta.
- **Ana risk:**
  - sıcaklık ve hareketli bayramlar (kartta iş günü ortalamasıyla kısmen azaltıldı)
  - lisanssız GES büyümesinin şebeke tüketimini kaydırması
  - KKO, RKGE ve PMI'nin zaten erken sinyal vermesi (pratik değer)
- **Neden ilk sırada:** Mekanizma doğrudan, veri ucuz. Diğer bütün göstergelerin geçmesi gereken çıtayı da bu belirler.

### 2. Reel kartlı harcama → perakende satış hacmi (H-002)

- **Veri:** TCMB haftalık sektörel kart harcaması 2014-03'ten beri var, her Perşembe bir önceki hafta için yayımlanıyor.
- **Hedef:** TÜİK perakende hacmi T+42. Bu, katalogdaki en geniş pencere.
- **Ana risk:**
  - nominal TL serinin TÜFE ile reelleştirilmesindeki hata (2021-2024 yüksek enflasyon)
  - nakitten karta ve sonra karekod/FAST'a yapısal kayma
  - toplamda perakende dışı harcama kalemleri
  - bayram ve indirim günlerinin kayması

### 3. Hava trafiği → turizm (kayıt bekliyor)

- **Veri:**
  - DHMİ 2008'den havalimanı bazında aylık, T+12.
  - EUROCONTROL Türkiye, havalimanı ve havayolu bazında günlük, ~1 gün gecikmeyle; ama yalnız cari yıl, geçmiş biriktirilmeli.
- **Hedef:** KTB yabancı ziyaretçi (T+25) ya da TCMB turizm geliri (T+43).
- **Ana risk:** Dış hat yolcuya İstanbul'un transfer trafiği ve yurtdışına çıkan vatandaşlar karışıyor. Ziyaretçi sayısıyla ilişki kısmen mekanik.

### 4. Sentinel-5P NO2 → imalat sanayi üretimi (H-003)

- **Veri:**
  - TROPOMI L2 NO2 "collection 03": 2018-05'ten tutarlı yeniden işleme (RPRO v2.4.0), sonrası OFFL, ~8-10 gün gecikme.
  - GEE'nin OFFL L3 koleksiyonu kullanılmıyor. Temmuz 2021'deki v2.2 geçişi kirli bölgelerde kolonu %10-40 yükseltti ([KNMI](https://www.knmi.nl/research/publications/sentinel-5p-tropomi-no2-retrieval-impact-of-version-v2-2-improvements-and-comparisons-with-omi-and-ground-based-data-4fc96bb6-2d18-41ab-a0c6-a3696dccff87)). Karışık sürümlü seri, COVID sonrası toparlanmayla çakışan sahte bir pozitif ilişki üretebilirdi ([sürüm tablosu](https://www.temis.nl/airpollution/no2col/tropomi_no2_data_versions.php)).
  - Bölge: Kocaeli, Sakarya, Bursa ve Tekirdağ.
  - Plasebo bölge (Kastamonu + Sinop) test öncesi sabitlendi.
- **Ana risk:**
  - meteoroloji (rüzgâr, sınır tabakası)
  - trafik ve ısınma payı
  - 2019-08 piksel boyutu değişimi
  - 2023 sonrası küçük OFFL sürüm geçişleri
  - kış bulutluluğu
  - yalnız ~20 örneklem dışı gözlem (testin gücü düşük)
- **Hedef gecikmesi:** h=1 seçildi. Gösterge ~T+10'da hazır olduğunda önceki ayın SÜE değeri büyük olasılıkla açıklanmış olur; referansa bu bilgiyi vermek ihtiyatlı seçimdir.

### 5. Pozitif kontrol: AKSEN Göynük

- **Saha:** Göynük linyit santrali (270 MW) kırsalda, yakınında başka büyük kaynak yok. EPİAŞ santral bazlı üretimi "bilinen gerçek" olarak var.
- **Ne ölçer:** NO2/SO2 yönteminin (bulut maskesi, rüzgâr, arka plan) tek bir tesisin faaliyetini gerçekten izleyip izlemediğini.
- **Karar kuralı:**
  - NO2 burada bile santral üretimini izlemiyorsa Aliağa veya İskenderun gibi karışık sahalarda denemenin anlamı yok.
  - İzliyorsa şirket düzeyi uydu fikirleri sırayla açılabilir: Erdemir Ereğli ve Kardemir termal + NO2 → sıvı çelik; Ford Otosan stok sahası + Ro-Ro → ihracat adedi.
- **Bu bir bulgu değildir.** Üretim hacmi zaten resmi olarak biliniyor; çalışma yalnız veri hattını doğrular. AKSEN hasılatını tahmin etmek anlamına da gelmez.

**H-003 için neden NO2'yi seçtim (puan sırasından sapma):** Puan sırasıyla üçüncü fikir hava trafiği → turizm (14), NO2 ise 12. Üç gerekçeyle NO2'yi kayda geçirdim:

1. DHMİ ile KTB'nin ziyaretçi sayısı kısmen aynı insanları sayar. Testi geçmesi alternatif veri hakkında yeni bir şey söylemez.
2. KTB'ye karşı öncülük yalnız ~2 hafta.
3. Laboratuvarın asıl bilinmeyeni uydu kanalının işe yarayıp yaramadığıdır. NO2 bunun en ucuz doğrudan testidir. Elenmesi de değerli bilgidir.

Bu bir yönetmen yargısıdır. İsterseniz H-003'ü geri çekip turizm fikrini kaydederim. Kart henüz test edilmediği için bu, "test sonrası kriter değiştirme" sayılmaz.

## 8. Kayda geçen hipotezler (test edilmedi)

Üç kart `hipotez` ajanı tarafından şablondan dolduruldu ve `kayit/hipotezler.csv` dosyasına `onerildi` durumuyla eklendi.

**Ortak ve test öncesi sabitlenmiş ayarlar:**
- Dönüşüm: `yoy`. İlk açıklanan hedef değerleri bulunursa yoy aynı baskıdan hesaplanır ve test `--donusum duzey --gosterge-donusum yoy` ile çalışır.
- Hariç dönemler: `--haric 2020-03:2021-06,2023-02:2023-03,2024-02:2024-03` (COVID şoku ve baz etkisi; deprem ve 12 ay sonraki baz etkisi).
- Başarı kriteri: RMSE oranı < 0,90 ve yön isabeti ≥ %60 ve referansın yön isabetinden yüksek ve DM p < düzeltilmiş eşik.

| Kart | Gösterge | Hedef | `--hedef-gecikme` | Gerekli erişim |
|---|---|---|---|---|
| [H-001](../hipotezler/H-001.md) | EPİAŞ gerçek zamanlı tüketim, iş günü ortalaması | TÜİK SÜE imalat (C), takvim arındırılmış | 2 | EPİAŞ kaydı (yedek: EVDS) |
| [H-002](../hipotezler/H-002.md) | TCMB haftalık kartlı harcama, TÜFE ile reel, aylık günlük ortalama | TÜİK perakende satış hacmi, takvim arındırılmış | 2 | EVDS3 anahtarı |
| [H-003](../hipotezler/H-003.md) | TROPOMI L2 NO2 collection 03 (RPRO v2.4.0 + OFFL), Kocaeli + Sakarya + Bursa + Tekirdağ | H-001 ile aynı | 1 | CDSE ya da NASA Earthdata (GEE gerekmez) |

**Test öncesi yönetmen düzeltmeleri.** Hipotez ajanı kartları yazdıktan sonra aşağıdaki sorunları işaretledi. Hiçbir kart test edilmemişken düzeltildiler; her kartın sonunda kayıtlıdır:

| Sorun | Düzeltme | Kart |
|---|---|---|
| SÜE toplamındaki elektrik-gaz bölümü elektrik tüketimiyle tanımsal olarak bağlı | Hedef imalat (C) alt endeksi | H-001, H-003 |
| Deprem ayları hariç olsa da 12 ay sonra yoy bazı olarak örnekleme giriyor | `2024-02:2024-03` de hariç | Üçü de |
| Aylık toplam, artık yıl Şubat'ında yoy'u ±%3,5 kaydırıyor | Aylık günlük ortalama | H-002 |
| GEE OFFL L3'te v2.2 sürüm sıçraması (Temmuz 2021, +%10-40) sahte pozitif riski taşıyor | RPRO v2.4.0 + OFFL | H-003 |
| İlk açıklanan düzeyler farklı baz yıllarından geliyor | Yoy aynı baskıdan; `--donusum duzey` | Üçü de |

Kartlarda kayıtlı ama düzeltilmeyen, insanın bilmesi gerekenler:
- H-001'de lisanssız GES'in şebeke tüketimini aşağı kaydırma riski.
- H-002'de TÜFE'nin 2026 baz değişimi. Kasa dönemi ve canlı kullanım için zincirleme gerekir.
- H-003'te düşük test gücü (~20 örneklem dışı gözlem).
- Plasebo bölgede düşük arka plan değerleri yoy'u çok oynak yapıyor; plasebonun geçememesi bu yüzden zayıf kanıttır.

## 9. Test motoru ve süreç için öneriler (insan kararı)

Bunlar yapılmadı; yalnız öneri:

1. **Çeyreklik hedef desteği.** Şirket finansalları için motorun çeyreklik frekans ve daha düşük asgari gözlem şartıyla çalışan bir kipi gerekir. Bu, çoklu test ve küçük örneklem riskini artırır; eşiği insan belirlemeli.
2. **Ek bilgi testi.** Motor tek gösterge ve AR referansı alıyor. "NO2, elektrik tüketiminin ya da PMI/KKO'nun üstüne bilgi ekliyor mu?" sorusu için referansa bir rakip gösterge eklenebilmeli. Şüphecinin 8. maddesi bunu zaten soruyor.
3. **Vintage arşivi.** EVDS, PortWatch ve EUROCONTROL geçmişi tutmadığı ya da revize ettiği için yayın günü kopyalarını saklayan bir zamanlanmış görev gerekir. Bu insan onayı gerektirir.
4. **Hariç maskesi.** `--haric` yalnız hedef ayını örneklemden çıkarıyor. Hariç aylar sonraki satırlarda gecikmeli hedef olarak ve 12 ay sonra yoy bazı olarak örnekleme girmeye devam ediyor. Kartlar bunu deprem baz etkisini ayrıca hariç tutarak kısmen telafi ediyor. Motor düzeyinde bir çözüm daha temiz olur.
5. **Düzeltilmiş eşik sıraya bağlı.** Eşik 0,05 bölü toplam deneme sayısı olduğu için önce test edilen kart daha gevşek bir eşikle değerlendirilir. Bir turdaki kartların aynı eşikle değerlendirilmesi (ör. tur sonundaki toplam deneme sayısıyla) düşünülebilir.
6. **Dokümantasyon.** README ve `.env.example` içindeki `evds2` talimatı `evds3` olarak güncellenmeli. EPİAŞ, Earthdata ve CDSE için değişkenler eklenmeli.

## 10. Açılması gereken hesaplar ve API anahtarları (adım adım)

Kimlik bilgilerini sohbete yazmayın; `.env` dosyasına kendiniz yazın. Ajanlar `.env` okuyamaz (`settings.json` bunu yasaklar); betikler `python-dotenv` ile okur.

Değişken adlarının tam listesi `.env.example` dosyasındadır; veri betikleri yalnız bu adları okur. Başka bir projeden kopyalanan `.env` farklı adlar kullanıyorsa adları bu listeye göre değiştirin. `.env`'i doldurduktan sonra `python src/veri/anahtar_kontrol.py --baglan` her A grubu kaynağına küçük bir kimlik doğrulama isteği gönderir. Betik değerleri yazdırmaz ve veri indirmez. Hangi kartların hazır olduğunu raporlar.

### A. Kayda geçen kartlar için gerekli (öncelik sırasıyla)

**1. TCMB EVDS3** (ücretsiz). Gerekli kartlar: H-001 hedefi ve yedek göstergesi, H-002 göstergesi ve TÜFE.
1. https://evds3.tcmb.gov.tr adresinde "Üye Ol" ile kullanıcı adı, parola ve e-posta girin; e-postayı onaylayın.
2. Giriş yapın, Benim Sayfam → Profil → API anahtarını kopyalayın.
3. `.env` dosyasına yazın: `EVDS_API_KEY=...`
4. Not: Yeni API tabanı `https://evds3.tcmb.gov.tr/igmevdsms-dis/`, anahtar `key` başlığında gönderiliyor. Eski evds2 anahtarının geçerli kalıp kalmadığı doğrulanamadı; yeni hesaptan almak en güvenlisi.

**2. EPİAŞ Şeffaflık Platformu** (ücretsiz). Gerekli kart: H-001.
1. Kayıt formunu doldurun: https://kayit.epias.com.tr/epias-transparency-platform-registration-form (form JavaScript ile yükleniyor; istenen alanlar ve onay süresi doğrulanamadı).
2. Kullanıcı adınız kayıt e-postanızdır.
3. `.env` dosyasına yazın: `EPIAS_KULLANICI=...` ve `EPIAS_SIFRE=...` (öneri değişken adları).
4. Betik bileti (TGT) `POST https://giris.epias.com.tr/cas/v1/tickets` ile alacak; bilet 2 saat geçerli. API belgesi: https://seffaflik.epias.com.tr/electricity-service/technical/en/index.html

**3. NASA Earthdata Login veya Copernicus Data Space Ecosystem** (ikisi de ücretsiz; biri yeterli). **2026-10-29 güncellemesi:** H-003 için artık gerekli değil, yalnız yedek. Aynı RPRO v2.4.0 ve OFFL dosyaları AWS Açık Veri kovası `s3://meeo-s5p` içinde anahtarsız duruyor (https://registry.opendata.aws/sentinel5p/; doğrulama: hipotezler/H-003.md, erişim notu). İlk yazılan gerekçe: H-003, tutarlı NO2 ürünü (RPRO v2.4.0 + OFFL) için. Earthdata ileride Black Marble NOAA-20 (VJ146) ve FIRMS arşivi için de gerekecek; ikisini birden açmak en esnek yol.
- Earthdata Login:
  1. https://urs.earthdata.nasa.gov adresinde kayıt olun.
  2. Profilde "Generate Token" ile belirteç oluşturun.
  3. `.env` dosyasına yazın: `EARTHDATA_TOKEN=...`. GES DISC OPeNDAP ile yalnız Marmara alt kümesi indirilebilir; tam yörünge dosyası indirmek gerekmez.
- CDSE:
  1. https://dataspace.copernicus.eu adresinde kayıt olun ve e-postanızı onaylayın.
  2. `.env` dosyasına `CDSE_KULLANICI=...` ve `CDSE_SIFRE=...` yazın. Sentinel Hub Statistical API için Dashboard → User settings → OAuth clients altında bir istemci de oluşturulabilir.
  3. Ücretsiz kota: 12 TB/30 gün ve 10.000 PU/ay.

### B. Sonraki turlar için

**4. Google Earth Engine** (ticari olmayan kullanım ücretsiz). Keşif ve görselleştirme için kullanışlı; H-003 artık gerektirmiyor.
1. Google hesabınızla https://console.cloud.google.com adresinde yeni bir proje oluşturun.
2. https://code.earthengine.google.com/register adresinde projeyi Earth Engine'e "ticari olmayan" olarak kaydedin ve uygunluk sorularını yanıtlayın. Doğrulama yılda bir yenilenir.
3. Katman olarak Community (150 EECU-saat/ay, varsayılan) seçin. Contributor katmanı faturalandırma hesabı ister.
4. Terminalde `earthengine authenticate` çalıştırın, sonra `.env` dosyasına `GEE_PROJECT=<proje-kimliği>` yazın.
5. **Karar sizde:** Kişisel yatırım araştırmasının "ticari olmayan" sayılıp sayılmadığı GEE şartlarında açık değil. Çıktılar bir müşteriye, fona veya satılan bir ürüne gidecekse ticaridir. Emin değilseniz Google'a yazılı sorun ya da CDSE/Earthdata yolunu kullanın.

**5. Sentinel-2 ve Sentinel-1 için CDSE.** 3. maddede açmadıysanız şirket düzeyi fikirler (stok sahası, liman) için gerekecek.

**6. NASA FIRMS MAP_KEY** (ücretsiz).
1. https://firms.modaps.eosdis.nasa.gov/api/map_key/ adresine e-postanızı girin; anahtar e-postayla gelir.
2. Limit 10 dakikada 5.000 işlem.

**7. USGS ERS** (ücretsiz). Landsat termal için.
1. https://ers.cr.usgs.gov/register adresinde kayıt olun.
2. Toplu erişim (M2M) için ayrıca başvuru gerekir; onay süresi doğrulanamadı.

**8. OpenSky Network** (ücretsiz, sınırlı).
1. Hesap açın, Account → API client oluşturun ve `credentials.json` dosyasını indirin (OAuth2).
2. Tarihsel veritabanı (Trino) için "Request Data Access" formu var; akademik/kamu değilseniz lisans gerekebilir.

**9. IMF PortWatch** (hesap yok). Sistematik indirme ve ticari kullanım için IMF koşulları yazılı izin istiyor; kullanımdan önce IMF'ye yazmanız önerilir.

**10. Google Trends API alfa** (isteğe bağlı). Başvuru: https://developers.google.com/search/apis/trends. Yalnız son 1800 gün, onay garantisi yok.

**11. ENTSO-E** (düşük öncelik). Kayıttan sonra transparency@entsoe.eu adresine "Restful API access" konulu e-posta gönderin. EPİAŞ zaten birincil kaynak.

### C. Önerilmeyenler (ücretli veya bu proje için uygun değil)

| Kaynak | Neden |
|---|---|
| EOG VNL programatik erişim | Ücretli abonelik |
| EOG VNF | Akademik ya da ticari lisans gerekiyor |
| Planet | Ticari; E&R programı üniversite şartlı |
| SkyFi | km² başına ücret |
| MarineTraffic/Kpler, Spire, ADS-B Exchange | Teklif usulü |
| FlightAware AeroAPI | Tarihsel veri için en az 100 USD/ay |
| Flightradar24, VesselFinder | Ücretli |
| AISHub | AIS alıcı istasyonu işletmek gerekiyor |

## 11. Doğrulanamayanlar (özet)

**Enerji ve lojistik:**
- EPİAŞ: geçmiş başlangıcı, santral yayın eşiği, kullanım/lisans koşulları, kayıt formu alanları.
- BOTAŞ günlük veri; ENTSO-E'de Türkiye veri setleri; Türk Boğazları geçiş istatistikleri (site açılmadı); KGM ve TCDD aylık serileri.

**Hedef seriler:**
- EVDS seri kodlarının çoğu: yalnız veri grubu kodları ve TÜFE `TP.FG.J0` doğrulandı.
- OECD STES Revisions'ta Türkiye için hangi ölçülerin dolu olduğu.
- Türk Çimento yayın gecikmesi.

**Uydu:**
- EOG VNL aylık son ay ve gecikme; abonelik ücreti.
- GEE'de S5P OFFL'in yeniden işlenmiş veri içerip içermediği.
- Sentinel-2 L2A'nın Türkiye için GEE'deki başlangıç ayı.
- Black Marble aylık ürün gecikmesi.

**Dijital:**
- Google Trends web arayüzünün gecikmesi; LinkedIn/Kariyer.net/Secretcv endeksleri; PriceStats Türkiye kapsamı; Endeksa ve sahibinden erişimi.

**Şirket:**
- Tüpraş rafineri payları güncel değil (2019); Kardemir kapasitesi (2019).
- Gübretaş tesis payları ve Razi'nin muhasebe durumu; Pegasus'un SAW payı; TAV'ın havalimanı bazında hasılatı.

## 12. Şeffaflık notları

1. **Kişisel veri hatası (dijital ajan).** Wikimedia Pageviews API'sine atılan **tek bir** yoklama isteğinin `User-Agent` başlığına kullanıcının e-posta adresi yazıldı. Tekrarlanmadı, sonraki isteklerde genel bir tanımlayıcı kullanıldı. İleride Wikimedia için bir proje iletişim adresi kullanılmalı.
2. **Ayrı veri seti.** Şirket finansalları veri seti yalnız okundu; çalışma dosyaları ve commit geçmişi değişmedi.
3. **Yoklama istekleri.** Tümü anahtarsız ve küçük:
   - EPİAŞ: bir anonim POST (401).
   - PortWatch ArcGIS sorguları; EUROCONTROL'ün dört pano JSON'u (2-6 MB, bellekte okundu, diske yazılmadı).
   - CDSE ve GEE katalog sorguları; İBB CKAN; EVDS3 takvim ucu; OECD SDMX yapı sorguları; GitHub API; Wikimedia (1 istek).
   - Belge ve sayfa metinleri yalnız oturumun geçici klasörüne kaydedildi.
