from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json

from config.config import get_config

Base = declarative_base()

class PipelineRun(Base):
    """Model for storing CI/CD pipeline run information"""
    __tablename__ = "pipeline_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, unique=True, index=True)  # GitHub Actions run ID
    workflow_name = Column(String, index=True)
    status = Column(String)  # success, failure, cancelled, etc.
    conclusion = Column(String)  # success, failure, cancelled, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration = Column(Float)  # in seconds
    branch = Column(String)
    commit_sha = Column(String)
    commit_message = Column(Text)
    actor = Column(String)
    jobs_data = Column(JSON)  # Store detailed job information
    artifacts = Column(JSON)  # Store artifact information
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "workflow_name": self.workflow_name,
            "status": self.status,
            "conclusion": self.conclusion,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "commit_message": self.commit_message,
            "actor": self.actor,
            "jobs_data": self.jobs_data,
            "artifacts": self.artifacts
        }

class PipelineIssue(Base):
    """Model for storing identified pipeline issues"""
    __tablename__ = "pipeline_issues"
    
    id = Column(Integer, primary_key=True, index=True)
    pipeline_run_id = Column(Integer, index=True)
    issue_type = Column(String)  # test_failure, build_failure, security_vulnerability, etc.
    severity = Column(String)  # low, medium, high, critical
    title = Column(String)
    description = Column(Text)
    detected_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    status = Column(String, default="open")  # open, investigating, resolved, false_positive
    affected_jobs = Column(JSON)
    error_logs = Column(Text)
    suggested_fixes = Column(JSON)
    ai_analysis = Column(Text)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "pipeline_run_id": self.pipeline_run_id,
            "issue_type": self.issue_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "status": self.status,
            "affected_jobs": self.affected_jobs,
            "error_logs": self.error_logs,
            "suggested_fixes": self.suggested_fixes,
            "ai_analysis": self.ai_analysis
        }

class AgentAction(Base):
    """Model for storing agent actions and recommendations"""
    __tablename__ = "agent_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String, index=True)
    action_type = Column(String)  # alert, fix_suggestion, auto_fix, analysis
    pipeline_run_id = Column(Integer, index=True)
    issue_id = Column(Integer, index=True)
    action_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime)
    status = Column(String, default="pending")  # pending, executed, failed, cancelled
    result = Column(JSON)
    error_message = Column(Text)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "action_type": self.action_type,
            "pipeline_run_id": self.pipeline_run_id,
            "issue_id": self.issue_id,
            "action_data": self.action_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "status": self.status,
            "result": self.result,
            "error_message": self.error_message
        }

class Deployment(Base):
    """Model for storing deployment information"""
    __tablename__ = "deployments"
    
    id = Column(Integer, primary_key=True, index=True)
    deployment_name = Column(String, index=True)
    namespace = Column(String)
    image_tag = Column(String)
    status = Column(String)  # running, failed, pending, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    replicas = Column(Integer)
    available_replicas = Column(Integer)
    ready_replicas = Column(Integer)
    pipeline_run_id = Column(Integer, index=True)
    kubernetes_data = Column(JSON)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "deployment_name": self.deployment_name,
            "namespace": self.namespace,
            "image_tag": self.image_tag,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "replicas": self.replicas,
            "available_replicas": self.available_replicas,
            "ready_replicas": self.ready_replicas,
            "pipeline_run_id": self.pipeline_run_id,
            "kubernetes_data": self.kubernetes_data
        }

class Notification(Base):
    """Model for storing notification history"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    notification_type = Column(String)  # slack, email, teams, etc.
    recipient = Column(String)
    subject = Column(String)
    message = Column(Text)
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String)  # sent, failed, pending
    error_message = Column(Text)
    related_issue_id = Column(Integer, index=True)
    related_action_id = Column(Integer, index=True)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "notification_type": self.notification_type,
            "recipient": self.recipient,
            "subject": self.subject,
            "message": self.message,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "status": self.status,
            "error_message": self.error_message,
            "related_issue_id": self.related_issue_id,
            "related_action_id": self.related_action_id
        }

# Database session management
config = get_config()
engine = create_engine(config.database.url, echo=config.database.echo)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def cleanup_old_data():
    """Clean up old data based on retention policy"""
    db = SessionLocal()
    try:
        retention_date = datetime.utcnow() - timedelta(days=config.monitoring.retention_days)
        
        # Clean up old pipeline runs
        db.query(PipelineRun).filter(PipelineRun.created_at < retention_date).delete()
        
        # Clean up old issues
        db.query(PipelineIssue).filter(PipelineIssue.detected_at < retention_date).delete()
        
        # Clean up old agent actions
        db.query(AgentAction).filter(AgentAction.created_at < retention_date).delete()
        
        # Clean up old notifications
        db.query(Notification).filter(Notification.sent_at < retention_date).delete()
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close() 