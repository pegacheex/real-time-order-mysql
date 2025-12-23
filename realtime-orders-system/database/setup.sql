-- Real-Time Order Updates System - Database Setup
-- Creates orders table, change log table, and triggers

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS realtime_orders;
USE realtime_orders;

-- Main orders table
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    status ENUM('pending', 'shipped', 'delivered') NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_updated_at (updated_at)
);

-- Change log table for capturing all modifications
CREATE TABLE IF NOT EXISTS order_changes (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    operation_type ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,
    old_data JSON NULL,
    new_data JSON NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    INDEX idx_processed_changed (processed, changed_at),
    INDEX idx_order_id (order_id)
);

-- Drop existing triggers if they exist
DROP TRIGGER IF EXISTS orders_after_insert;
DROP TRIGGER IF EXISTS orders_after_update;
DROP TRIGGER IF EXISTS orders_after_delete;

-- Trigger for INSERT operations
DELIMITER $$
CREATE TRIGGER orders_after_insert
    AFTER INSERT ON orders
    FOR EACH ROW
BEGIN
    INSERT INTO order_changes (
        order_id, 
        operation_type, 
        old_data, 
        new_data
    ) VALUES (
        NEW.id,
        'INSERT',
        NULL,
        JSON_OBJECT(
            'id', NEW.id,
            'customer_name', NEW.customer_name,
            'product_name', NEW.product_name,
            'status', NEW.status,
            'created_at', NEW.created_at,
            'updated_at', NEW.updated_at
        )
    );
END$$

-- Trigger for UPDATE operations
CREATE TRIGGER orders_after_update
    AFTER UPDATE ON orders
    FOR EACH ROW
BEGIN
    INSERT INTO order_changes (
        order_id, 
        operation_type, 
        old_data, 
        new_data
    ) VALUES (
        NEW.id,
        'UPDATE',
        JSON_OBJECT(
            'id', OLD.id,
            'customer_name', OLD.customer_name,
            'product_name', OLD.product_name,
            'status', OLD.status,
            'created_at', OLD.created_at,
            'updated_at', OLD.updated_at
        ),
        JSON_OBJECT(
            'id', NEW.id,
            'customer_name', NEW.customer_name,
            'product_name', NEW.product_name,
            'status', NEW.status,
            'created_at', NEW.created_at,
            'updated_at', NEW.updated_at
        )
    );
END$$

-- Trigger for DELETE operations
CREATE TRIGGER orders_after_delete
    AFTER DELETE ON orders
    FOR EACH ROW
BEGIN
    INSERT INTO order_changes (
        order_id, 
        operation_type, 
        old_data, 
        new_data
    ) VALUES (
        OLD.id,
        'DELETE',
        JSON_OBJECT(
            'id', OLD.id,
            'customer_name', OLD.customer_name,
            'product_name', OLD.product_name,
            'status', OLD.status,
            'created_at', OLD.created_at,
            'updated_at', OLD.updated_at
        ),
        NULL
    );
END$$
DELIMITER ;

-- Insert sample data for testing
INSERT INTO orders (customer_name, product_name, status) VALUES
    ('Rishabh Oswal', 'MacBook Pro', 'pending'),
    ('Priya Patel', 'iPhone 15', 'shipped'),
    ('Rohan Gupta', 'iPad Air', 'delivered'),
    ('Ananya Singh', 'AirPods Pro', 'pending');

-- Verify setup
SELECT 'Orders table created with sample data:' as status;
SELECT * FROM orders;

SELECT 'Change log table ready:' as status;
SELECT COUNT(*) as initial_changes FROM order_changes;

SELECT 'Triggers created successfully' as status;