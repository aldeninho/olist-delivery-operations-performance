\set ON_ERROR_STOP on
\i sql/00_schema.sql
TRUNCATE olist.reviews, olist.order_items, olist.orders, olist.customers, olist.sellers, olist.products, olist.category_translation;
\copy olist.customers FROM 'data/source_olist/olist_customers_dataset.csv' CSV HEADER;
\copy olist.orders FROM 'data/source_olist/olist_orders_dataset.csv' CSV HEADER;
\copy olist.order_items FROM 'data/source_olist/olist_order_items_dataset.csv' CSV HEADER;
\copy olist.sellers FROM 'data/source_olist/olist_sellers_dataset.csv' CSV HEADER;
CREATE TEMP TABLE products_stage (product_id text, product_category_name text, product_name_lenght text, product_description_lenght text, product_photos_qty text, product_weight_g text, product_length_cm text, product_height_cm text, product_width_cm text);
\copy products_stage FROM 'data/source_olist/olist_products_dataset.csv' CSV HEADER;
INSERT INTO olist.products (product_id, product_category_name) SELECT product_id, NULLIF(product_category_name,'') FROM products_stage;
\copy olist.category_translation FROM 'data/source_olist/product_category_name_translation.csv' CSV HEADER;
CREATE TEMP TABLE reviews_stage (review_id text, order_id text, review_score text, review_comment_title text, review_comment_message text, review_creation_date text, review_answer_timestamp text);
\copy reviews_stage FROM 'data/source_olist/olist_order_reviews_dataset.csv' CSV HEADER;
INSERT INTO olist.reviews (review_id, order_id, review_score) SELECT review_id, order_id, NULLIF(review_score,'')::int FROM reviews_stage;
\i sql/01_build_fact_orders.sql
\i sql/02_validate_and_analyze.sql
