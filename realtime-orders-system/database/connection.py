"""Database connection and management utilities."""

import asyncio
import logging
from typing import Optional, Dict, Any, List
import aiomysql
from config import config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        self.pool: Optional[aiomysql.Pool] = None
        self._connection_params = {
            'host': config.DB_HOST,
            'port': config.DB_PORT,
            'user': config.DB_USER,
            'password': config.DB_PASSWORD,
            'db': config.DB_NAME,
            'charset': 'utf8mb4',
            'autocommit': True
        }
    
    async def initialize(self) -> None:
        """Initialize the database connection pool."""
        try:
            self.pool = await aiomysql.create_pool(
                minsize=5,
                maxsize=20,
                **self._connection_params
            )
            logger.info("Database connection pool initialized")
            
            # Test connection
            await self.health_check()
            
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def close(self) -> None:
        """Close the database connection pool."""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("Database connection pool closed")
    
    async def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
                    result = await cursor.fetchone()
                    return result[0] == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results."""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchall()
    
    async def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                return cursor.rowcount
    
    async def get_unprocessed_changes(self) -> List[Dict[str, Any]]:
        """Fetch unprocessed changes from the change log."""
        query = """
        SELECT id, order_id, operation_type, old_data, new_data, changed_at
        FROM order_changes 
        WHERE processed = FALSE 
        ORDER BY changed_at ASC, id ASC
        LIMIT 100
        """
        return await self.execute_query(query)
    
    async def mark_changes_processed(self, change_ids: List[int]) -> None:
        """Mark changes as processed."""
        if not change_ids:
            return
        
        placeholders = ','.join(['%s'] * len(change_ids))
        query = f"UPDATE order_changes SET processed = TRUE WHERE id IN ({placeholders})"
        await self.execute_update(query, tuple(change_ids))
        
        logger.debug(f"Marked {len(change_ids)} changes as processed")
    
    async def get_order_by_id(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific order by ID."""
        query = "SELECT * FROM orders WHERE id = %s"
        results = await self.execute_query(query, (order_id,))
        return results[0] if results else None
    
    async def get_all_orders(self) -> List[Dict[str, Any]]:
        """Get all orders."""
        query = "SELECT * FROM orders ORDER BY updated_at DESC"
        return await self.execute_query(query)

# Global database manager instance
db_manager = DatabaseManager()