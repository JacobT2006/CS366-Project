CREATE TABLE categories (
  category_id   INT PRIMARY KEY,
  category_name VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE stores (
  store_id   INT PRIMARY KEY,
  store_name VARCHAR(100) NOT NULL UNIQUE,
  city       VARCHAR(60)  NOT NULL,
  country    VARCHAR(60)  NOT NULL
);

CREATE TABLE products (
  product_id   INT PRIMARY KEY,
  product_name VARCHAR(120) NOT NULL UNIQUE,
  category_id  INT NOT NULL,
  launch_date  DATE NOT NULL,
  price        DECIMAL(10,2) NOT NULL,
  is_active    BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT chk_price CHECK (price >= 0),
  CONSTRAINT fk_prod_cat FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

CREATE TABLE sales (
  sale_id    INT PRIMARY KEY,
  sale_date  DATE NOT NULL,
  store_id   INT NOT NULL,
  CONSTRAINT fk_sale_store FOREIGN KEY (store_id) REFERENCES stores(store_id)
);

CREATE TABLE sale_items (
  sale_id    INT NOT NULL,
  product_id INT NOT NULL,
  quantity   INT NOT NULL,
  PRIMARY KEY (sale_id, product_id),
  CONSTRAINT chk_qty CHECK (quantity > 0),
  CONSTRAINT fk_si_sale FOREIGN KEY (sale_id)    REFERENCES sales(sale_id),
  CONSTRAINT fk_si_prod FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE warranty_cases (
  claim_id      INT PRIMARY KEY,
  sale_id       INT NOT NULL,
  product_id    INT NOT NULL,
  claim_date    DATE NOT NULL,
  repair_status VARCHAR(30) NOT NULL,
  CONSTRAINT chk_status CHECK (repair_status IN
    ('Pending','In Progress','Completed','Rejected')),
  CONSTRAINT fk_w_item FOREIGN KEY (sale_id, product_id)
    REFERENCES sale_items(sale_id, product_id)
);

CREATE TABLE year_sales (
  year     INT PRIMARY KEY,
  earnings DECIMAL(18,2),
  revenue  DECIMAL(18,2),
  profit   DECIMAL(18,2),
  income   DECIMAL(18,2)
);

CREATE TABLE year_financials (
  year          INT PRIMARY KEY,
  total_assets  DECIMAL(18,2),
  cash_on_hand  DECIMAL(18,2),
  long_term_debt DECIMAL(18,2),
  employees     INT,
  CONSTRAINT fk_yf_year FOREIGN KEY (year) REFERENCES year_sales(year)
);

CREATE TABLE store_sales (
  store_id     INT NOT NULL,
  year         INT NOT NULL,
  total_sales  DECIMAL(18,2) NOT NULL DEFAULT 0,
  total_profit DECIMAL(18,2) NOT NULL DEFAULT 0,
  PRIMARY KEY (store_id, year),
  FOREIGN KEY (store_id) REFERENCES stores(store_id),
  FOREIGN KEY (year)     REFERENCES year_sales(year)
);