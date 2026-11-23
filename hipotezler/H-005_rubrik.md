# H-005 etiketleme rubriği (sürüm v1, 2026-11-07)

Bu dosya test öncesi sabitlenmiştir. Test sonrası değiştirilmez; değişiklik gerekirse yeni bir hipotez açılır.

## Görev

Sana TCMB Para Politikası Kurulu toplantı özetlerinden alınmış cümleler veriliyor. Her cümleye üç etiket ver: **tur**, **konu** ve **yon**.

Cümlelerde bazı yerler bilerek maskelenmiştir:
- `<AY>`: ay adı
- `<YIL>`: yıl
- `<SAYI>`: sayı

Maskelerin arkasındaki tarihi veya sayıyı tahmin etmeye çalışma. Cümlenin hangi döneme ait olduğunu bildiğini düşünsen bile bu bilgiyi kullanma. Ekonomide sonradan ne olduğunu da kullanma.

**Yalnızca cümlede açıkça yazanı oku.** Yorum yapma, ima arama.

## 1. tur (cümlenin türü)

- **`tekrar`:** Tamamlanmış bir döneme ait, zaten yayımlanmış bir veriyi ya da gelişmeyi gerçekleşmiş olarak anlatır. Bu veri resmi istatistik, anket ya da piyasa fiyatı olabilir. Tipik ifadeler: "gerçekleşmiştir", "artmıştır", "gerilemiştir", "kaydetmiştir", "seyretmiştir". Yayımlanmış anket sonuçlarını aktaran cümleler de buraya girer, örneğin "enflasyon beklentilerinde iyileşme sürmektedir".
- **`oncu`:** Kurulun, henüz bitmemiş içinde bulunulan dönem ya da gelecek hakkındaki kendi değerlendirmesidir. Yayımlanmış resmi rakamların ötesine geçer. Tipik ifadeler:
  - "öncü veriler / öncü göstergeler … işaret etmektedir"
  - "ana eğilimin … olduğu değerlendirilmektedir"
  - "beklenmektedir", "öngörülmektedir"
  - risk dengesi cümleleri, örneğin "enflasyona ilişkin riskler yukarı yönlüdür"
- **`yonlendirme`:** Kurulun para politikası duruşu, kararı ya da gelecekte atacağı adımlar hakkındadır. Örnekler: "sıkı duruş korunacaktır", "politika faizi … belirlenmiştir", "gerekirse araçlar kullanılacaktır".
- **`diger`:** Yukarıdakilerin hiçbiri.

Bir cümle hem gerçekleşmiş veriyi aktarıp hem de öncü bir değerlendirme yapıyorsa `oncu` seç.

## 2. konu

- **`enflasyon`:** Fiyatlar, enflasyon, ana eğilim, enflasyon beklentileri, maliyetler, fiyatlama davranışı.
- **`aktivite`:** Talep, üretim, istihdam, büyüme.
- **`dis`:** Dış ticaret, cari denge, küresel gelişmeler.
- **`finansal`:** Kredi, kur, faiz, finansal koşullar, rezervler.
- **`diger`:** Yukarıdakilerin hiçbiri.

Birden fazla konu varsa cümlenin asıl öznesini seç.

## 3. yon (yalnızca konu = enflasyon için; diğer konularda her zaman 0)

- **`+1`:** Cümle enflasyonun, fiyat baskılarının, ana eğilimin ya da enflasyon risklerinin yükseldiğini, hızlandığını, bozulduğunu veya yukarı yönlü olduğunu söylüyor.
- **`-1`:** Cümle enflasyonun, fiyat baskılarının ya da ana eğilimin gerilediğini, yavaşladığını, iyileştiğini söylüyor; dezenflasyonun sürdüğünü ya da güçlendiğini veya risklerin aşağı yönlü olduğunu belirtiyor.
- **`0`:** Değişim yok, yön karışık, yön belirsiz ya da cümle yön içermiyor. Kendi politika duruşunu anlatan cümleler genellikle 0 olur, örneğin "enflasyonda kalıcı düşüş sağlanana kadar sıkı duruş korunacaktır".

## Örnekler (uydurma cümleler)

| Cümle | tur | konu | yon |
|---|---|---|---|
| Tüketici fiyatları `<AY>` ayında yüzde `<SAYI>` artmıştır. | tekrar | enflasyon | +1 |
| Öncü veriler `<AY>` ayında ana eğilimin gerilediğine işaret etmektedir. | oncu | enflasyon | -1 |
| Enflasyona ilişkin riskler yukarı yönlü olmaya devam etmektedir. | oncu | enflasyon | +1 |
| Sıkı para politikası duruşu korunacaktır. | yonlendirme | diger | 0 |
| Öncü göstergeler iç talepte ılımlı bir seyre işaret etmektedir. | oncu | aktivite | 0 |
| Kredi büyümesi `<AY>` ayında yavaşlamıştır. | tekrar | finansal | 0 |

## Çıktı biçimi

Partideki **her** cümle için tek bir kayıt yaz. Hiçbir `cid` atlanmamalı ve hiçbiri tekrarlanmamalı. Dosya JSON olmalı:

```json
{"parti": "A_01", "rubrik": "v1", "etiketler": [{"cid": "c1a2b3", "tur": "oncu", "konu": "enflasyon", "yon": -1}]}
```

İzin verilen değerler:
- `tur`: tekrar, oncu, yonlendirme, diger
- `konu`: enflasyon, aktivite, dis, finansal, diger
- `yon`: -1, 0, 1
