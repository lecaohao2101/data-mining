"""Phần 2 — Clustering ngày theo mẫu phát điện (Data Mining Methods, M3).

Đầu vào:  data/processed/system_<id>_2015_hourly_clean.csv (Phase 1)
Đầu ra:   data/processed/system_<id>_2015_daily_features.csv
            (đặc trưng ngày + nhãn cụm K-Means / GMM với k đã chọn)
          outputs/clustering_report.json
          outputs/clustering_system_<id>.png

Cách làm:
- Tính đặc trưng ngày từ bản giờ đã làm sạch (Phase 1), chuẩn hoá theo
  công suất định mức (per kW) để 3 hệ so sánh được với nhau.
- Phân cụm RIÊNG từng hệ (khí hậu và quy mô khác nhau, không gộp chung).
- Đặc trưng clustering (chuẩn hoá z-score trong từng hệ):
    energy_kwh_per_kw, peak_per_kw, daytime_hours,
    poa_daytime_mean, ambient_temp_mean, variability (std/mean công suất ban ngày)
- Chạy K-Means và GMM với k = 2..6. Chọn k bằng silhouette (K-Means) và BIC (GMM);
  nếu k nhỏ hơn mà silhouette chỉ kém tối đa 0,02 thì ưu tiên k nhỏ hơn (đơn giản hơn).
- Kiểm chứng: cụm phải giải thích được bằng thời tiết thực (bức xạ, nhiệt độ,
  tháng trong năm), xem trong clustering_report.json -> cluster_profiles.

Chạy:  python scripts/clustering.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "outputs"

CAPACITY_KW = {4: 1.0, 1278: 171.36, 1403: 6.0}
FEATURES = [
    "energy_kwh_per_kw",
    "peak_per_kw",
    "daytime_hours",
    "poa_daytime_mean",
    "ambient_temp_mean",
    "variability",
]
K_RANGE = range(2, 7)


def daily_features(sid: int) -> pd.DataFrame:
    df = pd.read_csv(INPUT_DIR / f"system_{sid}_2015_hourly_clean.csv", parse_dates=["timestamp"])
    df["date"] = df["timestamp"].dt.date
    rows = []
    for dt, g in df.groupby("date"):
        day = g[g["is_daytime"]]
        mean_day_power = day["power_per_kw"].mean() if len(day) else float("nan")
        std_day_power = day["power_per_kw"].std() if len(day) else float("nan")
        rows.append(
            {
                "date": str(dt),
                "system_id": sid,
                "n_hours": int(len(g)),
                "energy_kwh_per_kw": float(g["ac_power_w"].clip(lower=0).sum() / 1000.0 / CAPACITY_KW[sid]),
                "peak_per_kw": float(g["power_per_kw"].max()),
                "daytime_hours": int(len(day)),
                "poa_daytime_mean": float(day["poa_irradiance_wm2"].mean()) if len(day) else float("nan"),
                "poa_max": float(g["poa_irradiance_wm2"].max()),
                "ambient_temp_mean": float(g["ambient_temp_c"].mean()),
                "module_temp_mean": float(g["module_temp_c"].mean()),
                "variability": float(std_day_power / mean_day_power) if mean_day_power else float("nan"),
                "outlier_hours": int(g["outlier_any"].sum()),
            }
        )
    out = pd.DataFrame(rows)
    # Ngày thiếu giờ qua đêm (System 1403) vẫn giữ lại: ban ngày còn đủ.
    return out


def silhouette_score_safe(X, labels) -> float:
    from sklearn.metrics import silhouette_score

    if len(set(labels)) < 2 or len(set(labels)) >= len(X):
        return float("nan")
    return float(silhouette_score(X, labels))


def cluster_system(sid: int) -> dict:
    daily = daily_features(sid)
    X = StandardScaler().fit_transform(daily[FEATURES].fillna(daily[FEATURES].median()).values)

    kmeans_table, gmm_table = [], []
    kmeans_labels, gmm_labels = {}, {}
    for k in K_RANGE:
        km = KMeans(n_clusters=k, n_init=20, random_state=42).fit(X)
        kmeans_labels[k] = km.labels_
        kmeans_table.append(
            {
                "k": k,
                "inertia": float(km.inertia_),
                "silhouette": silhouette_score_safe(X, km.labels_),
            }
        )
        gm = GaussianMixture(n_components=k, covariance_type="full", n_init=3, random_state=42).fit(X)
        pred = gm.predict(X)
        gmm_labels[k] = pred
        gmm_table.append(
            {
                "k": k,
                "bic": float(gm.bic(X)),
                "aic": float(gm.aic(X)),
                "silhouette": silhouette_score_safe(X, pred),
            }
        )

    # Chọn k: K-Means theo silhouette, ưu tiên k nhỏ nếu chỉ kém <= 0,02.
    best_sil = max(r["silhouette"] for r in kmeans_table)
    best_k = min(r["k"] for r in kmeans_table if r["silhouette"] >= best_sil - 0.02)
    best_gmm_k = min(gmm_table, key=lambda r: r["bic"])["k"]

    daily["kmeans_cluster"] = kmeans_labels[best_k]
    daily["gmm_cluster"] = gmm_labels[best_gmm_k]
    daily.to_csv(INPUT_DIR / f"system_{sid}_2015_daily_features.csv", index=False)

    # Mô tả từng cụm (giá trị gốc, không chuẩn hoá) + tháng chiếm đa số.
    daily["month"] = pd.to_datetime(daily["date"]).dt.month
    profiles = []
    for c in sorted(daily["kmeans_cluster"].unique()):
        sub = daily[daily["kmeans_cluster"] == c]
        profiles.append(
            {
                "cluster": int(c),
                "n_days": int(len(sub)),
                "energy_kwh_per_kw_mean": round(float(sub["energy_kwh_per_kw"].mean()), 2),
                "peak_per_kw_mean": round(float(sub["peak_per_kw"].mean()), 2),
                "daytime_hours_mean": round(float(sub["daytime_hours"].mean()), 1),
                "poa_daytime_mean": round(float(sub["poa_daytime_mean"].mean()), 1),
                "ambient_temp_mean": round(float(sub["ambient_temp_mean"].mean()), 1),
                "variability_mean": round(float(sub["variability"].mean()), 2),
                "outlier_hours_mean": round(float(sub["outlier_hours"].mean()), 1),
                "months": {str(m): int(n) for m, n in sub["month"].value_counts().sort_index().items()},
            }
        )

    report = {
        "system_id": sid,
        "n_days": int(len(daily)),
        "features": FEATURES,
        "kmeans": kmeans_table,
        "gmm": gmm_table,
        "chosen_k_kmeans": int(best_k),
        "chosen_k_gmm_by_bic": int(best_gmm_k),
        "cluster_profiles_kmeans": profiles,
    }
    plot_system(sid, daily, kmeans_table, gmm_table, best_k)
    return report


def plot_system(sid, daily, kmeans_table, gmm_table, best_k):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    ks = [r["k"] for r in kmeans_table]
    # Inertia (hàng trăm) và silhouette (0-1) khác thang đo -> dùng 2 trục y.
    ax_twin = axes[0].twinx()
    (l1,) = axes[0].plot(ks, [r["inertia"] for r in kmeans_table], "o-", label="K-Means inertia (elbow)")
    (l2,) = ax_twin.plot(ks, [r["silhouette"] for r in kmeans_table], "s-", label="K-Means silhouette")
    (l3,) = ax_twin.plot(ks, [r["silhouette"] for r in gmm_table], "^-", label="GMM silhouette")
    axes[0].axvline(best_k, color="grey", linestyle="--", label=f"chosen k={best_k}")
    axes[0].set_xlabel("k")
    axes[0].set_ylabel("Inertia")
    ax_twin.set_ylabel("Silhouette")
    axes[0].set_title(f"System {sid}: elbow + silhouette")
    axes[0].legend(handles=[l1, l2, l3], fontsize=8, loc="upper right")
    axes[0].grid(alpha=0.3)

    sc = axes[1].scatter(
        daily["poa_daytime_mean"],
        daily["energy_kwh_per_kw"],
        c=daily["kmeans_cluster"],
        cmap="tab10",
        s=18,
    )
    axes[1].set_xlabel("Bức xạ ban ngày TB (W/m²)")
    axes[1].set_ylabel("Năng lượng (kWh/kW/ngày)")
    axes[1].set_title(f"System {sid}: ngày theo cụm (K-Means, k={best_k})")
    axes[1].grid(alpha=0.3)
    fig.colorbar(sc, ax=axes[1], label="cụm")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / f"clustering_system_{sid}.png", dpi=150)
    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    reports = [cluster_system(sid) for sid in [4, 1278, 1403]]
    (OUTPUT_DIR / "clustering_report.json").write_text(
        json.dumps(reports, indent=2, ensure_ascii=False)
    )
    for r in reports:
        km = {x["k"]: round(x["silhouette"], 3) for x in r["kmeans"]}
        print(
            f"System {r['system_id']}: k K-Means={r['chosen_k_kmeans']} "
            f"(silhouette {km}), k GMM theo BIC={r['chosen_k_gmm_by_bic']}, "
            f"cụm: {[p['n_days'] for p in r['cluster_profiles_kmeans']]} ngày"
        )
    print("Report: outputs/clustering_report.json")


if __name__ == "__main__":
    main()
