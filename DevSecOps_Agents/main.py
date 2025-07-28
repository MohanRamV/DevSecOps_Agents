import asyncio
import uvicorn
import sys
import logging
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager

from config.config import get_config
from models.database import init_db, get_db, cleanup_old_data
from agents.pipeline_monitor_agent import PipelineMonitorAgent
from agents.deployment_monitor_agent import DeploymentMonitorAgent
from agents.notification_agent import NotificationAgent
from services.github_service import GitHubService

# Configure logging with better error handling
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('devsecops_monitor.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Suppress specific Windows asyncio errors
logging.getLogger('asyncio').setLevel(logging.WARNING)

# Windows-specific asyncio policy fix
if sys.platform.startswith('win'):
    # Use SelectorEventLoop on Windows to avoid ProactorEventLoop issues
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Alternative: Use ProactorEventLoop but with better error handling
    # asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Global variables for agents and monitoring task
pipeline_agent = None
deployment_agent = None
notification_agent = None
monitoring_task = None

class SafeBackgroundTasks:
    """Wrapper for background tasks with better error handling"""
    
    @staticmethod
    async def safe_execute(func, *args, **kwargs):
        """Execute function with proper error handling"""
        try:
            if asyncio.iscoroutinefunction(func):
                await func(*args, **kwargs)
            else:
                func(*args, **kwargs)
        except ConnectionResetError:
            # Ignore connection reset errors
            pass
        except Exception as e:
            logger.error(f"Error in background task {func.__name__}: {e}")

async def run_scheduled_monitoring():
    """Run scheduled monitoring tasks with enhanced error handling"""
    global pipeline_agent, deployment_agent, notification_agent
    
    config = get_config()
    logger.info("Starting scheduled monitoring loop...")
    
    retry_count = 0
    max_retries = 3
    
    while True:
        try:
            logger.debug("Running scheduled monitoring cycle...")
            
            # Create tasks with proper error handling
            tasks = []
            
            if pipeline_agent:
                tasks.append(SafeBackgroundTasks.safe_execute(pipeline_agent.execute))
            
            if deployment_agent:
                tasks.append(SafeBackgroundTasks.safe_execute(deployment_agent.execute))
            
            if notification_agent:
                tasks.append(SafeBackgroundTasks.safe_execute(notification_agent.execute))
            
            if tasks:
                # Run all monitoring agents with timeout
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=300  # 5 minute timeout
                    )
                    retry_count = 0  # Reset retry count on success
                except asyncio.TimeoutError:
                    logger.warning("Monitoring cycle timed out")
                except ConnectionResetError:
                    # Ignore connection reset errors
                    pass
            
            # Wait for next cycle
            await asyncio.sleep(config.monitoring.check_interval)
            
        except ConnectionResetError:
            # Ignore connection reset errors and continue
            logger.debug("Connection reset error in monitoring loop (ignored)")
            await asyncio.sleep(5)
        except Exception as e:
            retry_count += 1
            logger.error(f"Error in scheduled monitoring (attempt {retry_count}): {e}")
            
            if retry_count >= max_retries:
                logger.error("Max retries reached, waiting longer before retry")
                await asyncio.sleep(300)  # Wait 5 minutes
                retry_count = 0
            else:
                await asyncio.sleep(60)  # Wait 1 minute before retrying

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifespan events with enhanced error handling"""
    global pipeline_agent, deployment_agent, notification_agent, monitoring_task
    
    # Startup
    logger.info("Starting DevSecOps AI Monitoring System...")
    
    try:
        # Initialize database
        init_db()
        logger.info("Database initialized")
        
        # Clean up old data
        cleanup_old_data()
        logger.info("Old data cleanup completed")
        
        # Initialize agent instances with individual error handling
        agents_initialized = []
        
        try:
            pipeline_agent = PipelineMonitorAgent()
            agents_initialized.append("pipeline_monitor")
            logger.info("Pipeline monitor agent initialized")
        except Exception as e:
            logger.error(f"Failed to initialize pipeline agent: {e}")
            pipeline_agent = None
        
        try:
            deployment_agent = DeploymentMonitorAgent()
            agents_initialized.append("deployment_monitor")
            logger.info("Deployment monitor agent initialized")
        except Exception as e:
            logger.error(f"Failed to initialize deployment agent: {e}")
            deployment_agent = None
        
        try:
            notification_agent = NotificationAgent()
            agents_initialized.append("notification")
            logger.info("Notification agent initialized")
        except Exception as e:
            logger.error(f"Failed to initialize notification agent: {e}")
            notification_agent = None
        
        logger.info(f"Agents initialized: {', '.join(agents_initialized) if agents_initialized else 'None'}")
        
        # Start scheduled monitoring if at least one agent is available
        if any([pipeline_agent, deployment_agent, notification_agent]):
            monitoring_task = asyncio.create_task(run_scheduled_monitoring())
            logger.info("Scheduled monitoring started")
        else:
            logger.warning("No agents available, scheduled monitoring disabled")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down DevSecOps AI Monitoring System...")
    try:
        if monitoring_task and not monitoring_task.done():
            monitoring_task.cancel()
            try:
                await asyncio.wait_for(monitoring_task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except ConnectionResetError:
                pass  # Ignore connection reset during shutdown
        logger.info("Shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="DevSecOps AI Monitoring System",
    description="Intelligent CI/CD pipeline monitoring and issue detection",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware with better configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.exception_handler(ConnectionResetError)
async def connection_reset_handler(request, exc):
    """Handle connection reset errors gracefully"""
    logger.debug("Connection reset error handled")
    return {"error": "Connection reset", "status": "handled"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "DevSecOps AI Monitoring System",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "platform": sys.platform
    }

@app.get("/health")
async def health_check():
    """Health check endpoint with enhanced agent status"""
    try:
        agents_status = {}
        overall_health = "healthy"
        
        # Check agent health if they exist
        for agent_name, agent in [
            ("pipeline_monitor", pipeline_agent),
            ("deployment_monitor", deployment_agent),
            ("notification", notification_agent)
        ]:
            if agent:
                try:
                    # Add timeout to health checks
                    health_result = await asyncio.wait_for(
                        agent.health_check(), 
                        timeout=10.0
                    )
                    agents_status[agent_name] = health_result
                except asyncio.TimeoutError:
                    agents_status[agent_name] = {"status": "timeout"}
                    overall_health = "degraded"
                except ConnectionResetError:
                    agents_status[agent_name] = {"status": "connection_reset"}
                    overall_health = "degraded"
                except Exception as e:
                    agents_status[agent_name] = {"status": "error", "error": str(e)}
                    overall_health = "degraded"
            else:
                agents_status[agent_name] = {"status": "not_initialized"}
                overall_health = "degraded"
        
        return {
            "status": overall_health,
            "timestamp": datetime.utcnow().isoformat(),
            "agents": agents_status,
            "monitoring_task_running": monitoring_task is not None and not monitoring_task.done() if monitoring_task else False
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.post("/monitor/pipeline")
async def monitor_pipeline(background_tasks: BackgroundTasks):
    """Trigger pipeline monitoring"""
    if not pipeline_agent:
        raise HTTPException(status_code=503, detail="Pipeline agent not initialized")
        
    try:
        background_tasks.add_task(SafeBackgroundTasks.safe_execute, pipeline_agent.execute)
        return {
            "message": "Pipeline monitoring started",
            "status": "triggered",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error triggering pipeline monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/monitor/deployment")
async def monitor_deployment(background_tasks: BackgroundTasks):
    """Trigger deployment monitoring"""
    if not deployment_agent:
        raise HTTPException(status_code=503, detail="Deployment agent not initialized")
        
    try:
        background_tasks.add_task(SafeBackgroundTasks.safe_execute, deployment_agent.execute)
        return {
            "message": "Deployment monitoring started",
            "status": "triggered",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error triggering deployment monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/notify")
async def send_notifications(background_tasks: BackgroundTasks):
    """Trigger notification sending"""
    if not notification_agent:
        raise HTTPException(status_code=503, detail="Notification agent not initialized")
        
    try:
        background_tasks.add_task(SafeBackgroundTasks.safe_execute, notification_agent.execute)
        return {
            "message": "Notification sending started",
            "status": "triggered",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error triggering notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/monitor/all")
async def monitor_all(background_tasks: BackgroundTasks):
    """Trigger all monitoring agents"""
    available_agents = []
    
    if pipeline_agent:
        background_tasks.add_task(SafeBackgroundTasks.safe_execute, pipeline_agent.execute)
        available_agents.append("pipeline_monitor")
    
    if deployment_agent:
        background_tasks.add_task(SafeBackgroundTasks.safe_execute, deployment_agent.execute)
        available_agents.append("deployment_monitor")
    
    if notification_agent:
        background_tasks.add_task(SafeBackgroundTasks.safe_execute, notification_agent.execute)
        available_agents.append("notification")
    
    if not available_agents:
        raise HTTPException(status_code=503, detail="No agents available")
    
    try:
        return {
            "message": f"Monitoring agents started: {', '.join(available_agents)}",
            "status": "triggered",
            "agents_started": available_agents,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error triggering all monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ... (Include all other endpoints from the previous version)
# For brevity, I'm including just the key endpoints. The rest remain the same.

@app.get("/issues")
async def get_issues(
    status: str = None,
    severity: str = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get pipeline issues with optional filtering"""
    try:
        from models.database import PipelineIssue
        
        query = db.query(PipelineIssue)
        
        if status:
            query = query.filter(PipelineIssue.status == status)
        if severity:
            query = query.filter(PipelineIssue.severity == severity)
        
        issues = query.order_by(PipelineIssue.detected_at.desc()).limit(limit).all()
        
        return {
            "issues": [issue.to_dict() for issue in issues],
            "count": len(issues),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching issues: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook/github")
async def github_webhook(request: dict):
    """Handle GitHub webhook events with better error handling"""
    try:
        # Process webhook based on event type
        event_type = request.get("headers", {}).get("X-GitHub-Event")
        
        if event_type == "workflow_run" and pipeline_agent:
            # Trigger pipeline monitoring safely
            asyncio.create_task(SafeBackgroundTasks.safe_execute(pipeline_agent.execute))
            return {"message": "Pipeline monitoring triggered via webhook"}
        
        elif event_type == "push" and deployment_agent:
            # Trigger deployment monitoring safely
            asyncio.create_task(SafeBackgroundTasks.safe_execute(deployment_agent.execute))
            return {"message": "Deployment monitoring triggered via webhook"}
        
        else:
            return {"message": f"Webhook received for event: {event_type}"}
            
    except Exception as e:
        logger.error(f"Error processing GitHub webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def configure_uvicorn_logging():
    """Configure uvicorn logging to reduce noise"""
    uvicorn_logger = logging.getLogger("uvicorn.access")
    uvicorn_logger.setLevel(logging.WARNING)
    
    # Reduce uvicorn error logging
    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.setLevel(logging.WARNING)

if __name__ == "__main__":
    config = get_config()
    
    # Configure logging
    configure_uvicorn_logging()
    
    # Additional Windows-specific configuration
    if sys.platform.startswith('win'):
        # Set event loop policy before running
        if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    logger.info(f"Starting server on {config.api_host}:{config.api_port}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Event loop policy: {asyncio.get_event_loop_policy().__class__.__name__}")
    
    # Start FastAPI server with optimized configuration
    uvicorn.run(
        "main:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.debug,
        access_log=False,  # Reduce log noise
        log_level="warning" if not config.debug else "info"
    )