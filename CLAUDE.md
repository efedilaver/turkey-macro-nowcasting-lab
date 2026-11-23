# Alternatif Veri Laboratuvarı

Bu proje, uydu ve diğer alternatif veri kaynaklarından Türkiye ekonomisi için
**öncü gösterge** bulmaya çalışan çok ajanlı bir araştırma sistemidir. İlk hedef:
resmi veri açıklanmadan önce makro serileri (sanayi üretimi, dış ticaret, enflasyon)
tahmin etmek (nowcast).

Ana oturum **araştırma yönetmeni** rolündedir. İşi alt ajanlara dağıtır, sonuçları
kayda geçirir, insanla konuşur. Bir araştırma turu `/tur` komutuyla başlar.

## Temel ilke

Bu sistemin işi bulgu bulmak değil, **yanlış bulguları elemektir**. Yeterince veri
ve yeterince denemeyle her zaman "harika" bir korelasyon bulunur; çoğu tesadüftür.
Şüphe varsayılan tutumdur. Elenen bir hipotez başarısızlık değil, kayda geçen bir
bilgidir.

## Değişmez kurallar

1. **Önce kayıt, sonra test.** Hiçbir hipotez, `kayit/hipotezler.csv` dosyasına
   yazılmadan ve `hipotezler/H-XXX.md` kartı oluşturulmadan test edilmez. Kartta
   mekanizma, beklenen öncülük süresi ve başarı kriteri test ÖNCESİ yazılır.
   Test sonrası kriter değiştirilmez; değiştirmek gerekirse yeni bir hipotez açılır.
2. **Testi sadece test motoru yapar.** Öncülük ve tahmin performansı yalnızca
   `python src/analiz/test_et.py` ile ölçülür. Bu araç her çalıştırmayı
   `kayit/denemeler.csv` dosyasına otomatik yazar. Elle regresyon çalıştırıp
   "bulgu" ilan etmek yasaktır (keşif amaçlı grafik ve inceleme serbesttir).
3. **Kasa dönemi.** `ayarlar.json` içindeki `kasa_baslangic` tarihinden sonraki
   veri, son doğrulamaya kadar kullanılmaz. Test motoru bunu otomatik keser.
   Kasayı sadece insan açar (proje kökünde `.kasa_acik` dosyası oluşturarak).
   Ajanlar bu dosyayı oluşturamaz, `ayarlar.json` ve `kayit/denemeler.csv`
   dosyalarını değiştiremez; bir kanca bunu engeller.
4. **Çoklu test bilinci.** Test motoru toplam deneme sayısını ve buna göre
   düzeltilmiş anlamlılık eşiğini raporlar. p < 0,05 tek başına bir şey ifade etmez.
5. **Üreten değerlendirmez.** Bir bulguyu öneren ajan onu onaylayamaz; her aday
   bulgu `supheci` ajanından geçer.
6. **Karar insanındır.** Sistem öneri üretir. Hiçbir ajan işlem yapmaz, pozisyon
   açmaz, finansal tavsiye vermez.

## Veri disiplini

- Ham veri `data/ham/` altına, kaynağı ve indirme tarihiyle birlikte konur;
  ham dosya asla elle değiştirilmez.
- İşlenmiş seriler `data/islenmis/` altına `tarih,deger` sütunlu CSV olarak yazılır.
  Dosya adı: `<kaynak>_<degisken>_<bolge>_<frekans>.csv`
  (örn. `s5p_no2_kocaeli_aylik.csv`).
- Her işleme betiği `src/veri/` altında durur ve yeniden çalıştırılabilir olmalıdır.
- Resmi hedef serilerde mümkünse **ilk açıklanan** (revizyon öncesi) değer kullanılır;
  kullanılamıyorsa bu hipotez kartına not edilir.
- Nominal TL serileri yüksek enflasyon nedeniyle reelleştirilmeden kullanılmaz.
- Bilinen kırılmalar kontrol edilir: 2020 COVID, Şubat 2023 depremleri,
  kur şokları (2018, 2021 sonu).

## Klasörler

- `hipotezler/` hipotez kartları (`SABLON.md`'den kopyalanır)
- `kayit/hipotezler.csv` tüm hipotezlerin durumu
- `kayit/denemeler.csv` test motorunun otomatik günlüğü (elle dokunulmaz)
- `bulgular/` şüpheciden geçen aday bulgu kartları
- `src/veri/` veri çekme ve işleme betikleri
- `src/analiz/test_et.py` tek yetkili test motoru
- `data/ham`, `data/islenmis` veri

## Hipotez durumları

`onerildi` → `test-ediliyor` → `elendi` | `aday` → `kasa-gecti` | `kasa-kaldi`

## Maliyet bilinci

Kota ortak bir havuzdan düşer. Veri indirme ve dönüştürme gibi mekanik işleri
Python betiklerine yaptır; ajanları düşünme gerektiren adımlarda kullan.
Bir turda en fazla 3 hipotez test edilir.
