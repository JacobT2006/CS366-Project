-- Each query header describes its level, purpose, and business use.
-- Query: Q01 | Level: Level 2 | Title: Revenue by product category
-- Description: Calculates units sold, revenue, and distinct sales for every category.
-- Useful for: Comparing category demand and revenue to guide inventory and promotions.
SELECT c.category_id, c.category_name,
       SUM(si.quantity) AS units_sold,
       ROUND(SUM(p.price * si.quantity), 2) AS revenue,
       COUNT(DISTINCT s.sale_id) AS sale_count
FROM categories AS c
JOIN products AS p ON p.category_id = c.category_id
JOIN sale_items AS si ON si.product_id = p.product_id
JOIN sales AS s ON s.sale_id = si.sale_id
GROUP BY c.category_id, c.category_name
ORDER BY revenue DESC;

-- Query: Q02 | Level: Level 2 | Title: Annual revenue by store
-- Description: Aggregates yearly sales revenue and order counts for each store.
-- Useful for: Comparing store performance across locations and years.
SELECT st.store_id, st.store_name, YEAR(s.sale_date) AS sale_year,
       COUNT(DISTINCT s.sale_id) AS sale_count,
       ROUND(SUM(p.price * si.quantity), 2) AS revenue
FROM stores AS st
JOIN sales AS s ON s.store_id = st.store_id
JOIN sale_items AS si ON si.sale_id = s.sale_id
JOIN products AS p ON p.product_id = si.product_id
GROUP BY st.store_id, st.store_name, YEAR(s.sale_date)
ORDER BY sale_year DESC, revenue DESC;

-- Query: Q03 | Level: Level 2 | Title: Top-selling products
-- Description: Ranks products by units sold and revenue.
-- Useful for: Identifying products to prioritize for stock and marketing.
SELECT p.product_id, p.product_name, c.category_name,
       SUM(si.quantity) AS units_sold,
       ROUND(SUM(p.price * si.quantity), 2) AS revenue
FROM products AS p
JOIN categories AS c ON c.category_id = p.category_id
JOIN sale_items AS si ON si.product_id = p.product_id
JOIN sales AS s ON s.sale_id = si.sale_id
GROUP BY p.product_id, p.product_name, c.category_name
ORDER BY units_sold DESC, revenue DESC
LIMIT 15;

-- Query: Q04 | Level: Level 3 | Title: Warranty claim rate by category
-- Description: Uses conditional aggregation to compare distinct claimed sales with total sales by category.
-- Useful for: Finding product categories with unusually high warranty claim rates.
SELECT c.category_name,
       COUNT(DISTINCT si.sale_id) AS sales_count,
       COUNT(DISTINCT w.claim_id) AS claim_count,
       ROUND(100.0 * COUNT(DISTINCT w.claim_id) /
             NULLIF(COUNT(DISTINCT si.sale_id), 0), 2) AS claim_rate_percent
FROM categories AS c
JOIN products AS p ON p.category_id = c.category_id
JOIN sale_items AS si ON si.product_id = p.product_id
LEFT JOIN warranty_cases AS w ON w.sale_id = si.sale_id AND w.product_id = si.product_id
GROUP BY c.category_id, c.category_name
ORDER BY claim_rate_percent DESC;

-- Query: Q05 | Level: Level 3 | Title: Above-category-average product prices
-- Description: Uses a correlated subquery to find products priced above their category average.
-- Useful for: Reviewing premium-priced items within comparable product groups.
SELECT p.product_id, p.product_name, c.category_name, p.price,
       (SELECT ROUND(AVG(p2.price), 2)
        FROM products AS p2
        WHERE p2.category_id = p.category_id) AS category_average_price
FROM products AS p
JOIN categories AS c ON c.category_id = p.category_id
WHERE p.price > (
    SELECT AVG(p2.price)
    FROM products AS p2
    WHERE p2.category_id = p.category_id
)
ORDER BY c.category_name, p.price DESC;

-- Query: Q06 | Level: Level 3 | Title: Monthly revenue trend
-- Description: Uses a derived monthly aggregate and LAG to calculate month-over-month revenue change.
-- Useful for: Tracking seasonality and identifying meaningful sales increases or drops.
WITH monthly_revenue AS (
    SELECT DATE_FORMAT(s.sale_date, '%Y-%m') AS sales_month,
           SUM(p.price * si.quantity) AS revenue
    FROM sales AS s
    JOIN sale_items AS si ON si.sale_id = s.sale_id
    JOIN products AS p ON p.product_id = si.product_id
    GROUP BY DATE_FORMAT(s.sale_date, '%Y-%m')
)
SELECT sales_month, ROUND(revenue, 2) AS revenue,
       ROUND(LAG(revenue) OVER (ORDER BY sales_month), 2) AS previous_month_revenue,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY sales_month)) /
             NULLIF(LAG(revenue) OVER (ORDER BY sales_month), 0), 2) AS change_percent
