-- StockWise Soweto MySQL 8 schema. Tables are normalized to 3NF where practical.
CREATE DATABASE IF NOT EXISTS spaza_inventory CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE spaza_inventory;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(160) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('owner', 'admin') NOT NULL DEFAULT 'owner',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_users_email (email)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS shops (
  id INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(20) NOT NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  cash_budget DECIMAL(12,2) NOT NULL DEFAULT 2500.00,
  storage_capacity_units INT NOT NULL DEFAULT 600,
  review_period_days INT NOT NULL DEFAULT 3,
  safety_stock_days INT NOT NULL DEFAULT 1,
  owner_user_id INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_shops_owner FOREIGN KEY (owner_user_id) REFERENCES users(id),
  CONSTRAINT ck_shops_budget CHECK (cash_budget >= 0),
  CONSTRAINT ck_shops_capacity CHECK (storage_capacity_units >= 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS suppliers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  contact_phone VARCHAR(30),
  lead_time_days INT NOT NULL DEFAULT 2,
  delivery_fee DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT ck_supplier_lead CHECK (lead_time_days >= 0),
  CONSTRAINT ck_supplier_fee CHECK (delivery_fee >= 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS products (
  id INT AUTO_INCREMENT PRIMARY KEY,
  sku VARCHAR(40) NOT NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  category VARCHAR(80) NOT NULL,
  pack_size INT NOT NULL,
  unit_cost DECIMAL(10,2) NOT NULL,
  storage_units_per_item DECIMAL(8,3) NOT NULL DEFAULT 1.000,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  supplier_id INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_products_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
  CONSTRAINT ck_products_pack CHECK (pack_size > 0),
  CONSTRAINT ck_products_cost CHECK (unit_cost >= 0),
  INDEX ix_products_sku_supplier (sku, supplier_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS inventory_balances (
  id INT AUTO_INCREMENT PRIMARY KEY,
  shop_id INT NOT NULL,
  product_id INT NOT NULL,
  on_hand INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_inventory_shop FOREIGN KEY (shop_id) REFERENCES shops(id),
  CONSTRAINT fk_inventory_product FOREIGN KEY (product_id) REFERENCES products(id),
  CONSTRAINT uq_inventory_shop_product UNIQUE (shop_id, product_id),
  CONSTRAINT ck_inventory_non_negative CHECK (on_hand >= 0),
  INDEX ix_inventory_shop_product (shop_id, product_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS stock_movements (
  id INT AUTO_INCREMENT PRIMARY KEY,
  shop_id INT NOT NULL,
  product_id INT NOT NULL,
  movement_type ENUM('sale','loss','receipt','return','adjustment_in','adjustment_out') NOT NULL,
  quantity INT NOT NULL,
  note VARCHAR(255),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_movements_shop FOREIGN KEY (shop_id) REFERENCES shops(id),
  CONSTRAINT fk_movements_product FOREIGN KEY (product_id) REFERENCES products(id),
  CONSTRAINT ck_movement_non_zero CHECK (quantity <> 0),
  INDEX ix_movement_shop_product_date (shop_id, product_id, created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS demand_history (
  id INT AUTO_INCREMENT PRIMARY KEY,
  shop_id INT NOT NULL,
  product_id INT NOT NULL,
  demand_date DATE NOT NULL,
  quantity_sold INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_demand_shop FOREIGN KEY (shop_id) REFERENCES shops(id),
  CONSTRAINT fk_demand_product FOREIGN KEY (product_id) REFERENCES products(id),
  CONSTRAINT uq_daily_demand UNIQUE (shop_id, product_id, demand_date),
  CONSTRAINT ck_demand_non_negative CHECK (quantity_sold >= 0),
  INDEX ix_demand_shop_product_date (shop_id, product_id, demand_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS orders (
  id INT AUTO_INCREMENT PRIMARY KEY,
  shop_id INT NOT NULL,
  supplier_id INT NOT NULL,
  status ENUM('draft','approved','placed','received','cancelled') NOT NULL DEFAULT 'draft',
  delivery_fee DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  total_cost DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  placed_at DATETIME NULL,
  expected_at DATETIME NULL,
  received_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_orders_shop FOREIGN KEY (shop_id) REFERENCES shops(id),
  CONSTRAINT fk_orders_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
  CONSTRAINT ck_orders_cost CHECK (total_cost >= 0),
  INDEX ix_orders_shop_status_date (shop_id, status, created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS order_lines (
  id INT AUTO_INCREMENT PRIMARY KEY,
  order_id INT NOT NULL,
  product_id INT NOT NULL,
  quantity_ordered INT NOT NULL,
  quantity_received INT NOT NULL DEFAULT 0,
  unit_cost DECIMAL(10,2) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_order_lines_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
  CONSTRAINT fk_order_lines_product FOREIGN KEY (product_id) REFERENCES products(id),
  CONSTRAINT uq_order_product UNIQUE (order_id, product_id),
  CONSTRAINT ck_order_line_positive CHECK (quantity_ordered > 0),
  CONSTRAINT ck_order_line_received CHECK (quantity_received BETWEEN 0 AND quantity_ordered),
  INDEX ix_order_lines_product (product_id)
) ENGINE=InnoDB;

