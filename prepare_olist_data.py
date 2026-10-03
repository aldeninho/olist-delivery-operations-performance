"""Build portfolio-ready operations tables from the public Olist dataset."""
from pathlib import Path
import json
import pandas as pd
import numpy as np

ROOT = Path(__file__).parent
SRC = ROOT / "data" / "source_olist"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

orders = pd.read_csv(SRC / "olist_orders_dataset.csv")
customers = pd.read_csv(SRC / "olist_customers_dataset.csv")
items = pd.read_csv(SRC / "olist_order_items_dataset.csv")
sellers = pd.read_csv(SRC / "olist_sellers_dataset.csv")
products = pd.read_csv(SRC / "olist_products_dataset.csv")
translation = pd.read_csv(SRC / "product_category_name_translation.csv")
reviews = pd.read_csv(SRC / "olist_order_reviews_dataset.csv")

for column in ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"]:
    orders[column] = pd.to_datetime(orders[column], errors="coerce")

item_enriched = (items.merge(products[["product_id", "product_category_name"]], on="product_id", how="left")
                 .merge(translation, on="product_category_name", how="left"))
item_enriched["category"] = item_enriched["product_category_name_english"].fillna("unavailable")
item_agg = (item_enriched.groupby("order_id", as_index=False)
            .agg(order_value_brl=("price", "sum"), freight_cost_brl=("freight_value", "sum"),
                 item_count=("order_item_id", "count"), seller_count=("seller_id", "nunique"),
                 category_count=("category", "nunique"), primary_category=("category", "first")))
review_agg = reviews.groupby("order_id", as_index=False).agg(review_score=("review_score", "mean"), review_count=("review_id", "nunique"))

fact = (orders.merge(customers[["customer_id", "customer_city", "customer_state"]], on="customer_id", how="left")
        .merge(item_agg, on="order_id", how="left")
        .merge(review_agg, on="order_id", how="left"))
fact["is_delivered"] = fact["order_status"].eq("delivered")
fact["is_cancelled"] = fact["order_status"].eq("canceled")
fact["delivery_days"] = (fact["order_delivered_customer_date"] - fact["order_purchase_timestamp"]).dt.total_seconds() / 86400
fact["estimated_delivery_days"] = (fact["order_estimated_delivery_date"] - fact["order_purchase_timestamp"]).dt.total_seconds() / 86400
fact["late_delivery_days"] = ((fact["order_delivered_customer_date"] - fact["order_estimated_delivery_date"]).dt.total_seconds() / 86400).clip(lower=0)
fact["sla_breach"] = np.where(fact["is_delivered"], np.where(fact["order_delivered_customer_date"] > fact["order_estimated_delivery_date"], "Yes", "No"), "Not delivered")
fact["purchase_month"] = fact["order_purchase_timestamp"].dt.to_period("M").astype(str)
fact["data_quality_flag"] = np.select(
    [fact["is_delivered"] & fact["order_delivered_customer_date"].isna(),
     fact["is_delivered"] & fact["order_estimated_delivery_date"].isna(),
     fact["is_delivered"] & (fact["order_delivered_customer_date"] < fact["order_purchase_timestamp"])],
    ["Missing delivery timestamp", "Missing estimated date", "Delivery before purchase"], default="Valid")

columns = ["order_id", "order_status", "order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date", "purchase_month", "customer_city", "customer_state", "order_value_brl", "freight_cost_brl", "item_count", "seller_count", "primary_category", "review_score", "delivery_days", "estimated_delivery_days", "late_delivery_days", "sla_breach", "data_quality_flag"]
fact[columns].to_csv(OUT / "fact_orders.csv", index=False)

delivered = fact[fact["is_delivered"]].copy()
def summary(df):
    n = len(df)
    d = df[df["is_delivered"]]
    return pd.Series({"total_orders": n, "delivered_orders": len(d), "cancelled_orders": int(df["is_cancelled"].sum()),
                      "on_time_delivery_pct": (d["sla_breach"].eq("No").mean() if len(d) else np.nan),
                      "sla_breach_pct": (d["sla_breach"].eq("Yes").mean() if len(d) else np.nan),
                      "avg_delivery_days": d["delivery_days"].mean(), "freight_cost_per_delivered_order_brl": d["freight_cost_brl"].mean(), "avg_review_score": d["review_score"].mean()})

overall = {"total_orders": int(len(fact)), "delivered_orders": int(len(delivered)), "cancelled_orders": int(fact["is_cancelled"].sum()),
           "cancellation_rate": float(fact["is_cancelled"].mean()), "on_time_delivery_rate": float(delivered["sla_breach"].eq("No").mean()),
           "sla_breach_rate": float(delivered["sla_breach"].eq("Yes").mean()), "avg_delivery_days": float(delivered["delivery_days"].mean()),
           "freight_cost_per_delivered_order_brl": float(delivered["freight_cost_brl"].mean()), "on_time_avg_review": float(delivered.loc[delivered.sla_breach.eq("No"), "review_score"].mean()), "late_avg_review": float(delivered.loc[delivered.sla_breach.eq("Yes"), "review_score"].mean())}