FROM monthly_revenue
ORDER BY sales_month;

-- Query: Q07 | Level: Level 3 | Title: Stores above their country average
-- Description: Compares each store's total revenue with its country's average using derived tables.
-- Useful for: Finding high-performing locations relative to their regional peers.
SELECT store_totals.store_id, store_totals.store_name, store_totals.country,
       ROUND(store_totals.revenue, 2) AS revenue,
       ROUND(country_averages.average_revenue, 2) AS country_average
FROM (
    SELECT st.store_id, st.store_name, st.country,
           SUM(p.price * si.quantity) AS revenue
    FROM stores AS st
    JOIN sales AS s ON s.store_id = st.store_id
    JOIN sale_items AS si ON si.sale_id = s.sale_id
    JOIN products AS p ON p.product_id = si.product_id
    GROUP BY st.store_id, st.store_name, st.country
) AS store_totals
JOIN (
    SELECT country, AVG(revenue) AS average_revenue
    FROM (
        SELECT st.country, st.store_id,
               SUM(p.price * si.quantity) AS revenue
        FROM stores AS st
        JOIN sales AS s ON s.store_id = st.store_id
        JOIN sale_items AS si ON si.sale_id = s.sale_id
        JOIN products AS p ON p.product_id = si.product_id
        GROUP BY st.country, st.store_id
    ) AS per_store
    GROUP BY country
) AS country_averages ON country_averages.country = store_totals.country
WHERE store_totals.revenue > country_averages.average_revenue
ORDER BY store_totals.country, store_totals.revenue DESC;

-- Query: Q08 | Level: Level 3 | Title: Apple financial trends
-- Description: Joins annual financial tables and uses LAG to compare revenue and net income year over year.
-- Useful for: Showing whether company-level financial performance is improving over time.
SELECT ys.year, ys.revenue, ys.net_income, yf.total_assets, yf.employees,
       LAG(ys.revenue) OVER (ORDER BY ys.year) AS previous_year_revenue,
       ROUND(100.0 * (ys.revenue - LAG(ys.revenue) OVER (ORDER BY ys.year)) /
             NULLIF(LAG(ys.revenue) OVER (ORDER BY ys.year), 0), 2) AS revenue_growth_percent
FROM year_sales AS ys
JOIN year_financials AS yf ON yf.year = ys.year
ORDER BY ys.year;

-- Query: Q09 | Level: Level 2 | Title: Warranty claims by store and repair status
-- Description: Groups warranty claims by store and status, including product details.
-- Useful for: Monitoring repair workload and identifying stores with open claims.
SELECT st.store_id, st.store_name, w.repair_status,
       COUNT(*) AS claim_count,
       COUNT(DISTINCT p.product_id) AS affected_products
FROM warranty_cases AS w
JOIN sales AS s ON s.sale_id = w.sale_id
JOIN stores AS st ON st.store_id = s.store_id
JOIN products AS p ON p.product_id = w.product_id
GROUP BY st.store_id, st.store_name, w.repair_status
ORDER BY claim_count DESC;

-- Query: Q10 | Level: Level 3 | Title: Products in the top sales quartile
-- Description: Uses a derived aggregate and window ranking to identify the top quartile of products by revenue.
-- Useful for: Focusing sales efforts on products that contribute most to revenue.
WITH product_revenue AS (
    SELECT p.product_id, p.product_name, c.category_name,
           SUM(p.price * si.quantity) AS revenue
    FROM products AS p
    JOIN categories AS c ON c.category_id = p.category_id
    JOIN sale_items AS si ON si.product_id = p.product_id
    JOIN sales AS s ON s.sale_id = si.sale_id
    GROUP BY p.product_id, p.product_name, c.category_name
),
ranked_products AS (
    SELECT product_id, product_name, category_name, revenue,
           NTILE(4) OVER (ORDER BY revenue DESC) AS revenue_quartile
    FROM product_revenue
)
SELECT product_id, product_name, category_name, ROUND(revenue, 2) AS revenue,
       revenue_quartile
FROM ranked_products
WHERE revenue_quartile = 1
ORDER BY revenue DESC;
