# PK/FK Inference Report

## Table `olist_customers_dataset`
- rows: 99441  cols: 5
- chosen PK: customer_id

## Table `olist_geolocation_dataset`
- rows: 1000163  cols: 5
- chosen PK: (none)

## Table `olist_order_items_dataset`
- rows: 112650  cols: 7
- chosen PK: order_id + order_item_id

## Table `olist_order_payments_dataset`
- rows: 103886  cols: 5
- chosen PK: order_id + payment_sequential

## Table `olist_order_reviews_dataset`
- rows: 99224  cols: 7
- chosen PK: review_id + order_id

## Table `olist_orders_dataset`
- rows: 99441  cols: 8
- chosen PK: order_id

## Table `olist_products_dataset`
- rows: 32951  cols: 9
- chosen PK: product_id

## Table `olist_sellers_dataset`
- rows: 3095  cols: 4
- chosen PK: seller_id

## Table `product_category_name_translation`
- rows: 71  cols: 2
- chosen PK: product_category_name

## FK candidates
- olist_customers_dataset.customer_id -> olist_orders_dataset.customer_id  (1:1)
- olist_order_items_dataset.order_id -> olist_orders_dataset.order_id  (1:N)
- olist_order_items_dataset.product_id -> olist_products_dataset.product_id  (1:N)
- olist_order_items_dataset.seller_id -> olist_sellers_dataset.seller_id  (1:N)
- olist_order_payments_dataset.order_id -> olist_orders_dataset.order_id  (1:N)
- olist_order_reviews_dataset.order_id -> olist_orders_dataset.order_id  (1:N)
- olist_products_dataset.product_category_name -> product_category_name_translation.product_category_name  (1:N)