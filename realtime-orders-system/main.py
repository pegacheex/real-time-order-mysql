"""Main application entry point for the real-time orders system."""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from config import config
from database.connection import db_manager
from event_listener import event_listener
from websocket_manager import websocket_manager
from models import WebSocketMessage

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Real-Time Orders System")
    
    try:
        # Validate configuration
        config.validate()
        
        # Initialize database
        await db_manager.initialize()
        
        # Subscribe WebSocket manager to event listener
        event_listener.subscribe(websocket_manager.broadcast_change)
        
        # Start event listener
        await event_listener.start()
        
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(heartbeat_loop())
        
        logger.info("System startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Real-Time Orders System")
        
        # Cancel heartbeat task
        if 'heartbeat_task' in locals():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Stop event listener
        await event_listener.stop()
        
        # Close database connections
        await db_manager.close()
        
        logger.info("System shutdown completed")

# Create FastAPI app
app = FastAPI(
    title="Real-Time Orders System",
    description="A system for real-time order updates using WebSockets",
    version="1.0.0",
    lifespan=lifespan
)

async def heartbeat_loop():
    """Send periodic heartbeats to connected clients."""
    while True:
        try:
            await asyncio.sleep(30)  # Send heartbeat every 30 seconds
            await websocket_manager.send_heartbeat()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in heartbeat loop: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time order updates."""
    await websocket_manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            
            # Echo back client messages (for testing)
            try:
                client_message = eval(data)  # In production, use proper JSON parsing
                if isinstance(client_message, dict) and client_message.get("type") == "ping":
                    pong_message = WebSocketMessage(
                        type="heartbeat",
                        data={"message": "pong"}
                    )
                    await websocket.send_text(pong_message.json())
            except:
                pass  # Ignore malformed messages
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        db_healthy = await db_manager.health_check()
        
        return {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "event_listener": "running" if event_listener.running else "stopped",
            "websocket_connections": len(websocket_manager.active_connections),
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.get("/stats")
async def get_stats():
    """Get system statistics."""
    try:
        connection_stats = websocket_manager.get_connection_stats()
        
        # Get recent changes count
        recent_changes = await db_manager.execute_query(
            "SELECT COUNT(*) as count FROM order_changes WHERE changed_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)"
        )
        
        return {
            "websocket_connections": connection_stats,
            "recent_changes_last_hour": recent_changes[0]["count"] if recent_changes else 0,
            "event_listener_status": "running" if event_listener.running else "stopped"
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/client", response_class=HTMLResponse)
async def get_client():
    """Serve the HTML client for testing."""
    return HTMLResponse(content=CLIENT_HTML)

# Simple HTML client for testing
CLIENT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Real-Time Orders Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .status { padding: 10px; border-radius: 4px; margin-bottom: 20px; }
        .connected { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .disconnected { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .orders-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .order-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .order-header { display: flex; justify-content: between; align-items: center; margin-bottom: 15px; }
        .order-id { font-size: 18px; font-weight: bold; color: #2c3e50; }
        .status-badge { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        .status-pending { background-color: #fff3cd; color: #856404; }
        .status-shipped { background-color: #cce5ff; color: #004085; }
        .status-delivered { background-color: #d4edda; color: #155724; }
        .order-details { margin-top: 10px; }
        .order-details div { margin: 5px 0; }
        .updates-log { background: white; padding: 20px; border-radius: 8px; margin-top: 20px; max-height: 300px; overflow-y: auto; }
        .update-item { padding: 10px; border-left: 4px solid #007bff; margin: 10px 0; background-color: #f8f9fa; }
        .update-insert { border-left-color: #28a745; }
        .update-update { border-left-color: #ffc107; }
        .update-delete { border-left-color: #dc3545; }
        .timestamp { font-size: 12px; color: #6c757d; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Real-Time Orders Dashboard</h1>
            <p>Live updates from MySQL database changes</p>
        </div>
        
        <div id="status" class="status disconnected">
            Connecting to WebSocket...
        </div>
        
        <div id="orders" class="orders-grid">
            <!-- Orders will be populated here -->
        </div>
        
        <div class="updates-log">
            <h3>Live Updates Log</h3>
            <div id="updates">
                <!-- Updates will be shown here -->
            </div>
        </div>
    </div>

    <script>
        let ws;
        let orders = {};
        
        function connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function() {
                document.getElementById('status').className = 'status connected';
                document.getElementById('status').textContent = 'Connected to real-time updates';
                console.log('WebSocket connected');
            };
            
            ws.onmessage = function(event) {
                const message = JSON.parse(event.data);
                console.log('Received message:', message);
                
                switch(message.type) {
                    case 'initial_data':
                        handleInitialData(message.data);
                        break;
                    case 'order_change':
                        handleOrderChange(message.data);
                        break;
                    case 'heartbeat':
                        console.log('Heartbeat received');
                        break;
                    case 'error':
                        console.error('Server error:', message.data);
                        break;
                }
            };
            
            ws.onclose = function() {
                document.getElementById('status').className = 'status disconnected';
                document.getElementById('status').textContent = 'Disconnected - Reconnecting...';
                console.log('WebSocket disconnected, reconnecting...');
                setTimeout(connect, 3000);
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
            };
        }
        
        function handleInitialData(data) {
            orders = {};
            data.orders.forEach(order => {
                orders[order.id] = order;
            });
            renderOrders();
            addUpdate('System', 'Loaded initial data', new Date().toISOString());
        }
        
        function handleOrderChange(data) {
            const { operation, order_data, order_id, timestamp } = data;
            
            switch(operation) {
                case 'INSERT':
                    orders[order_id] = order_data;
                    addUpdate('INSERT', `New order #${order_id}: ${order_data.product_name}`, timestamp);
                    break;
                case 'UPDATE':
                    if (orders[order_id]) {
                        const oldStatus = orders[order_id].status;
                        orders[order_id] = order_data;
                        addUpdate('UPDATE', `Order #${order_id} status: ${oldStatus} → ${order_data.status}`, timestamp);
                    }
                    break;
                case 'DELETE':
                    if (orders[order_id]) {
                        const orderName = orders[order_id].product_name;
                        delete orders[order_id];
                        addUpdate('DELETE', `Order #${order_id} deleted: ${orderName}`, timestamp);
                    }
                    break;
            }
            
            renderOrders();
        }
        
        function renderOrders() {
            const ordersContainer = document.getElementById('orders');
            ordersContainer.innerHTML = '';
            
            Object.values(orders).forEach(order => {
                const orderCard = document.createElement('div');
                orderCard.className = 'order-card';
                orderCard.innerHTML = `
                    <div class="order-header">
                        <span class="order-id">Order #${order.id}</span>
                        <span class="status-badge status-${order.status}">${order.status.toUpperCase()}</span>
                    </div>
                    <div class="order-details">
                        <div><strong>Customer:</strong> ${order.customer_name}</div>
                        <div><strong>Product:</strong> ${order.product_name}</div>
                        <div><strong>Created:</strong> ${new Date(order.created_at).toLocaleString()}</div>
                        <div><strong>Updated:</strong> ${new Date(order.updated_at).toLocaleString()}</div>
                    </div>
                `;
                ordersContainer.appendChild(orderCard);
            });
        }
        
        function addUpdate(type, message, timestamp) {
            const updatesContainer = document.getElementById('updates');
            const updateItem = document.createElement('div');
            updateItem.className = `update-item update-${type.toLowerCase()}`;
            updateItem.innerHTML = `
                <div><strong>${type}:</strong> ${message}</div>
                <div class="timestamp">${new Date(timestamp).toLocaleString()}</div>
            `;
            updatesContainer.insertBefore(updateItem, updatesContainer.firstChild);
            
            // Keep only last 20 updates
            while (updatesContainer.children.length > 20) {
                updatesContainer.removeChild(updatesContainer.lastChild);
            }
        }
        
        // Start connection
        connect();
    </script>
</body>
</html>
"""

def handle_shutdown(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Run the server
    uvicorn.run(
        "main:app",
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        log_level=config.LOG_LEVEL.lower(),
        reload=False
    )