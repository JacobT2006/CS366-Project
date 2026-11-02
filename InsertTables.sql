USE retailInfo_db;

-- Drop in child-to-parent order so the script can be re-run
DROP TABLE IF EXISTS dataset_imports;
DROP TABLE IF EXISTS store_sales;
DROP TABLE IF EXISTS year_financials;
DROP TABLE IF EXISTS year_sales;
DROP TABLE IF EXISTS warranty_cases;
DROP TABLE IF EXISTS sale_items;
DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS stores;
DROP TABLE IF EXISTS categories;

CREATE TABLE categories (
  category_id   VARCHAR(20) PRIMARY KEY,
  category_name VARCHAR(80) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE stores (
  store_id   VARCHAR(20) PRIMARY KEY,
  store_name VARCHAR(100) NOT NULL UNIQUE,
  city       VARCHAR(60)  NOT NULL,
  country    VARCHAR(60)  NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE products (
  product_id   VARCHAR(20) PRIMARY KEY,
  product_name VARCHAR(120) NOT NULL UNIQUE,
  category_id  VARCHAR(20)  NOT NULL,
  launch_date  DATE NOT NULL,
  price        DECIMAL(10,2) NOT NULL,
  is_active    BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT chk_price CHECK (price >= 0),
  CONSTRAINT fk_prod_cat FOREIGN KEY (category_id) REFERENCES categories(category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE sales (
  sale_id   VARCHAR(20) PRIMARY KEY,
  sale_date DATE NOT NULL,
  store_id  VARCHAR(20) NOT NULL,
  CONSTRAINT fk_sale_store FOREIGN KEY (store_id) REFERENCES stores(store_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Bridge table resolving the many-to-many between sales and products
CREATE TABLE sale_items (
  sale_id    VARCHAR(20) NOT NULL,
  product_id VARCHAR(20) NOT NULL,
  quantity   INT NOT NULL,
  PRIMARY KEY (sale_id, product_id),
  CONSTRAINT chk_qty CHECK (quantity > 0),
  CONSTRAINT fk_si_sale FOREIGN KEY (sale_id)    REFERENCES sales(sale_id),
  CONSTRAINT fk_si_prod FOREIGN KEY (product_id) REFERENCES products(product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE warranty_cases (
  claim_id      VARCHAR(20) PRIMARY KEY,
  sale_id       VARCHAR(20) NOT NULL,
  product_id    VARCHAR(20) NOT NULL,
  claim_date    DATE NOT NULL,
  repair_status VARCHAR(30) NOT NULL,
  CONSTRAINT chk_warranty_status CHECK (repair_status IN
    ('Pending', 'In Progress', 'Completed', 'Rejected')),
  CONSTRAINT fk_w_item FOREIGN KEY (sale_id, product_id)
    REFERENCES sale_items(sale_id, product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE year_sales (
  year               INT PRIMARY KEY,
  ebitda             DECIMAL(18,2),
  revenue            DECIMAL(18,2),
  gross_profit       DECIMAL(18,2),
  operating_income   DECIMAL(18,2),
  net_income         DECIMAL(18,2),
  eps                DECIMAL(10,2),
  shares_outstanding BIGINT,
  year_close_price   DECIMAL(10,4),
  gross_margin       DECIMAL(6,2),
  pe_ratio           DECIMAL(8,2)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE year_financials (
  year           INT PRIMARY KEY,
  total_assets   DECIMAL(18,2),
  cash_on_hand   DECIMAL(18,2),
  long_term_debt DECIMAL(18,2),
  total_liabilities DECIMAL(18,2),
  employees      INT,
  CONSTRAINT fk_yf_year FOREIGN KEY (year) REFERENCES year_sales(year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE store_sales (
  store_id     VARCHAR(20) NOT NULL,
  year         INT NOT NULL,
  total_sales  DECIMAL(18,2) NOT NULL DEFAULT 0,
  total_profit DECIMAL(18,2) NOT NULL DEFAULT 0,
  PRIMARY KEY (store_id, year),
  CONSTRAINT fk_ss_store FOREIGN KEY (store_id) REFERENCES stores(store_id),
  CONSTRAINT fk_ss_year  FOREIGN KEY (year)     REFERENCES year_sales(year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE dataset_imports (
  dataset_name VARCHAR(50) PRIMARY KEY,
  row_count    BIGINT NOT NULL,
  imported_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;