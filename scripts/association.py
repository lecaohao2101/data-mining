"""Phần 3 — Luật kết hợp thời tiết -> phát điện (Data Mining Methods, M1).

Đầu vào:  data/processed/system_<id>_2015_hourly_clean.csv (Phase 1)
Đầu ra:   outputs/association_rules.csv
          outputs/association_report.json

Cách làm:
- Chỉ dùng giờ ban ngày (is_daytime, bức xạ > 50 W/m²), vì ban đêm công suất
  ≈ 0 là bình thường, không phải mẫu phát điện.
- Rời rạc hoá từng biến liên tục thành Low / Medium / High theo phân vị 1/3
  và 2/3 riêng từng hệ (ngưỡng ghi trong report, vì khí hậu 3 hệ khác nhau).
  Biến dùng:
    - chung: poa_irradiance_wm2 (irr), power_per_kw (power)
    - nhiệt độ: ambient_temp_c, NGOẠI TRỪ System 1403 dùng module_temp_c
      (cảm biến môi trường của 1403 đọc cao bất thường trong mùa nóng)
    - System 1278 thêm: relative_humidity_pct (humidity), wind_speed_ms (wind)
- Chạy cả Apriori và FP-Growth với min_support = 0,05, max_len = 3, kiểm tra
  2 thuật toán cho cùng số frequent itemset (lý thuyết: phải giống nhau).
- Luật: metric lift >= 1, confidence >= 0,5, sắp xếp theo lift giảm dần.
  Chỉ giữ luật có Lift > 1 (antecedent làm tăng khả năng xảy ra của consequent
  so với ngẫu nhiên) và Support đủ lớn (>= 0,05, tức >= ~190 giờ ban ngày).

Chạy:  python scripts/association.py
"""

import json
from pathlib import Path

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules, fpgrowth

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "outputs"

MIN_SUPPORT = 0.05
MIN_CONFIDENCE = 0.5
LABELS = ["Low", "Medium", "High"]

# Biến dùng cho từng hệ: (tên cột, tên ngắn trong item)
VARIABLES = {
    4: [("poa_irradiance_wm2", "irr"), ("ambient_temp_c", "temp"), ("power_per_kw", "power")],
    1278: [
        ("poa_irradiance_wm2", "irr"),
        ("ambient_temp_c", "temp"),
        ("relative_humidity_pct", "humidity"),
        ("wind_speed_ms", "wind"),
        ("power_per_kw", "power"),
    ],
    1403: [("poa_irradiance_wm2", "irr"), ("module_temp_c", "temp"), ("power_per_kw", "power")],
}


def discretize(df: pd.DataFrame, variables) -> tuple[pd.DataFrame, dict]:
    """Rời rạc hoá theo tertile, trả về DataFrame one-hot + ngưỡng đã dùng."""
    items = pd.DataFrame(index=df.index)
    edges: dict = {}
    for col, short in variables:
        s = pd.to_numeric(df[col], errors="coerce")
        q1, q2 = s.quantile(1 / 3), s.quantile(2 / 3)
        edges[short] = {"column": col, "low_max": round(float(q1), 2), "medium_max": round(float(q2), 2)}
        cat = pd.cut(s, bins=[-float("inf"), q1, q2, float("inf")], labels=LABELS)
        for label in LABELS:
            items[f"{short}={label}"] = (cat == label).astype(bool)
    return items, edges


def mine_system(sid: int) -> dict:
    df = pd.read_csv(INPUT_DIR / f"system_{sid}_2015_hourly_clean.csv", parse_dates=["timestamp"])
    day = df[df["is_daytime"]].copy()
    variables = VARIABLES[sid]
    # Bỏ giờ thiếu biến dùng (vd System 1278 thiếu nhiệt độ môi trường 719 giờ).
    cols = [c for c, _ in variables]
    before = len(day)
    day = day.dropna(subset=cols)
    dropped = before - len(day)

    onehot, edges = discretize(day, variables)

    freq_ap = apriori(onehot, min_support=MIN_SUPPORT, max_len=3, use_colnames=True)
    freq_fp = fpgrowth(onehot, min_support=MIN_SUPPORT, max_len=3, use_colnames=True)
    # Hai thuật toán phải cho cùng tập frequent itemset (so sánh theo itemset).
    ap_sets = {frozenset(x) for x in freq_ap["itemsets"]}
    fp_sets = {frozenset(x) for x in freq_fp["itemsets"]}
    assert ap_sets == fp_sets, f"Apriori vs FP-Growth khác nhau ở system {sid}"

    rules = association_rules(freq_ap, metric="lift", min_threshold=1.0)
    rules = rules[(rules["confidence"] >= MIN_CONFIDENCE) & (rules["support"] >= MIN_SUPPORT)]
    rules = rules.sort_values(["lift", "confidence"], ascending=False).reset_index(drop=True)
    rules["system_id"] = sid
    rules["antecedents"] = rules["antecedents"].apply(lambda x: ", ".join(sorted(x)))
    rules["consequents"] = rules["consequents"].apply(lambda x: ", ".join(sorted(x)))

    # Luật đáng quan tâm nhất: consequent là power (công suất).
    power_rules = rules[rules["consequents"].str.contains("power=")]
    top = []
    for _, r in power_rules.head(15).iterrows():
        top.append(
            {
                "antecedents": r["antecedents"],
                "consequents": r["consequents"],
                "support": round(float(r["support"]), 3),
                "confidence": round(float(r["confidence"]), 3),
                "lift": round(float(r["lift"]), 2),
            }
        )

    return {
        "system_id": sid,
        "variables": {short: edges[short] for _, short in variables},
        "daytime_hours": int(before),
        "transactions_used": int(len(day)),
        "transactions_dropped_missing": int(dropped),
        "n_frequent_itemsets_apriori": int(len(freq_ap)),
        "n_frequent_itemsets_fpgrowth": int(len(freq_fp)),
        "apriori_equals_fpgrowth": bool(ap_sets == fp_sets),
        "n_rules_lift_gt_1_conf_ge_0_5": int(len(rules)),
        "top_power_rules": top,
    }, rules


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    all_rules, reports = [], []
    for sid in [4, 1278, 1403]:
        report, rules = mine_system(sid)
        reports.append(report)
        all_rules.append(rules)
        print(
            f"System {sid}: {report['transactions_used']} giờ ban ngày dùng được, "
            f"{report['n_frequent_itemsets_apriori']} frequent itemsets, "
            f"{report['n_rules_lift_gt_1_conf_ge_0_5']} luật (lift>1, conf>=0.5), "
            f"luật power mạnh nhất lift={report['top_power_rules'][0]['lift'] if report['top_power_rules'] else None}"
        )
    pd.concat(all_rules, ignore_index=True).to_csv(OUTPUT_DIR / "association_rules.csv", index=False)
    (OUTPUT_DIR / "association_report.json").write_text(
        json.dumps(reports, indent=2, ensure_ascii=False)
    )
    print("Report: outputs/association_report.json, outputs/association_rules.csv")


if __name__ == "__main__":
    main()
