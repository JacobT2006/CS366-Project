USE retailInfo_db;
DELIMITER //

DROP PROCEDURE IF EXISTS sp_search_products//
CREATE PROCEDURE sp_search_products(
    IN p_search VARCHAR(100),
    IN p_category_id VARCHAR(20),
    IN p_active TINYINT
)
BEGIN
    SELECT p.product_id, p.product_name, c.category_name, p.launch_date,
           p.price, p.is_active
    FROM products AS p
    JOIN categories AS c ON c.category_id = p.category_id
    WHERE (p_search IS NULL OR p.product_name LIKE CONCAT('%', p_search, '%'))
      AND (p_category_id IS NULL OR p.category_id = p_category_id)
      AND (p_active IS NULL OR p.is_active = p_active)
    ORDER BY p.product_name;
END//

DROP PROCEDURE IF EXISTS sp_record_sale//
CREATE PROCEDURE sp_record_sale(
    IN p_sale_id VARCHAR(20),
    IN p_sale_date DATE,
    IN p_store_id VARCHAR(20),
    IN p_product_id VARCHAR(20),
    IN p_quantity INT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    IF p_quantity IS NULL OR p_quantity <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Quantity must be greater than zero';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM stores WHERE store_id = p_store_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Store does not exist';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM products WHERE product_id = p_product_id AND is_active = TRUE) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Product does not exist or is inactive';
    END IF;
    IF EXISTS (SELECT 1 FROM sales WHERE sale_id = p_sale_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Sale ID already exists';
    END IF;

    START TRANSACTION;
    INSERT INTO sales (sale_id, sale_date, store_id)
    VALUES (p_sale_id, p_sale_date, p_store_id);
    INSERT INTO sale_items (sale_id, product_id, quantity)
    VALUES (p_sale_id, p_product_id, p_quantity);
    SELECT p_sale_id AS sale_id, p_product_id AS product_id, p_quantity AS quantity;
END//

DROP PROCEDURE IF EXISTS sp_update_product_price//
CREATE PROCEDURE sp_update_product_price(
    IN p_product_id VARCHAR(20),
    IN p_new_price DECIMAL(10,2)
)
BEGIN
    IF p_new_price IS NULL OR p_new_price < 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Price must be zero or greater';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM products WHERE product_id = p_product_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Product does not exist';
    END IF;

    UPDATE products SET price = p_new_price WHERE product_id = p_product_id;
    SELECT product_id, price FROM products WHERE product_id = p_product_id;
END//

DROP PROCEDURE IF EXISTS sp_set_product_active//
CREATE PROCEDURE sp_set_product_active(
    IN p_product_id VARCHAR(20),
    IN p_active TINYINT
)
BEGIN
    IF p_active IS NULL OR p_active NOT IN (0, 1) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Active flag must be 0 or 1';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM products WHERE product_id = p_product_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Product does not exist';
    END IF;

    UPDATE products SET is_active = p_active WHERE product_id = p_product_id;
    SELECT product_id, is_active FROM products WHERE product_id = p_product_id;
END//

DROP PROCEDURE IF EXISTS sp_update_warranty_status//
CREATE PROCEDURE sp_update_warranty_status(
    IN p_claim_id VARCHAR(20),
    IN p_status VARCHAR(30)
)
BEGIN
    IF p_status NOT IN ('Pending', 'In Progress', 'Completed', 'Rejected') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid warranty status';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM warranty_cases WHERE claim_id = p_claim_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Warranty claim does not exist';
    END IF;

    UPDATE warranty_cases SET repair_status = p_status WHERE claim_id = p_claim_id;
    SELECT claim_id, repair_status
    FROM warranty_cases
    WHERE claim_id = p_claim_id;
END//

DROP PROCEDURE IF EXISTS sp_store_sales_summary//
CREATE PROCEDURE sp_store_sales_summary(
    IN p_store_id VARCHAR(20),
    IN p_year INT
)
BEGIN
    SELECT st.store_id, st.store_name, YEAR(s.sale_date) AS sales_year,
           COUNT(DISTINCT s.sale_id) AS sale_count,
           SUM(si.quantity) AS units_sold,
           ROUND(SUM(p.price * si.quantity), 2) AS revenue
    FROM stores AS st
    JOIN sales AS s ON s.store_id = st.store_id
    JOIN sale_items AS si ON si.sale_id = s.sale_id
    JOIN products AS p ON p.product_id = si.product_id
    WHERE (p_store_id IS NULL OR st.store_id = p_store_id)
      AND (p_year IS NULL OR YEAR(s.sale_date) = p_year)
    GROUP BY st.store_id, st.store_name, YEAR(s.sale_date)
    ORDER BY sales_year DESC, revenue DESC;
END//

DELIMITER ;
