# Olist Delivery Operations Performance

**Stack: PostgreSQL | Python | Excel | Power BI**

## Executive summary

This project analyzes real, anonymized Brazilian e-commerce data from Olist to identify delivery-performance priorities. Across 99,441 orders, 91.9% of delivered orders met the estimated delivery date. The SLA-breach rate was 8.1%, and late delivery corresponded to a much lower average review score (2.57 versus 4.29 for on-time orders).

The biggest priority segment is customer state **RJ**: it had 1,664 late deliveries, approximately 662 more than expected at the overall late-delivery rate. This is an association, not a proven cause; route, carrier, seller, and inventory data must be validated before intervention.

## Business problem

An Operations Manager needs to monitor late delivery, cancellations, freight cost, customer impact, seller performance, and geographic variation, then identify where to investigate first.

## Data source and scope

Source: [Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). The data is real anonymized marketplace activity in Brazil from September 2016 to October 2018. It includes orders, customers, sellers, item-level freight, categories, and reviews. The original source tables are preserved in `data/source_olist/`.

## Deliverables

- `data/processed/fact_orders.csv` — one row per order, built from the relational source data
- `data/processed/seller_delivery_fact.csv` — one row per seller-item contribution
- `data/processed/` — validated summary tables, quality checks, and opportunity sizing
- `sql/00_schema.sql`, `01_build_fact_orders.sql`, `02_validate_and_analyze.sql`, `03_load_and_run.sql` — PostgreSQL setup, transformation, validation, analysis, and a full load-and-run script (validated end-to-end on PostgreSQL 16)
- `excel/operations_review.xlsx` — management review workbook with dashboard and detail tabs
- `powerbi/DAX_Measures.md` — import steps, DAX measures, and page specification
- `powerbi/olist_delivery_operations/` — PBI Desktop source project (TMDL data model + PBIR report JSON) for the 3-page dashboard
- `powerbi/olist_delivery_operations.pbit` — compiled Power BI template; open in Power BI Desktop, refresh against the local CSVs, then **Save As → .pbix** to embed cached data

## KPI definitions

| KPI | Definition |
|---|---|
| On-time delivery % | Delivered orders on or before their promised date ÷ delivered orders |
| Average delivery time | Average days from order date to delivered date; cancelled orders excluded |
| SLA breach rate | Delivered orders after their promised date ÷ delivered orders |
| Cancellation rate | Cancelled orders ÷ all orders |
| Freight cost per delivered order | Freight value ÷ delivered orders; a logistics cost proxy, not full fulfillment cost |

## Data model

`Fact Orders` is the main fact table. The report can be modeled with Date, Customer State, Category, and Status dimensions. `Seller Delivery Fact` supports seller comparisons at seller-item grain, avoiding false order-level seller attribution when an order has several sellers.

## Analysis approach

1. Validate status/date sequences, nulls, duplicate IDs, and key delivery fields.
2. Calculate operational KPIs with explicit denominators.
3. Compare performance by month, region, vendor, and category.
4. Rank state/category priority segments by excess late orders versus the overall late-delivery baseline.
5. Recommend operational validation steps rather than claiming causality from observational data.

## Top three priority segments

| Rank | Segment | Quantified impact | Recommended validation |
|---|---|---|---|
| 1 | RJ customer state | 1,664 late deliveries; ~662 excess late orders versus baseline | Carrier coverage and promised-date logic |
| 2 | BA customer state | 457 late deliveries; ~193 excess late orders versus baseline | Route and seller-mix comparison |
| 3 | CE customer state | 196 late deliveries; ~92 excess late orders versus baseline | Delivery handoff and freight review |

## Dashboard preview

![Excel dashboard preview](images/olist_dashboard_preview.png)

## Interview talking points

- Explain why cancelled orders are excluded from delivery-time and SLA denominators.
- Show why seller analysis uses seller-item grain while KPIs use order grain.
- Explain the distinction between an observed priority segment and a causal finding that requires operational validation.
- Describe how you would refresh the report when new order data arrives.

## How to reproduce

1. `python prepare_olist_data.py` — rebuild `data/processed/` from `data/source_olist/`.
2. `node build_olist_workbook.mjs` — rebuild `excel/operations_review.xlsx` and the dashboard preview image.
3. `node verify_olist_project.mjs` — validate the workbook renders and KPIs match `project_metrics.json`.

The earlier mock-data version of this project is preserved untouched under `archive/mock_data_version/` and is not part of the current workflow.

## Limitations and next steps

The public source supports an end-to-end portfolio workflow but does not include carrier scan events, inventory availability, or a validated causal label. For production, integrate those data sources and track interventions against a controlled baseline.
