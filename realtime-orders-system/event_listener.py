"""Event listener service for monitoring database changes."""

import asyncio
import logging
from typing import List, Callable, Awaitable
from datetime import datetime

from database.connection import db_manager
from models import OrderChange, OrderChangeNotification, Order
from config import config

logger = logging.getLogger(__name__)

class EventListener:
    """Listens for database changes and notifies subscribers."""
    
    def __init__(self):
        self.subscribers: List[Callable[[OrderChangeNotification], Awaitable[None]]] = []
        self.running = False
        self._task: asyncio.Task = None
    
    def subscribe(self, callback: Callable[[OrderChangeNotification], Awaitable[None]]) -> None:
        """Subscribe to order change notifications."""
        self.subscribers.append(callback)
        logger.info(f"New subscriber added. Total subscribers: {len(self.subscribers)}")
    
    def unsubscribe(self, callback: Callable[[OrderChangeNotification], Awaitable[None]]) -> None:
        """Unsubscribe from order change notifications."""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
            logger.info(f"Subscriber removed. Total subscribers: {len(self.subscribers)}")
    
    async def start(self) -> None:
        """Start the event listener."""
        if self.running:
            logger.warning("Event listener is already running")
            return
        
        self.running = True
        self._task = asyncio.create_task(self._listen_loop())
        logger.info("Event listener started")
    
    async def stop(self) -> None:
        """Stop the event listener."""
        if not self.running:
            return
        
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Event listener stopped")
    
    async def _listen_loop(self) -> None:
        """Main listening loop."""
        logger.info("Starting change detection loop")
        
        while self.running:
            try:
                # Fetch unprocessed changes
                changes = await db_manager.get_unprocessed_changes()
                
                if changes:
                    logger.info(f"Processing {len(changes)} new changes")
                    
                    # Process each change
                    processed_ids = []
                    for change_row in changes:
                        try:
                            change = OrderChange.from_db_row(change_row)
                            notification = await self._create_notification(change)
                            
                            # Notify all subscribers
                            await self._notify_subscribers(notification)
                            processed_ids.append(change.id)
                            
                        except Exception as e:
                            logger.error(f"Error processing change {change_row.get('id')}: {e}")
                    
                    # Mark changes as processed
                    if processed_ids:
                        await db_manager.mark_changes_processed(processed_ids)
                
                # Wait before next poll
                await asyncio.sleep(config.CHANGE_LOG_POLL_INTERVAL)
                
            except asyncio.CancelledError:
                logger.info("Event listener cancelled")
                break
            except Exception as e:
                logger.error(f"Error in event listener loop: {e}")
                await asyncio.sleep(1)  # Brief pause before retry
    
    async def _create_notification(self, change: OrderChange) -> OrderChangeNotification:
        """Create a notification from a change event."""
        order_data = None
        
        # For INSERT and UPDATE, get current order data
        if change.operation_type in ['INSERT', 'UPDATE']:
            order_row = await db_manager.get_order_by_id(change.order_id)
            if order_row:
                order_data = Order(**order_row)
        
        return OrderChangeNotification(
            change_id=change.id,
            order_id=change.order_id,
            operation=change.operation_type,
            order_data=order_data,
            previous_data=change.old_data,
            timestamp=change.changed_at
        )
    
    async def _notify_subscribers(self, notification: OrderChangeNotification) -> None:
        """Notify all subscribers of a change."""
        if not self.subscribers:
            return
        
        # Notify all subscribers concurrently
        tasks = []
        for subscriber in self.subscribers.copy():  # Copy to avoid modification during iteration
            try:
                task = asyncio.create_task(subscriber(notification))
                tasks.append(task)
            except Exception as e:
                logger.error(f"Error creating notification task: {e}")
        
        if tasks:
            # Wait for all notifications to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log any errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error notifying subscriber {i}: {result}")

# Global event listener instance
event_listener = EventListener()