"""Phần 4 — Anomaly detection (Data Mining Methods, M4).

Đầu vào:  data/processed/system_<id>_2015_hourly_clean.csv (Phase 1)
Đầu ra:   outputs/anomaly_report.json
          outputs/anomaly_system_<id>.csv (giờ bị gắn cờ bởi Isolation Forest)
          outputs/anomaly_system_<id>.png (biểu đồ, tạo local)

Cách làm:
- Chỉ dùng giờ ban ngày (is_daytime), vì ban đêm công suất ≈ 0 là bình thường.
- Đặc trưng (chuẩn hoá z-score trong từng hệ): power_per_kw,
  poa_irradiance_wm2, module_temp_c, irr_ratio (công suất/kW trên mỗi W/m²).
  Không dùng ambient_temp_c: cảm biến môi trường của System 1403 đọc cao
  bất thường, và của System 1278 thiếu 719 giờ.
- Hai mô hình, cùng tỉ lệ anomaly kỳ vọng 5% (contamination/nu = 0,05):
  Isolation Forest (n_estimators=200) và One-Class SVM (RBF, nu=0,05).
  So sánh mức đồng thuận giữa 2 mô hình.
- KHÔNG báo % accuracy: không có nhãn ground-truth. Đánh giá bằng:
  (1) các ca sự cố đã biết có bị phát hiện không (xem case_studies),
  (2) ca phát hiện có giải thích vật lý không,
  (3) tỉ lệ cảnh báo có hợp lý không (kỳ vọng ~5%, không phải 30–40%).

Case study bắt buộc:
- System 1403, 15/06/2015: inverter 1 đọc 0 cả ngày, inverter 2 bình thường.
- System 1278, 03/07/2015: file thô chỉ có 68/96 dòng 15 phút, thiếu nhiều.
- System 4: các giờ bức xạ > 800 W/m² nhưng công suất < 10% định mức (Phase 1).

Chạy:  python scripts/anomaly.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "outputs"

FEATURES = ["power_per_kw", "poa_irradiance_wm2", "module_temp_c", "irr_ratio"]
CONTAMINATION = 0.05

CASE_STUDIES = {
    1403: {"date": "2015-06-15", "label": "inverter 1 = 0 cả ngày, inverter 2 bình thường"},
    1278: {"date": "2015-07-03", "label": "file thô chỉ 68/96 dòng 15 phút, thiếu nhiều"},
    4: {"date": None, "label": "giờ bức xạ > 800 W/m² nhưng công suất < 10% định mức (Phase 1)"},
}


def detect_system(sid: int) -> dict:
    df = pd.read_csv(INPUT_DIR / f"system_{sid}_2015_hourly_clean.csv", parse_dates=["timestamp"])
    day = df[df["is_daytime"]].copy()
    before = len(day)
    day = day.dropna(subset=FEATURES)
    X = StandardScaler().fit_transform(day[FEATURES].values)

    iso = IsolationForest(n_estimators=200, contamination=CONTAMINATION, random_state=42)
    day["if_anomaly"] = iso.fit_predict(X) == -1
    day["if_score"] = iso.decision_function(X)  # càng âm càng bất thường

    ocsvm = OneClassSVM(kernel="rbf", nu=CONTAMINATION, gamma="scale")
    day["ocsvm_anomaly"] = ocsvm.fit_predict(X) == -1

    day["both_anomaly"] = day["if_anomaly"] & day["ocsvm_anomaly"]
    day["any_anomaly"] = day["if_anomaly"] | day["ocsvm_anomaly"]

    # Lưu danh sách giờ Isolation Forest gắn cờ, xếp theo độ bất thường.
    flagged = day[day["if_anomaly"]].sort_values("if_score")
    flagged_out = flagged[
        ["timestamp", "ac_power_w", "power_per_kw", "poa_irradiance_wm2",
         "ambient_temp_c", "module_temp_c", "irr_ratio", "if_score",
         "ocsvm_anomaly", "outlier_iqr", "outlier_low_power_high_irr"]
    ]
    flagged_out.to_csv(OUTPUT_DIR / f"anomaly_system_{sid}.csv", index=False)

    # Case study.
    case = CASE_STUDIES[sid]
    case_result: dict = {"label": case["label"]}
    if case["date"]:
        sub = day[day["timestamp"].dt.strftime("%Y-%m-%d") == case["date"]]
        case_result.update(
            {
                "date": case["date"],
                "daytime_hours_in_analysis": int(len(sub)),
                "if_flagged": int(sub["if_anomaly"].sum()),
                "ocsvm_flagged": int(sub["ocsvm_anomaly"].sum()),
                "both_flagged": int(sub["both_anomaly"].sum()),
            }
        )
    else:
        sub = day[day["outlier_low_power_high_irr"]]
        case_result.update(
            {
                "n_low_power_high_irr_hours": int(len(sub)),
                "if_flagged_of_those": int(sub["if_anomaly"].sum()),
                "ocsvm_flagged_of_those": int(sub["ocsvm_anomaly"].sum()),
                "both_flagged_of_those": int(sub["both_anomaly"].sum()),
            }
        )

    # 10 giờ bất thường nhất theo Isolation Forest.
    top = []
    for _, r in flagged.head(10).iterrows():
        top.append(
            {
                "timestamp": str(r["timestamp"]),
                "ac_power_w": round(float(r["ac_power_w"]), 1),
                "power_per_kw": round(float(r["power_per_kw"]), 1),
                "poa_irradiance_wm2": round(float(r["poa_irradiance_wm2"]), 1),
                "module_temp_c": round(float(r["module_temp_c"]), 1),
                "irr_ratio": round(float(r["irr_ratio"]), 3),
                "if_score": round(float(r["if_score"]), 3),
                "ocsvm_also_flags": bool(r["ocsvm_anomaly"]),
            }
        )

    report = {
        "system_id": sid,
        "features": FEATURES,
        "contamination_nu": CONTAMINATION,
        "daytime_hours": int(before),
        "hours_used": int(len(day)),
        "hours_dropped_missing": int(before - len(day)),
        "if_anomalies": int(day["if_anomaly"].sum()),
        "if_rate_pct": round(100 * float(day["if_anomaly"].mean()), 2),
        "ocsvm_anomalies": int(day["ocsvm_anomaly"].sum()),
        "ocsvm_rate_pct": round(100 * float(day["ocsvm_anomaly"].mean()), 2),
        "both_anomalies": int(day["both_anomaly"].sum()),
        "agreement_if_ocsvm_pct": round(
            100 * float((day["if_anomaly"] == day["ocsvm_anomaly"]).mean()), 1
        ),
        "phase1_iqr_overlap_if_pct": round(
            100 * float(day.loc[day["outlier_iqr"], "if_anomaly"].mean())
            if day["outlier_iqr"].sum()
            else 0.0,
            1,
        ),
        "case_study": case_result,
        "top_if_anomalies": top,
    }
    plot_system(sid, day)
    return report


def plot_system(sid: int, day: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    normal = day[~day["if_anomaly"]]
    anom = day[day["if_anomaly"]]
    ax.scatter(normal["poa_irradiance_wm2"], normal["power_per_kw"], s=10, alpha=0.4, label="bình thường")
    ax.scatter(anom["poa_irradiance_wm2"], anom["power_per_kw"], s=25, color="red", label="Isolation Forest gắn cờ")
    ax.set_xlabel("Bức xạ POA (W/m²)")
    ax.set_ylabel("Công suất (W/kW)")
    ax.set_title(f"System {sid}: anomaly ban ngày (Isolation Forest, 5%)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / f"anomaly_system_{sid}.png", dpi=150)
    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    reports = [detect_system(sid) for sid in [4, 1278, 1403]]
    (OUTPUT_DIR / "anomaly_report.json").write_text(
        json.dumps(reports, indent=2, ensure_ascii=False)
    )
    for r in reports:
        print(
            f"System {r['system_id']}: IF {r['if_anomalies']} giờ ({r['if_rate_pct']}%), "
            f"OC-SVM {r['ocsvm_anomalies']} giờ ({r['ocsvm_rate_pct']}%), "
            f"cả 2 cùng gắn cờ {r['both_anomalies']} giờ, "
            f"đồng thuận {r['agreement_if_ocsvm_pct']}%, "
            f"case study: {r['case_study']}"
        )
    print("Report: outputs/anomaly_report.json")


if __name__ == "__main__":
    main()
