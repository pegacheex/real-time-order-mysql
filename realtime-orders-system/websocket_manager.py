"""WebSocket connection manager for real-time client communication."""

import asyncio
import json
import logging
from typing import Set, Dict, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

from models import WebSocketMessage, OrderChangeNotification, Order
from database.connection import db_manager

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections and broadcasts."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        # Store connection info
        self.connection_info[websocket] = {
            'connected_at': datetime.utcnow(),
            'client_info': websocket.headers.get('user-agent', 'Unknown')
        }
        
        logger.info(f"New WebSocket connection. Total connections: {len(self.active_connections)}")
        
        # Send initial data to the new client
        await self._send_initial_data(websocket)
    
    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.connection_info.pop(websocket, None)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast_change(self, notification: OrderChangeNotification) -> None:
        """Broadcast an order change to all connected clients."""
        if not self.active_connections:
            return
        
        message = WebSocketMessage(
            type="order_change",
            data={
                "change_id": notification.change_id,
                "order_id": notification.order_id,
                "operation": notification.operation,
                "order_data": notification.order_data.dict() if notification.order_data else None,
                "previous_data": notification.previous_data,
                "timestamp": notification.timestamp.isoformat()
            }
        )
        
        await self._broadcast_message(message)
        logger.info(f"Broadcasted {notification.operation} for order {notification.order_id} to {len(self.active_connections)} clients")
    
    async def send_heartbeat(self) -> None:
        """Send heartbeat to all connected clients."""
        if not self.active_connections:
            return
        
        message = WebSocketMessage(
            type="heartbeat",
            data={"server_time": datetime.utcnow().isoformat()}
        )
        
        await self._broadcast_message(message)
    
    async def _send_initial_data(self, websocket: WebSocket) -> None:
        """Send initial orders data to a newly connected client."""
        try:
            orders = await db_manager.get_all_orders()
            
            # Convert datetime objects to ISO format
            orders_data = []
            for order in orders:
                order_dict = dict(order)
                for key, value in order_dict.items():
                    if isinstance(value, datetime):
                        order_dict[key] = value.isoformat()
                orders_data.append(order_dict)
            
            message = WebSocketMessage(
                type="initial_data",
                data={"orders": orders_data}
            )
            
            await self._send_message(websocket, message)
            logger.debug(f"Sent initial data with {len(orders)} orders to new client")
            
        except Exception as e:
            logger.error(f"Error sending initial data: {e}")
            error_message = WebSocketMessage(
                type="error",
                data={"message": "Failed to load initial data"}
            )
            await self._send_message(websocket, error_message)
    
    async def _broadcast_message(self, message: WebSocketMessage) -> None:
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return
        
        message_json = message.json()
        disconnected_clients = set()
        
        # Send to all clients concurrently
        tasks = []
        for websocket in self.active_connections.copy():
            task = asyncio.create_task(self._send_message_safe(websocket, message_json, disconnected_clients))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Clean up disconnected clients
        for websocket in disconnected_clients:
            self.disconnect(websocket)
    
    async def _send_message(self, websocket: WebSocket, message: WebSocketMessage) -> None:
        """Send a message to a specific WebSocket."""
        await websocket.send_text(message.json())
    
    async def _send_message_safe(self, websocket: WebSocket, message_json: str, disconnected_clients: Set[WebSocket]) -> None:
        """Safely send a message, handling disconnections."""
        try:
            await websocket.send_text(message_json)
        except WebSocketDisconnect:
            disconnected_clients.add(websocket)
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {e}")
            disconnected_clients.add(websocket)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about current connections."""
        return {
            "total_connections": len(self.active_connections),
            "connections": [
                {
                    "connected_at": info["connected_at"].isoformat(),
                    "client_info": info["client_info"]
                }
                for info in self.connection_info.values()
            ]
        }

# Global WebSocket manager instance
websocket_manager = WebSocketManager()