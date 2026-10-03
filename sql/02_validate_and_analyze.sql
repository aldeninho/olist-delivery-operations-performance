-- Data quality checks
SELECT 'duplicate order IDs' AS check_name, COUNT(*) - COUNT(DISTINCT order_id) AS issue_count FROM olist.orders
UNION ALL
SELECT 'delivered orders missing actual delivery date', COUNT(*) FROM olist.orders WHERE order_status='delivered' AND order_delivered_customer_date IS NULL
UNION ALL
SELECT 'delivered orders missing estimated delivery date', COUNT(*) FROM olist.orders WHERE order_status='delivered' AND order_estimated_delivery_date IS NULL;

-- KPI scorecard. Delivery metrics use delivered orders only.
SELECT COUNT(*) AS total_orders,
       COUNT(*) FILTER (WHERE order_status='delivered') AS delivered_orders,
       ROUND(100.0 * COUNT(*) FILTER (WHERE order_status='canceled') / COUNT(*), 2) AS cancellation_rate_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE sla_breach='No') / NULLIF(COUNT(*) FILTER (WHERE order_status='delivered'), 0), 2) AS on_time_delivery_pct,
       ROUND(AVG(delivery_days) FILTER (WHERE order_status='delivered'), 2) AS avg_delivery_days,
       ROUND(AVG(freight_cost_brl) FILTER (WHERE order_status='delivered'), 2) AS freight_cost_per_delivered_order_brl
FROM olist.fact_orders;

-- Priority segments: excess late orders compared with the overall late rate.
WITH baseline AS (SELECT AVG((sla_breach='Yes')::int) AS late_rate FROM olist.fact_orders WHERE order_status='delivered')
SELECT customer_state, COUNT(*) AS delivered_orders, COUNT(*) FILTER (WHERE sla_breach='Yes') AS late_orders,
       ROUND(100.0 * AVG((sla_breach='Yes')::int), 2) AS late_rate_pct,
       ROUND(COUNT(*) FILTER (WHERE sla_breach='Yes') - COUNT(*) * baseline.late_rate, 1) AS excess_late_orders_vs_baseline
FROM olist.fact_orders CROSS JOIN baseline WHERE order_status='delivered'
GROUP BY customer_state, baseline.late_rate HAVING COUNT(*) >= 200
ORDER BY excess_late_orders_vs_baseline DESC;
