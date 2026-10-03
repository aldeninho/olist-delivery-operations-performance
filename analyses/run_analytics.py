"""Seller latency, route/distance proxy, trends, and financial impact analyses."""
import csv, json, math
from collections import defaultdict
from datetime import datetime

DATA = "data/processed"
SRC = "data/source_olist"

def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

fact = read_csv(f"{DATA}/fact_orders.csv")
sel = read_csv(f"{DATA}/seller_delivery_fact.csv")

# index fact by order_id for customer-state join
fact_by_order = {r["order_id"]: r for r in fact}

BASE_LATE = sum(1 for r in sel if r["order_status"] == "delivered" and r["sla_breach"] == "Yes") / max(
    1, sum(1 for r in sel if r["order_status"] == "delivered"))

# ---------- Seller analysis ----------
S = defaultdict(lambda: {"state": None, "categories": set(), "delivered": 0, "orders": set(), "late": 0, "late_value": 0.0, "late_freight": 0.0, "days_total": 0.0, "days_n": 0})
for r in sel:
    if r["order_status"] != "delivered":
        continue
    s = S[r["seller_id"]]
    s["state"] = r["seller_state"]
    s["categories"].add(r["category"])
    s["delivered"] += 1
    s["orders"].add(r["order_id"])
    if r["sla_breach"] == "Yes":
        s["late"] += 1
        s["late_value"] += float(r["price"])
        s["late_freight"] += float(r["freight_cost_brl"])
    try:
        s["days_total"] += float(r["delivery_days"])
        s["days_n"] += 1
    except (ValueError, TypeError):
        pass

seller_rows = []
for sid, s in S.items():
    n = s["delivered"]
    if n < 30:
        continue
    late_rate = s["late"] / n
    excess = s["late"] - n * BASE_LATE
    seller_rows.append({
        "seller_id": sid, "seller_state": s["state"], "delivered_items": n, "delivered_orders": len(s["orders"]),
        "late_items": s["late"], "late_rate": round(late_rate, 4), "excess_late_items": round(excess, 1),
        "late_item_price_brl": round(s["late_value"], 2), "late_item_freight_brl": round(s["late_freight"], 2),
        "avg_delivery_days": round(s["days_total"] / s["days_n"], 2) if s["days_n"] else None,
    })

seller_rows.sort(key=lambda r: r["excess_late_items"], reverse=True)
with open(f"{DATA}/seller_late_exposure.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(seller_rows[0].keys()))
    w.writeheader()
    w.writerows(seller_rows)

# ---------- Route/distance-proxy analysis ----------
R = defaultdict(lambda: {"n": 0, "late": 0})
for r in sel:
    if r["order_status"] != "delivered":
        continue
    fo = fact_by_order.get(r["order_id"])
    if not fo:
        continue
    s_state = r["seller_state"]
    c_state = fo["customer_state"]
    same = "same state" if s_state == c_state else "different state"
    R[same]["n"] += 1
    if r["sla_breach"] == "Yes":
        R[same]["late"] += 1
    pair_key = f"{c_state} <- {s_state}"
    R[pair_key]["n"] += 1
    if r["sla_breach"] == "Yes":
        R[pair_key]["late"] += 1

route_rows = []
for key, v in R.items():
    if v["n"] < 30:
        continue
    route_rows.append({"route": key, "delivered_items": v["n"], "late_items": v["late"], "late_rate": round(v["late"] / v["n"], 4)})
route_rows.sort(key=lambda r: r["late_rate"], reverse=True)
with open(f"{DATA}/route_performance.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["route", "delivered_items", "late_items", "late_rate"])
    w.writeheader()
    w.writerows(route_rows)

same_n, same_late = R["same state"]["n"], R["same state"]["late"]
diff_n, diff_late = R["different state"]["n"], R["different state"]["late"]

# ---------- Trend ----------
monthly = read_csv(f"{DATA}/monthly_performance.csv")
monthly_late = [
    {
        "purchase_month": m["purchase_month"],
        "total_orders": int(float(m["total_orders"])),
        "sla_breach_pct": round(float(m["sla_breach_pct"] or 0), 2),
        "avg_delivery_days": round(float(m["avg_delivery_days"] or 0), 2),
        "cancellation_rate_pct": round(100 * int(float(m["cancelled_orders"] or 0)) / max(1, int(float(m["total_orders"] or 0))), 2),
        "freight_cost_per_delivered_order_brl": round(float(m["freight_cost_per_delivered_order_brl"] or 0), 2),
    }
    for m in monthly
]
with open(f"{DATA}/monthly_trend.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(monthly_late[0].keys()))
    w.writeheader()
    w.writerows(monthly_late)

# ---------- Financial impact ----------
late = [r for r in fact if r["order_status"] == "delivered" and r["sla_breach"] == "Yes"]
delivered = [r for r in fact if r["order_status"] == "delivered"]
total_order_value = sum(float(r["order_value_brl"]) for r in delivered)
total_freight = sum(float(r["freight_cost_brl"]) for r in delivered)
late_order_value = sum(float(r["order_value_brl"]) for r in late)
late_freight = sum(float(r["freight_cost_brl"]) for r in late)
avg_review_late = sum(float(r["review_score"]) for r in late if r["review_score"]) / max(1, sum(1 for r in late if r["review_score"]))
delivered_with_score = [r for r in delivered if r["review_score"]]
avg_review_ontime = sum(float(r["review_score"]) for r in delivered_with_score if r["sla_breach"] == "No") / max(1, sum(1 for r in delivered_with_score if r["sla_breach"] == "No"))
financial = {
    "delivered_orders": len(delivered),
    "late_orders": len(late),
    "late_order_value_brl": round(late_order_value, 2),
    "late_freight_cost_brl": round(late_freight, 2),
    "late_order_value_share_of_delivered": round(late_order_value / total_order_value, 4),
    "late_freight_share_of_delivered": round(late_freight / total_freight, 4),
    "avg_review_score_late": round(avg_review_late, 2),
    "avg_review_score_on_time": round(avg_review_ontime, 2),
    "review_score_gap_late_vs_on_time": round(avg_review_ontime - avg_review_late, 2),
}
with open(f"{DATA}/financial_impact.json", "w") as f:
    json.dump(financial, f, indent=2)

print("BASE_LATE", round(BASE_LATE, 4))
print("same_state:", same_late, "/", same_n, "=", round(same_late/same_n, 4))
print("different_state:", diff_late, "/", diff_n, "=", round(diff_late/diff_n, 4))
print("HIGHEST excess sellers:", len(seller_rows))
for r in seller_rows[:5]:
    print(r["seller_id"][:8], r["delivered_items"], r["late_items"], r["excess_late_items"], r["late_item_price_brl"])
print("financial:", json.dumps(financial, indent=1))
