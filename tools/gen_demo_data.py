# -*- coding: utf-8 -*-
"""
產生網頁 demo 的真實數據檔 demo_data.js。
完全比照 cnn_biomass.py 的最佳模型：
  特徵 = 側拍結構 sd_* + 累積環境 [temp, cum_sun, cum_gdd, cum_uv]
  模型 = RandomForest(n_estimators=400, random_state=0)
  驗證 = leave-one-day-out (LeaveOneGroupOut by day)，raw / log 取 R² 較佳者
每株信心區間 = 該留出樣本在 400 棵樹上的預測分布 2.5~97.5 百分位。
輸出 window.DEMO_DATA（供 file:// 直接以 <script> 載入，免 fetch/CORS）。
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.model_selection import LeaveOneGroupOut

CF = 0.47
csv_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])

df = pd.read_csv(csv_path)
sd_cols = [c for c in df.columns if c.startswith("sd_")]
env_cols = [c for c in ["temp", "cum_sun", "cum_gdd", "cum_uv"] if c in df.columns]
feats = sd_cols + env_cols

d = df.dropna(subset=feats + ["dry_weight_g"]).reset_index(drop=True)
X = d[feats].values
y = d["dry_weight_g"].values
groups = d["day"].values
rf = RandomForestRegressor(n_estimators=400, random_state=0)


def run(logy):
    yt = np.log(y) if logy else y
    pred = np.zeros_like(y, float)
    tree_lo = np.zeros_like(y, float)
    tree_hi = np.zeros_like(y, float)
    for tr, te in LeaveOneGroupOut().split(X, yt, groups):
        m = clone(rf).fit(X[tr], yt[tr])
        p = m.predict(X[te])
        pred[te] = np.exp(p) if logy else p
        per_tree = np.array([est.predict(X[te]) for est in m.estimators_])  # (400, n_te)
        if logy:
            per_tree = np.exp(per_tree)
        tree_lo[te] = np.percentile(per_tree, 2.5, axis=0)
        tree_hi[te] = np.percentile(per_tree, 97.5, axis=0)
    r2 = r2_score(y, pred)
    rmse = float(np.sqrt(mean_squared_error(y, pred)))
    return pred, tree_lo, tree_hi, r2, rmse


best = None
for logy in [False, True]:
    pred, lo, hi, r2, rmse = run(logy)
    print(f"[{'log' if logy else 'raw'}] leave-1-day-out R2={r2:+.3f} RMSE={rmse:.3f} g n={len(y)}")
    if best is None or r2 > best[-2]:
        best = (logy, pred, lo, hi, r2, rmse)

logy, pred, lo, hi, r2, rmse = best
rel = (hi - lo) / np.maximum(pred, 1e-6)
thr = float(np.percentile(rel, 75))  # 只有最不確定的約 1/4 標記送驗

samples = []
for i in range(len(d)):
    samples.append({
        "day": int(d.day[i]),
        "plant": int(d.plant[i]),
        "measured_g": round(float(y[i]), 4),
        "pred_g": round(float(pred[i]), 4),
        "ci_lo_g": round(float(max(0.0, lo[i])), 4),
        "ci_hi_g": round(float(hi[i]), 4),
        "flag_lab": bool(rel[i] > thr),
        "td_green_pct": round(float(d.td_green_frac[i] * 100), 3) if "td_green_frac" in d else None,
        "sd_green_pct": round(float(d.sd_green_frac[i] * 100), 3),
        "sd_height": round(float(d.sd_bbox_h_frac[i]), 4),
        "sd_aspect": round(float(d.sd_aspect[i]), 3),
        "sd_solidity": round(float(d.sd_solidity[i]), 3),
        "temp": round(float(d.temp[i]), 1),
        "cum_sun": round(float(d.cum_sun[i]), 1),
        "cum_gdd": round(float(d.cum_gdd[i]), 1),
        "cum_uv": round(float(d.cum_uv[i]), 1),
    })
samples.sort(key=lambda s: (s["day"], s["plant"]))

# featured：跨生長期挑代表 + 至少一個臨界(送驗)案例
flagged = [s for s in samples if s["flag_lab"]]
spread = [samples[0], samples[len(samples)//4], samples[len(samples)//2],
          samples[3*len(samples)//4], samples[-1]]
featured_keys = []
for s in spread + flagged[:2]:
    k = [s["day"], s["plant"]]
    if k not in featured_keys:
        featured_keys.append(k)

out = {
    "placeholder": False,
    "model": "RandomForest (400 trees) · side-view structure + cumulative environment",
    "validation": "leave-one-day-out cross-validation",
    "logy": bool(logy),
    "carbon_fraction": CF,
    "n_samples": len(samples),
    "n_days": int(len(set(groups))),
    "r2": round(float(r2), 3),
    "rmse_g": round(rmse, 4),
    "featured": featured_keys,
    "samples": samples,
}
out_path.parent.mkdir(parents=True, exist_ok=True)
js = "// 由 gen_demo_data2.py 從 perplant_features.csv 產生；真實 leave-one-day-out 結果。\n"
js += "window.DEMO_DATA = " + json.dumps(out, ensure_ascii=False, indent=2) + ";\n"
out_path.write_text(js, encoding="utf-8")
print(f"chosen={'log' if logy else 'raw'} R2={r2:.3f} RMSE={rmse:.3f} n={len(samples)} -> {out_path}")
