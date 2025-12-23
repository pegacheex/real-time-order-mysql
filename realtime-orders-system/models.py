"""Data models for the real-time orders system."""

from datetime import datetime
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
import json

class Order(BaseModel):
    """Order data model."""
    id: int
    customer_name: str
    product_name: str
    status: Literal['pending', 'shipped', 'delivered']
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class OrderChange(BaseModel):
    """Order change event model."""
    id: int
    order_id: int
    operation_type: Literal['INSERT', 'UPDATE', 'DELETE']
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    changed_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'OrderChange':
        """Create OrderChange from database row."""
        return cls(
            id=row['id'],
            order_id=row['order_id'],
            operation_type=row['operation_type'],
            old_data=json.loads(row['old_data']) if row['old_data'] else None,
            new_data=json.loads(row['new_data']) if row['new_data'] else None,
            changed_at=row['changed_at']
        )

class WebSocketMessage(BaseModel):
    """WebSocket message model."""
    type: Literal['order_change', 'initial_data', 'heartbeat', 'error']
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class OrderChangeNotification(BaseModel):
    """Order change notification for WebSocket clients."""
    change_id: int
    order_id: int
    operation: Literal['INSERT', 'UPDATE', 'DELETE']
    order_data: Optional[Order] = None
    previous_data: Optional[Dict[str, Any]] = None
    timestamp: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }