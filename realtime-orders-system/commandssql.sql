-- Real-Time Orders System 

-- 1. Show current orders 
SELECT id, customer_name, product_name, status, updated_at FROM orders ORDER BY id;

-- 2. Demo: Update Rishabh Oswal's order status (Order Fulfillment Flow)
-- Show: pending → shipped
UPDATE orders SET status = 'shipped' WHERE customer_name = 'Rishabh Oswal';

-- 3. Demo: Complete Rishabh's order delivery
-- Show: shipped → delivered  
UPDATE orders SET status = 'delivered' WHERE customer_name = 'Rishabh Oswal';

-- 4. Demo: Rishabh places a new order (watch real-time creation)
INSERT INTO orders (customer_name, product_name, status) 
VALUES ('Rishabh Oswal', 'Gaming Setup', 'pending');

-- 5. Demo: Update Rishabh's new order
UPDATE orders SET status = 'shipped' WHERE customer_name = 'Rishabh Oswal' AND product_name = 'Gaming Setup';

-- 6. Create orders for Rishabh's friends (bulk operations)
INSERT INTO orders (customer_name, product_name, status) VALUES 
    ('Aarav Sharma', 'Smartphone', 'pending'),
    ('Diya Gupta', 'Tablet', 'pending'),
    ('Vihaan Singh', 'Headphones', 'pending');

-- 7. Process multiple orders (stress test)
UPDATE orders SET status = 'shipped' WHERE status = 'pending' LIMIT 3;

-- 8.  Rishabh cancels an order
DELETE FROM orders WHERE customer_name = 'Rishabh Oswal' AND product_name = 'Gaming Setup';

-- 9.  Show Rishabh's order history
SELECT id, customer_name, product_name, status, created_at, updated_at 
FROM orders WHERE customer_name = 'Rishabh Oswal' ORDER BY created_at;

-- 10. Show all current orders (final state)
SELECT id, customer_name, product_name, status, updated_at FROM orders ORDER BY updated_at DESC;

-- 11. Show change log focusing on Rishabh's activities
SELECT oc.id, oc.order_id, oc.operation_type, oc.changed_at, o.customer_name, o.product_name
FROM order_changes oc
LEFT JOIN orders o ON oc.order_id = o.id
WHERE o.customer_name = 'Rishabh Oswal' OR oc.new_data LIKE '%Rishabh Oswal%' OR oc.old_data LIKE '%Rishabh Oswal%'
ORDER BY oc.changed_at DESC LIMIT 10;

-- 12. Show complete audit trail (all recent changes)
SELECT id, order_id, operation_type, changed_at FROM order_changes 
ORDER BY changed_at DESC LIMIT 15;