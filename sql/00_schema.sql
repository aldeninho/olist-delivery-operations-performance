-- PostgreSQL 14+. Load the original Olist CSVs into these tables with COPY.
CREATE SCHEMA IF NOT EXISTS olist;
CREATE TABLE IF NOT EXISTS olist.orders (
  order_id text PRIMARY KEY, customer_id text, order_status text,
  order_purchase_timestamp timestamp, order_approved_at timestamp,
  order_delivered_carrier_date timestamp, order_delivered_customer_date timestamp,
  order_estimated_delivery_date timestamp
);
CREATE TABLE IF NOT EXISTS olist.customers (customer_id text PRIMARY KEY, customer_unique_id text, customer_zip_code_prefix integer, customer_city text, customer_state text);
CREATE TABLE IF NOT EXISTS olist.order_items (order_id text, order_item_id integer, product_id text, seller_id text, shipping_limit_date timestamp, price numeric, freight_value numeric);
CREATE TABLE IF NOT EXISTS olist.sellers (seller_id text PRIMARY KEY, seller_zip_code_prefix integer, seller_city text, seller_state text);
CREATE TABLE IF NOT EXISTS olist.products (product_id text PRIMARY KEY, product_category_name text);
CREATE TABLE IF NOT EXISTS olist.category_translation (product_category_name text PRIMARY KEY, product_category_name_english text);
CREATE TABLE IF NOT EXISTS olist.reviews (review_id text, order_id text, review_score integer);
CREATE INDEX IF NOT EXISTS ix_orders_customer ON olist.orders(customer_id);
CREATE INDEX IF NOT EXISTS ix_items_order ON olist.order_items(order_id);
CREATE INDEX IF NOT EXISTS ix_items_seller ON olist.order_items(seller_id);
