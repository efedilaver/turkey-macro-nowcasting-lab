# data/

Bu klasör depoda **boştur**. Ham ve işlenmiş veri lisans koşulları ve boyut nedeniyle yayımlanmaz
(TCMB EVDS, TÜİK/OECD, EPİAŞ, TPPD, Petrol Ofisi, Sentinel-5P).

Yerelde betikler şu düzeni kurar:

| Klasör | İçerik |
|---|---|
| `data/ham/` | Kaynaktan indirilen dosyaların aynısı, kaynak ve indirme tarihiyle. Elle değiştirilmez. |
| `data/ara/` | Ara ürünler (ör. H-005 için PPK cümle tablosu ve etiketler). |
| `data/islenmis/` | `tarih,deger` sütunlu aylık seriler: `<kaynak>_<degisken>_<bolge>_<frekans>.csv` |

Hangi betiğin hangi seriyi ürettiği ana README'nin "Yeniden üretme" bölümünde.

Not: Veri sağlayıcılar geçmiş değerleri revize eder. Bugün yeniden indirilen seriler,
`kayit/` altındaki denemelerde kullanılan baskıyla birebir aynı olmayabilir.
`hipotezler/H-006_H-007.sha256` içindeki veri dosyası parmak izleri bu yüzden
yeniden indirilen dosyalarla büyük olasılıkla tutmaz.
