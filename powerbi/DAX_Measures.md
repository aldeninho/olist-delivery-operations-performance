# Power BI measures

Import `data/processed/fact_orders.csv` as `Fact Orders`. This is a real, anonymized Olist public dataset at order grain. Set timestamp columns to Date/Time and create a Date table related to `Fact Orders[order_purchase_timestamp]`.

```DAX
Total Orders = COUNTROWS('Fact Orders')
Delivered Orders = CALCULATE([Total Orders], 'Fact Orders'[order_status] = "delivered")
Cancelled Orders = CALCULATE([Total Orders], 'Fact Orders'[order_status] = "canceled")
Cancellation Rate = DIVIDE([Cancelled Orders], [Total Orders])
On-Time Deliveries = CALCULATE([Delivered Orders], 'Fact Orders'[sla_breach] = "No")
On-Time Delivery % = DIVIDE([On-Time Deliveries], [Delivered Orders])
SLA Breaches = CALCULATE([Delivered Orders], 'Fact Orders'[sla_breach] = "Yes")
SLA Breach Rate = DIVIDE([SLA Breaches], [Delivered Orders])
Average Delivery Days = AVERAGEX(FILTER('Fact Orders', 'Fact Orders'[order_status] = "delivered"), 'Fact Orders'[delivery_days])
Freight Cost per Delivered Order = DIVIDE(CALCULATE(SUM('Fact Orders'[freight_cost_brl]), 'Fact Orders'[order_status] = "delivered"), [Delivered Orders])
```

## Report pages

1. **Executive overview:** six KPI cards, monthly on-time trend, vendor ranking, and three action recommendations.
2. **Delivery & SLA:** SLA-breach rate by region and vendor, delivery-day distribution, filters for month, region, vendor, and category.
3. **Freight & delivery priorities:** freight cost per delivered order by state/category, cancelled-order trend, and priority-segment table.

Use the supplied summaries in `data/processed/` as validation views. Do not label state/category/seller associations as proven causes: they are priority segments requiring operational validation.
