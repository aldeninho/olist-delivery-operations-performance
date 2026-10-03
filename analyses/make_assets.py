"""Generate trend-analysis and data-model diagrams as PNGs for the README."""
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.patches as mp

DATA = "data/processed"
IM = "images"

# ---------- trend chart ----------
months, breach, days, cancel, freight = [], [], [], [], []
with open(f"{DATA}/monthly_trend.csv") as f:
    for r in csv.DictReader(f):
        months.append(r["purchase_month"])
        breach.append(float(r["sla_breach_pct"]))
        days.append(float(r["avg_delivery_days"]))
        cancel.append(float(r["cancellation_rate_pct"]))
        freight.append(float(r["freight_cost_per_delivered_order_brl"]))

fig, axes = plt.subplots(2, 2, figsize=(13, 8))
ticks = months[::3]
def _ax(ax, x, y, color, ylabel, title):
    ax.plot(x, y, marker=".", color=color, linewidth=1.6)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_ylabel(ylabel)
    ax.set_xticks(range(0, len(x), 3)); ax.set_xticklabels(ticks, rotation=45, fontsize=8)
    ax.grid(alpha=0.3)
_ax(axes[0,0], months, breach, "#d62728", "%", "Monthly late-delivery (SLA breach) %")
_ax(axes[0,1], months, days, "#1f77b4", "days", "Monthly average delivery days")
_ax(axes[1,0], months, cancel, "#9467bd", "%", "Monthly cancellation rate %")
_ax(axes[1,1], months, freight, "#2ca02c", "BRL", "Monthly freight cost / delivered order (BRL)")
fig.suptitle("Month-over-month delivery operations trend", fontsize=13, fontweight="bold")
fig.tight_layout(rect=(0, 0, 1, 0.95))
fig.savefig(f"{IM}/monthly_trend.png", dpi=130)

# ---------- data model diagram ----------
fig, ax = plt.subplots(figsize=(12, 6))
ax.axis("off")

def box(ax, x, y, w, h, title, lines):
    ax.add_patch(mp.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", fc="#f3f6fb", ec="#335599", lw=1.4))
    ax.text(x + w/2, y + h - 0.06, title, ha="center", va="top", fontsize=11, fontweight="bold", color="#1c3d7a")
    yy = y + h - 0.14
    for line in lines[:24]:
        ax.text(x + 0.015, yy, line, ha="left", va="top", fontsize=7.5, family="monospace")
        yy -= 0.045

box(ax, 0.03, 0.18, 0.44, 0.78, "Fact Orders (order grain)", [
    "order_id  PK", "order_status", "order_purchase_timestamp", "order_delivered_customer_date",
    "purchase_month", "customer_state", "customer_city", "order_value_brl",
    "freight_cost_brl", "item_count", "seller_count", "primary_category",
    "review_score", "delivery_days", "late_delivery_days", "sla_breach",
])
box(ax, 0.53, 0.30, 0.44, 0.66, "Seller Delivery Fact (seller-item grain)", [
    "order_id  FK", "seller_id", "seller_state", "category", "order_status",
    "order_purchase_timestamp", "order_delivered_customer_date",
    "price", "freight_cost_brl", "delivery_days", "sla_breach",
])
# relationships
ax.annotate("1", xy=(0.535, 0.62), fontsize=12, fontweight="bold", color="#1c3d7a")
ax.annotate("*", xy=(0.47, 0.55), fontsize=12, fontweight="bold", color="#1c3d7a")
ax.annotate("order_id", xy=(0.50, 0.58), fontsize=8, ha="center", color="#444")
ax.plot([0.47, 0.53], [0.58, 0.58], color="#335599", lw=1.6)
ax.text(0.26, 0.10, "1:1 reference join — Fact Orders anchors all KPIs; Seller Delivery Fact supports seller/route validation", ha="center", fontsize=9, color="#555")
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
fig.savefig(f"{IM}/data_model.png", dpi=130, bbox_inches="tight")

# ---------- KPI texture ----------
values = {"Total orders": "99,441", "On-time %": "91.9%", "SLA breach": "8.1%", "Cancel rate": "0.6%", "Avg delivery": "12.6 d", "Freight / order": "R$22.79"}
fig, axes = plt.subplots(1, 6, figsize=(16, 2.6))
colors = ["#f7e7a0", "#c4f0c2", "#f6c6c6", "#cfd8f7", "#f7d8f5", "#c9e8f5"]
for ax, (k, v), c in zip(axes, values.items(), colors):
    ax.axis("off")
    ax.add_patch(mp.FancyBboxPatch((0.05, 0.05), 0.9, 0.9, boxstyle="round,pad=0.05", fc=c, ec="#888", lw=1.2))
    ax.text(0.5, 0.62, v, ha="center", fontsize=22, fontweight="bold")
    ax.text(0.5, 0.26, k, ha="center", fontsize=9)
fig.subplots_adjust(wspace=0.55)
fig.savefig(f"{IM}/kpi_cards.png", dpi=130, bbox_inches="tight")
print("ok")
