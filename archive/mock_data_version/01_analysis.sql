-- PostgreSQL 14+ analysis. Import data/raw/orders.csv into an orders table first.
-- All metrics keep cancelled orders out of delivery/SLA denominators.

WITH delivered AS (
  SELECT * FROM orders WHERE status = 'Delivered'
), overall AS (
  SELECT
    (SELECT COUNT(*) FROM orders) AS total_orders,
    COUNT(*) AS delivered_orders,
    ROUND(100.0 * COUNT(*) FILTER (WHERE sla_breach = 'No') / COUNT(*), 1) AS on_time_delivery_pct,
    ROUND(AVG(delivery_days), 1) AS avg_delivery_days,
    ROUND(100.0 * COUNT(*) FILTER (WHERE sla_breach = 'Yes') / COUNT(*), 1) AS sla_breach_pct,
    ROUND(AVG(fulfillment_cost_inr), 0) AS cost_per_delivered_order_inr
  FROM delivered
)
SELECT overall.*, ROUND(100.0 * (total_orders - delivered_orders) / total_orders, 1) AS cancellation_pct
FROM overall;

-- Rank vendors by SLA risk. A lower on-time percentage ranks worse.
SELECT vendor_name, COUNT(*) AS total_orders,
       ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'Cancelled') / COUNT(*), 1) AS cancellation_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'Delivered' AND sla_breach = 'No') /
             NULLIF(COUNT(*) FILTER (WHERE status = 'Delivered'), 0), 1) AS on_time_pct,
       ROUND(AVG(delivery_days) FILTER (WHERE status = 'Delivered'), 1) AS avg_delivery_days
FROM orders GROUP BY vendor_name ORDER BY on_time_pct ASC;

-- Quantified root-cause impact: rank by affected orders, then breached/cancelled orders.
SELECT root_cause, COUNT(*) AS affected_orders,
       COUNT(*) FILTER (WHERE sla_breach = 'Yes') AS sla_breaches,
       COUNT(*) FILTER (WHERE status = 'Cancelled') AS cancellations,
       SUM(fulfillment_cost_inr) AS fulfillment_cost_inr
FROM orders
WHERE root_cause <> 'Normal operating variation'
GROUP BY root_cause
ORDER BY (COUNT(*) FILTER (WHERE sla_breach = 'Yes') + COUNT(*) FILTER (WHERE status = 'Cancelled')) DESC;
