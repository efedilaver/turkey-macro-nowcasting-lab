# BVAR dersi (öğrenme klasörü)

Bu klasör bir **ders**; araştırma hattının (hipotez kartı → `test_et.py` → şüpheci) parçası değil.
Buradaki sonuçlar `kayit/` dosyalarına girmez ve bulgu olarak kullanılmaz.

| Dosya | Ne |
|---|---|
| `bvar_ders.ipynb` | Ders defteri: VAR → Bayes → Minnesota prior → sıfırdan BVAR → λ laboratuvarı → kur geçişkenliği |
| `veri_cek.py` | EVDS3'ten 4 aylık seriyi çeker (SÜE, USD/TRY, TÜFE-MA, AOFM) |
| `veri/bvar_ders_aylik.csv` | Defterin kullandığı veri, 2011-01 .. 2025-03 (depoda yok; `veri_cek.py` ile üretilir) |
| `veri/ham/` | EVDS yanıtlarının aynısı, indirme tarihiyle (depoda yok) |

**Kasa:** Veri isteği 31-03-2025'te biter; kasa dönemi (2025-04 ve sonrası) indirilmez.

Çalıştırma (proje kökünden):

```bash
python ogrenme/bvar/veri_cek.py          # veriyi tazelemek için (EVDS_API_KEY gerekir)
jupyter notebook ogrenme/bvar/bvar_ders.ipynb
```
