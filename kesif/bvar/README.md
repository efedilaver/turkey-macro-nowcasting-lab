# BVAR geliştirme (keşif)

**Bu klasördeki hiçbir sonuç bulgu değildir.** H-004 elendikten sonra kullanıcı, modeli geliştirmek için hipotez kaydı kuralından feragat etti (2026-11-07). Buradaki çalıştırmalar:

- resmi test motorunun BVAR hesabını (`test_et.calistir_bvar`) kullanır ama `kayit/denemeler.csv`'ye **yazmaz**;
- H-004 ile **aynı örneklem dışı dönemi** (2019-12 → 2025-03) kullanır. Bu dönemin sonuçları H-004'te görüldüğü için buradaki iyileşmeler iyimser okunmalıdır (aynı veride ayar yapma riski);
- kasayı (2025-04+) **hiç açmaz**. Kasa, bu geliştirmelerin ileride temiz sınanabileceği tek dönemdir.

Her çalıştırma `varyant_gunlugu.csv`'ye eklenir; böylece kaç varyant denendiği bellidir.

## Önceden yazılan varyantlar (sonuçlar görülmeden, 2026-11-07)

H-004'te görülen iki zayıflığa yönelik:

| Varyant | Değişiklik | Neyi sınar |
|---|---|---|
| V1_sv | H-004 + ortak stokastik oynaklık (CCM 2016; φ = 0,95, s² ~ IG(3; 0,1)) | Kriz aylarında bantlar genişler mi? |
| V2_ayici | H-004 + İTO geçinme endeksi (kendi mevsimselliğinden arındırılmış, aylık log fark) + Brent (TL) | Ay içi bilgi şok aylarını yakalar mı? |
| V3_ayici_sv | V2 + stokastik oynaklık | İkisi birlikte |
| V4 (veri bulunursa) | V3 + akaryakıt pompa fiyatı + doğalgaz ve elektrik konut tarifesi | Yönetilen fiyatlar ek katkı yapar mı? |

Ana ölçüm H-004'le aynı: aylık enflasyon (logdiff, h = 1). V1 ve V3 ayrıca yıllık enflasyon (yoy, h = 12) ile koşulur.

## Çalıştırma sırasında yapılan değişiklik (kayıt için)

- **V2'nin ilk hâli Brent'i TL cinsinden (log düzey) kullanıyordu ve çalışmadı:** 2022 civarında posterior çekilişlerinin ~%99'u patlayan kök verdi, motor durdu (sonuç üretmedi, günlüğe yazılmadı). Teşhis: TL fiyatlar hızlanan trend taşıyor; Brent TL eklenince posterior ortalama kökü 1,03'e çıkıyor.
- **Düzeltme (sonuç görülmeden):** Brent dolar cinsinden (log düzey) girer. USD/TRY zaten VAR'da olduğundan log-doğrusal VAR'da bilgi aynıdır.
- V3 de aynı düzeltmeyle koşuldu (ilk hâli yarıda durduruldu, sonuç üretmedi).

## Sonuçlar (2026-11-07; aylık enflasyon, h = 1, 64 ay, 2019-12 → 2025-03)

