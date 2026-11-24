"""README grafiğini kayit/sonuclar/ altındaki test motoru çıktılarından üretir.

Çalıştırma (repo kökünden):  python scripts/grafikler.py
Çıktı: docs/figures/rmse_oranlari.png
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt

KOK = Path(__file__).resolve().parents[1]
CIKTI = KOK / "docs" / "figures"
CIKTI.mkdir(parents=True, exist_ok=True)

MAVI, GRI, METIN, IKINCIL, IZGARA = "#2a78d6", "#a3a29c", "#0b0b0b", "#52514e", "#e6e5e0"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": IZGARA,
    "xtick.color": IKINCIL, "ytick.color": METIN, "axes.labelcolor": IKINCIL,
    "figure.facecolor": "white", "savefig.dpi": 200, "savefig.bbox": "tight",
})

# Her hipotezin ana denemesi (kayit/hipotezler.csv'deki "ana deneme"); en iyiden en kötüye
ANA = [
    ("H-007", 10, "Ay içi fiyatlar + köprü regresyonu → TÜFE", True),
    ("H-006", 11, "Ay içi fiyatlar + BVAR → TÜFE", True),
    ("H-002", 1, "Kartlı harcama → perakende satış", False),
    ("H-004", 8, "Minnesota BVAR → TÜFE", False),
    ("H-005", 7, "PPK metin tonu → TÜFE sürprizi", False),
    ("H-001", 6, "Elektrik tüketimi → sanayi üretimi", False),
]
sonuclar = {}
for f in (KOK / "kayit" / "sonuclar").glob("*.json"):
    d = json.loads(f.read_text(encoding="utf-8"))
    sonuclar[(d["hipotez"], d["toplam_deneme"])] = d["rmse_oran"]

fig, ax = plt.subplots(figsize=(9, 4.4))
for y, (h, deneme, ad, gelistirme) in enumerate(reversed(ANA)):
    oran = sonuclar[(h, deneme)]
    ax.barh(y, oran, height=0.6, color=MAVI if oran < 0.9 else GRI, zorder=2)
    degisim = (1 - oran) * 100
    metin = f"hata %{abs(degisim):.0f} " + ("azaldı" if degisim >= 0 else "arttı")
    if gelistirme:
        metin += " (geliştirme dönemi)"
    ax.text(oran + 0.02, y, metin, va="center", fontsize=9.5, color=IKINCIL,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.5), zorder=4)
ax.set_yticks(range(len(ANA)))
ax.set_yticklabels([ad for _, _, ad, _ in reversed(ANA)])
ax.axvline(1.0, color=IKINCIL, lw=1, zorder=1)
ax.text(1.0, len(ANA) - 0.35, " kıyas modeli", fontsize=9, color=IKINCIL)
ax.set_xlim(0, 1.75)
ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0, 1.25])
ax.xaxis.set_major_formatter(lambda v, _: f"{v:.2f}".rstrip("0").rstrip(".").replace(".", ","))
ax.set_xlabel("Tahmin hatası / kıyas modelinin hatası (RMSE oranı, düşük daha iyi)")
ax.tick_params(axis="y", length=0)
fig.savefig(CIKTI / "rmse_oranlari.png", facecolor="white")
print("yazıldı:", CIKTI / "rmse_oranlari.png")
