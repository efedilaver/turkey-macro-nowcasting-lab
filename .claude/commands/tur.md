---
description: Bir araştırma turu çalıştır (hipotez → veri → test → şüpheci → kayıt)
argument-hint: [odak konusu, örn. "sanayi üretimi"]
---

Araştırma yönetmeni olarak bir tur çalıştır. Odak: $ARGUMENTS
(Odak verilmemişse `kayit/hipotezler.csv` dosyasına bakıp en az denenmiş hedefi seç.)

Adımlar:

1. **Durumu oku.** `kayit/hipotezler.csv`, `kayit/denemeler.csv` ve varsa
   `bulgular/` altındaki son notları oku. Bekleyen (`onerildi` veya `EK-IS`)
   hipotez varsa yeni üretmek yerine önce onları ele al.
2. **Hipotez.** Gerekirse `hipotez` ajanından odak konusu için en fazla 3
   hipotez iste. Kartları okuyup mekanizması zayıf olanı kendin `elendi`
   olarak işaretleyebilirsin (gerekçesiyle).
3. **Veri.** Her hipotez için `veri` ajanını çalıştır. Birbirinden bağımsız
   hipotezlerin veri işlerini paralel başlatabilirsin. Erişilemeyen veri varsa
   o hipotezi beklemeye al ve insana neyin gerektiğini not et.
4. **Test.** Verisi hazır olan her hipotez için `analist` ajanını çalıştır.
   Durumu `test-ediliyor` yap.
5. **Şüpheci.** Başarı kriterini karşılayan her hipotez için `supheci` ajanını
   çalıştır. Kriteri karşılamayanları `elendi` yap.
6. **Kayıt.** `kayit/hipotezler.csv` durumlarını güncelle. `ADAY` hükmü alanlar
   için `bulgular/` altına kısa bir özet kartı yaz.
7. **Rapor.** Bana şu formatta kısa bir özet ver:
   - Bu turda test edilen hipotezler ve sonuçları (tek satır her biri)
   - Toplam deneme sayısı (`kayit/denemeler.csv`)
   - Aday bulgular ve kasa doğrulaması için benden onay gerekenler
   - İnsanın yapması gerekenler (API anahtarı, erişim, karar)
   - Bir sonraki tur için öneri

Kasa doğrulamasını asla kendin başlatma; sadece önerebilirsin.
