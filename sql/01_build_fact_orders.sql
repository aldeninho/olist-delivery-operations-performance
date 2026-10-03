-- One row per order. Freight value is a logistics cost proxy, not full fulfillment cost.
CREATE OR REPLACE VIEW olist.fact_orders AS
WITH item_agg AS (
  SELECT i.order_id, SUM(i.price) AS order_value_brl, SUM(i.freight_value) AS freight_cost_brl,
         COUNT(*) AS item_count, COUNT(DISTINCT i.seller_id) AS seller_count,
         COALESCE(MAX(t.product_category_name_english), 'unavailable') AS category
  FROM olist.order_items i
  LEFT JOIN olist.products p ON p.product_id = i.product_id
  LEFT JOIN olist.category_translation t ON t.product_category_name = p.product_category_name
  GROUP BY i.order_id
), review_agg AS (
  SELECT order_id, AVG(review_score) AS review_score FROM olist.reviews GROUP BY order_id
)
SELECT o.order_id, o.order_status, o.order_purchase_timestamp, o.order_delivered_customer_date,
       o.order_estimated_delivery_date, date_trunc('month', o.order_purchase_timestamp)::date AS purchase_month,
       c.customer_state, c.customer_city, i.order_value_brl, i.freight_cost_brl, i.item_count, i.seller_count,
       i.category, r.review_score,
       EXTRACT(epoch FROM o.order_delivered_customer_date - o.order_purchase_timestamp)/86400.0 AS delivery_days,
       GREATEST(EXTRACT(epoch FROM o.order_delivered_customer_date - o.order_estimated_delivery_date)/86400.0, 0) AS late_delivery_days,
       CASE WHEN o.order_status = 'delivered' AND o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 'Yes'
            WHEN o.order_status = 'delivered' THEN 'No' ELSE 'Not delivered' END AS sla_breach
FROM olist.orders o
LEFT JOIN olist.customers c ON c.customer_id = o.customer_id
LEFT JOIN item_agg i ON i.order_id = o.order_id
LEFT JOIN review_agg r ON r.order_id = o.order_id;