state_summary = fact.groupby("customer_state").apply(summary, include_groups=False).reset_index().sort_values("sla_breach_pct", ascending=False)
category_summary = fact.groupby("primary_category").apply(summary, include_groups=False).reset_index().rename(columns={"primary_category": "category"}).sort_values("sla_breach_pct", ascending=False)
monthly_summary = fact.groupby("purchase_month").apply(summary, include_groups=False).reset_index().sort_values("purchase_month")

# Seller analysis stays at seller-order grain: each seller contribution is separate when an order has multiple sellers.
seller_fact = (item_enriched[["order_id", "seller_id", "category", "price", "freight_value"]]
               .merge(orders[["order_id", "order_status", "order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]], on="order_id", how="left")
               .merge(sellers[["seller_id", "seller_state"]], on="seller_id", how="left"))
for c in ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]:
    seller_fact[c] = pd.to_datetime(seller_fact[c], errors="coerce")
seller_fact["is_delivered"] = seller_fact["order_status"].eq("delivered")
seller_fact["is_cancelled"] = seller_fact["order_status"].eq("canceled")
seller_fact["sla_breach"] = np.where(seller_fact["is_delivered"], np.where(seller_fact["order_delivered_customer_date"] > seller_fact["order_estimated_delivery_date"], "Yes", "No"), "Not delivered")
seller_fact["delivery_days"] = (seller_fact["order_delivered_customer_date"] - seller_fact["order_purchase_timestamp"]).dt.total_seconds() / 86400
seller_fact["freight_cost_brl"] = seller_fact["freight_value"]
seller_fact["review_score"] = np.nan
seller_fact[["order_id", "seller_id", "seller_state", "category", "order_status", "order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date", "price", "freight_cost_brl", "delivery_days", "sla_breach"]].to_csv(OUT / "seller_delivery_fact.csv", index=False)
seller_summary = seller_fact.groupby("seller_id").apply(summary, include_groups=False).reset_index()
seller_summary = seller_summary[seller_summary["delivered_orders"] >= 50].sort_values(["sla_breach_pct", "delivered_orders"], ascending=[False, False])

baseline_late_rate = overall["sla_breach_rate"]
def opportunities(df, dimension, minimum):
    group = df.groupby(dimension).agg(delivered_orders=("order_id", "nunique"), late_orders=("sla_breach", lambda s: (s == "Yes").sum()), avg_late_days=("late_delivery_days", "mean"), avg_freight_brl=("freight_cost_brl", "mean")).reset_index()
    group["late_delivery_rate"] = group["late_orders"] / group["delivered_orders"]
    group["excess_late_orders_vs_baseline"] = (group["late_orders"] - group["delivered_orders"] * baseline_late_rate).clip(lower=0)
    group = group[group["delivered_orders"] >= minimum].copy()
    group.insert(0, "segment_type", dimension.replace("customer_", "customer ").replace("primary_", ""))
    group.rename(columns={dimension: "segment"}, inplace=True)
    return group

priority_segments = pd.concat([opportunities(delivered, "customer_state", 200), opportunities(delivered, "primary_category", 200)]).sort_values(["excess_late_orders_vs_baseline", "late_orders"], ascending=False)
priority_segments.to_csv(OUT / "priority_segments.csv", index=False)
state_summary.to_csv(OUT / "state_performance.csv", index=False)
category_summary.to_csv(OUT / "category_performance.csv", index=False)
seller_summary.to_csv(OUT / "seller_performance.csv", index=False)
monthly_summary.to_csv(OUT / "monthly_performance.csv", index=False)
quality = pd.DataFrame([{"check": "Duplicate order IDs", "result": int(fact.order_id.duplicated().sum())},
                        {"check": "Delivered orders missing customer delivery timestamp", "result": int((fact.is_delivered & fact.order_delivered_customer_date.isna()).sum())},
                        {"check": "Delivered orders missing estimated delivery date", "result": int((fact.is_delivered & fact.order_estimated_delivery_date.isna()).sum())},
                        {"check": "Orders with invalid delivery sequence", "result": int((fact.data_quality_flag == "Delivery before purchase").sum())}])
quality.to_csv(OUT / "data_quality_checks.csv", index=False)
with open(OUT / "project_metrics.json", "w") as fp:
    json.dump(overall, fp, indent=2)
print(json.dumps(overall, indent=2))
