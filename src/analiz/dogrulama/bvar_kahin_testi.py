"""Kâhin testi (H-004 motor doğrulaması): gerçek (B, Σ) ile motorun simülasyon yolu kalibre mi? (yalnız yapay veri)

DGP doğrudan VAR uzayında (sue, usd: 100·log düzey; tufe: 100·Δlog; aofm: düzey) tanımlı bir VAR(2).
Gerçek parametrelerle simüle edilen tahmin dağılımı, gerçekleşeni nominal oranda kapsamalı.
"""
import sys
import numpy as np
import pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bvar as bv

n, p = 4, 2
A1 = np.array([[1.30, 0.00, 0.00, 0.00],     # sue düzeyi (yakın birim kök)
               [0.00, 1.20, 0.10, -0.05],    # usd düzeyi
               [0.00, 0.03, 0.85, 0.00],     # tüfe aylık enflasyonu (kalıcı)
               [0.00, 0.02, 0.15, 1.10]])    # aofm
A2 = np.array([[-0.31, 0.00, 0.00, 0.00],
               [0.00, -0.21, 0.00, 0.04],
               [0.00, -0.025, 0.05, 0.00],
               [0.00, -0.02, -0.10, -0.15]])
c = np.array([4.0, 0.5, 0.25, 0.3])
Sig = np.array([[1.0, 0.2, 0.1, 0.0], [0.2, 4.0, 0.9, 0.3], [0.1, 0.9, 0.6, 0.1], [0.0, 0.3, 0.1, 0.5]])
B = np.zeros((n * p + 1, n)); B[:n] = A1.T; B[n:2 * n] = A2.T; B[-1] = c
print("en büyük kök:", round(float(bv.eslik_matrisleri(B[None], n, p)[0].__array__().shape[0]), 0),
      round(float(np.abs(np.linalg.eigvals(bv.eslik_matrisleri(B[None], n, p)[0])).max()), 4))

T = 900
tarih = pd.date_range("1950-01-01", periods=T, freq="MS")
rng = np.random.default_rng(3)
Y = np.zeros((T + 300, n)); Y[:2] = [300, 300, 2, 10]
Lc = np.linalg.cholesky(Sig)
for t in range(2, T + 300):
    Y[t] = c + A1 @ Y[t - 1] + A2 @ Y[t - 2] + Lc @ rng.standard_normal(n)
Z = pd.DataFrame(Y[300:], index=tarih, columns=["sue", "usdtry", "tufe", "aofm"])
L = {"sue": 2, "usdtry": 0, "tufe": 1, "aofm": 0}
yoy = 100 * (np.exp(Z["tufe"].rolling(12).sum() / 100) - 1)
logdiff = Z["tufe"]

for h, don, gercek in [(1, "logdiff", logdiff), (12, "yoy", yoy)]:
    pit, ic68, ic90, hata = [], [], [], []
    for t in tarih[100::2]:
        cek, _ = bv.hedef_cekilisleri(Z, "tufe", "logdiff", don, t, h, L, p, np.ones(n), 1.0, None, 2000, 1.02,
                                      np.random.default_rng(int(t.value % 2**31)), parametre=(B, Sig))
        q = np.percentile(cek, [5, 16, 84, 95])
        y = gercek[t]
        pit.append(np.mean(cek <= y)); ic68.append(q[1] <= y <= q[2]); ic90.append(q[0] <= y <= q[3])
        hata.append(y - cek.mean())
    print(f"h={h:2d} {don:7s}: {len(pit)} nokta, kapsama %68={np.mean(ic68):.3f} %90={np.mean(ic90):.3f}, "
          f"ort. PIT {np.mean(pit):.3f}, ort. hata {np.mean(hata):+.3f} (std {np.std(hata):.2f}), "
          f"PIT ondalık {np.histogram(pit, bins=10, range=(0, 1))[0].tolist()}")