| Model | RMSE oranı (AR'ye göre) | DM p | Yön | %68 / %90 kapsama | En iyi 5 ay hariç oran |
|---|---|---|---|---|---|
| H-004 (resmi deneme 8) | 0,807 | 0,067 | %77 | %61 / %81 | 1,07 |
| V1: + stokastik oynaklık | 0,819 | 0,051 | %72 | %66 / %86 | 1,00 |
| V2: + İTO + Brent, sabit varyans | çalışmadı (çekilişlerin ~%99'u patlayan) | | | | |
| V3: + İTO + Brent + SV | 0,647 | 0,018 | %75 | %75 / %91 | 0,76 |
| V4: V3 + akaryakıt | **0,527** | 0,013 | %81 | %81 / %97 | 0,59 |

Döneme göre V4: sakin 0,78; kur şoku 0,55; 2023 0,44; dezenflasyon 0,57. Bütün dönemlerde AR'den iyi.

12 ay ufkunda (yoy) iyileşme yok: V1 0,67 ve V3 0,60, ama ikisinde de yıllık enflasyon sistematik olarak eksik tahmin ediliyor (ortalama 14-17 puan) ve %90 bant ~%77 kapsıyor.

### Şüpheci kontrolü: kazanç BVAR'dan mı, veriden mi?

Aynı 64 ayda basit köprü regresyonu (TÜFE_t'yi o ay bilinen göstergelere OLS, genişleyen pencere, gerçek zamanlı):

| Köprü regresyonu | RMSE oranı |
|---|---|
| yalnız İTO | 0,625 |
| İTO + akaryakıt | 0,580 |
| İTO + akaryakıt + kur + TÜFE_{t−1} | **0,495** |

- **Nokta tahminde kazancın kaynağı ay içi veri, BVAR değil.** En basit köprü regresyonu V4 kadar iyi ya da daha iyi; şok aylarını da daha iyi yakalıyor (2021-12: köprü 8,6, V4 6,7, gerçek 13,0).
- BVAR'ın katkısı olasılık bantlarında: stokastik oynaklık bantları kalibre etti (V4'te artık hafifçe fazla geniş: %68 bant %81 kapsıyor).
- Köprü regresyonunda 5 tanım denendi; en iyisini seçmek de iyimserdir.

### Bu tablo ne değildir

- **Bulgu değildir.** Aynı örneklem dışı dönemde, H-004'ün nerede başarısız olduğunu gördükten sonra tasarlandı. Bonferroni'ye göre (toplam ≥ 10 deneme) hiçbir DM p değeri anlamlı değil.
- Tahmin anı değişti: V2'den itibaren TÜİK'ten 1-2 gün önce (İTO açıklandıktan sonra). AR referansı bu bilgiyi kullanmıyor, kıyas çıtası düşük.
- Temiz sınav yalnızca kasa dönemiyle (2025-04 → 2026-10, ~19 ay) yapılabilir. Bunun için model önce dondurulmalı, sonra kasayı insan açmalı.

### Denenenlerin sayımı

Tamamlanan 5 koşu (V1 h1, V1 h12, V3 h1, V3 h12, V4 h1), sonuç üretmeyen 2 V2 denemesi ve 1 yarıda durdurulan V3 denemesi. Ayrıca 5 köprü regresyonu tanımı.

## Tahmin anı notu

V2'den itibaren İTO ve Brent "ay sonunda bilinir" (yayın gecikmesi 0) sayılır. İTO ay verisini izleyen ayın 1'inde açıklar; yani bu varyantların tahmin anı fiilen **TÜİK açıklamasından 1-2 gün önce**dir. H-004'te tahmin anı ay sonuydu.

## Bilinen sınırlar

- İTO'nun mevsim faktörleri yalnızca 2011-01..2019-11 verisinden hesaplanır (`src/veri/tcmb_ayici_seriler.py`), örneklem dışına bilgi sızmaz. TÜFE hedefi ise TÜİK'in revize mevsimsellikten arındırılmış serisidir (H-004'teki risk aynen geçerli).
- SV ayarları (φ, s² prior'ı) bir kez seçildi, gerçek veride ayarlanmadı. Kod, modelin kendi sürecinden üretilmiş yapay veride doğrulandı (oynaklık izleme korelasyonu 0,71; %90 bant kapsaması %90).
- λ, sabit varyanslı modelin marjinal olabilirliğiyle seçilir; SV zinciri o λ ile koşar.

## Dosyalar

- `kosu.py`: koşucu. `tanimlar/`: varyant tanımları. `sonuclar/`: ay ay tablolar. `varyant_gunlugu.csv`: özet.
- SV kodu: `src/analiz/bvar.py` (`sv_cekilisleri`). Tanımda `"sv"` alanı yoksa motor eskisi gibi çalışır.
