import asyncio
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from config.config import get_config
from models.database import AgentAction, SessionLocal

class BaseAgent(ABC):
    """Base class for all monitoring agents"""
    
    def __init__(self, name: str):
        self.name = name
        self.config = get_config()
        self.start_time = None
        self.end_time = None
        
    @abstractmethod
    async def run(self) -> Dict[str, Any]:
        """Main entry point for the agent"""
        pass
    
    async def execute(self) -> Dict[str, Any]:
        """Execute the agent with proper logging and error handling"""
        self.start_time = datetime.utcnow()
        logger.info(f"Starting {self.name}...")
        
        try:
            result = await self.run()
            self.end_time = datetime.utcnow()
            
            # Log success
            logger.info(f"{self.name} completed successfully")
            
            # Store agent action
            await self._store_agent_action("completed", result)
            
            return result
            
        except Exception as e:
            self.end_time = datetime.utcnow()
            logger.error(f"Error in {self.name}: {e}")
            
            # Store error action
            error_result = {
                "error": str(e),
                "status": "failed"
            }
            await self._store_agent_action("failed", error_result)
            
            return error_result
    
    async def _store_agent_action(self, status: str, result: Dict[str, Any]) -> None:
        """Store agent action in database"""
        try:
            db = SessionLocal()
            action = AgentAction(
                agent_name=self.name,
                action_type="monitoring",
                action_data={
                    "start_time": self.start_time.isoformat() if self.start_time else None,
                    "end_time": self.end_time.isoformat() if self.end_time else None,
                    "duration": (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else None
                },
                status=status,
                result=result,
                executed_at=datetime.utcnow()
            )
            
            db.add(action)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error storing agent action: {e}")
            if db:
                db.rollback()
        finally:
            if db:
                db.close()
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the agent"""
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "description": self.__doc__ or "No description available",
            "config": {
                "environment": self.config.environment,
                "debug": self.config.debug
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check for the agent"""
        try:
            # Basic health check
            health_status = {
                "agent_name": self.name,
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "checks": {}
            }
            
            # Add specific health checks here
            health_status["checks"]["config_loaded"] = self.config is not None
            health_status["checks"]["agent_initialized"] = True
            
            return health_status
            
        except Exception as e:
            return {
                "agent_name": self.name,
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            } 