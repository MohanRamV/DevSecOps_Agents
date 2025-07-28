import os
import json
import hmac
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from github import Github, GithubException
from github.WorkflowRun import WorkflowRun
from github.Repository import Repository
from github.Commit import Commit
from loguru import logger

from config.config import get_config
from models.database import PipelineRun, get_db

class GitHubService:
    """Service for interacting with GitHub API"""
    
    def __init__(self):
        self.config = get_config()
        token = self.config.github.get_token()
        if not token:
            raise ValueError("GitHub token not configured. Please run setup_credentials.py first.")
        
        self.github = Github(token)
        
        # Get repository info using getter methods
        repository = self.config.github.get_repository()
        owner = self.config.github.get_owner()
        
        if not repository or not owner:
            raise ValueError("GitHub repository and owner not configured. Please run setup_credentials.py first.")
        
        self.repo = self.github.get_repo(f"{repository}")
        
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature"""
        if not self.config.github.webhook_secret:
            logger.warning("No webhook secret configured, skipping signature verification")
            return True
            
        expected_signature = hmac.new(
            self.config.github.webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
    
    def get_workflow_runs(self, branch: Optional[str] = None, status: Optional[str] = None, 
                         limit: int = 50) -> List[WorkflowRun]:
        """Get workflow runs from GitHub"""
        try:
            if branch and status:
                runs = self.repo.get_workflow_runs(branch=branch, status=status)
            elif branch:
                runs = self.repo.get_workflow_runs(branch=branch)
            elif status:
                runs = self.repo.get_workflow_runs(status=status)
            else:
                runs = self.repo.get_workflow_runs()
            
            return list(runs[:limit])
        except GithubException as e:
            logger.error(f"Error fetching workflow runs: {e}")
            return []
    
    def get_jobs_for_run(self, run):
        workflow_run = self.repo.get_workflow_run(run.id)
        return workflow_run.get_jobs()


    def get_workflow_run_details(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific workflow run"""
        try:
            run = self.repo.get_workflow_run(run_id)
            
            # Get jobs for this run
            jobs = []
            for job in self.get_jobs_for_run(run):
                job_data = {
                    "id": job.id,
                    "name": job.name,
                    "status": job.status,
                    "conclusion": job.conclusion,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "duration": (job.completed_at - job.started_at).total_seconds() if job.started_at and job.completed_at else None,
                    "steps": []
                }
                
                # Get steps for this job
                for step in job.get_steps():
                    step_data = {
                        "name": step.name,
                        "status": step.status,
                        "conclusion": step.conclusion,
                        "started_at": step.started_at.isoformat() if step.started_at else None,
                        "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                        "number": step.number
                    }
                    job_data["steps"].append(step_data)
                
                jobs.append(job_data)
            
            # Get artifacts
            artifacts = []
            for artifact in run.get_artifacts():
                artifact_data = {
                    "id": artifact.id,
                    "name": artifact.name,
                    "size_in_bytes": artifact.size_in_bytes,
                    "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
                    "expires_at": artifact.expires_at.isoformat() if artifact.expires_at else None
                }
                artifacts.append(artifact_data)
            
            return {
                "id": run.id,
                "name": run.name,
                "status": run.status,
                "conclusion": run.conclusion,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "updated_at": run.updated_at.isoformat() if run.updated_at else None,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "duration": (run.completed_at - run.started_at).total_seconds() if run.started_at and run.completed_at else None,
                "branch": run.head_branch,
                "commit_sha": run.head_sha,
                "commit_message": run.head_commit.message if run.head_commit else None,
                "actor": run.actor.login if run.actor else None,
                "jobs": jobs,
                "artifacts": artifacts,
                "logs_url": run.logs_url,
                "html_url": run.html_url
            }
        except GithubException as e:
            logger.error(f"Error fetching workflow run details: {e}")
            return None
    
    def get_repository_stats(self) -> Optional[Dict[str, Any]]:
        """Get repository statistics"""
        try:
            return {
                "name": self.repo.name,
                "full_name": self.repo.full_name,
                "description": self.repo.description,
                "language": self.repo.language,
                "stars": self.repo.stargazers_count,
                "forks": self.repo.forks_count,
                "open_issues": self.repo.open_issues_count,
                "default_branch": self.repo.default_branch,
                "created_at": self.repo.created_at.isoformat() if self.repo.created_at else None,
                "updated_at": self.repo.updated_at.isoformat() if self.repo.updated_at else None
            }
        except GithubException as e:
            logger.error(f"Error fetching repository stats: {e}")
            return None
    
    def get_commit_details(self, commit_sha: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a commit"""
        try:
            commit = self.repo.get_commit(commit_sha)
            return {
                "sha": commit.sha,
                "message": commit.commit.message,
                "author": {
                    "name": commit.commit.author.name,
                    "email": commit.commit.author.email,
                    "date": commit.commit.author.date.isoformat() if commit.commit.author.date else None
                },
                "committer": {
                    "name": commit.commit.committer.name,
                    "email": commit.commit.committer.email,
                    "date": commit.commit.committer.date.isoformat() if commit.commit.committer.date else None
                },
                "files_changed": len(commit.files),
                "additions": commit.stats.additions,
                "deletions": commit.stats.deletions,
                "total": commit.stats.total
            }
        except GithubException as e:
            logger.error(f"Error fetching commit details: {e}")
            return None
    
    def create_issue(self, title: str, body: str, labels: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Create a GitHub issue"""
        try:
            issue = self.repo.create_issue(
                title=title,
                body=body,
                labels=labels or []
            )
            return {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body,
                "state": issue.state,
                "html_url": issue.html_url,
                "created_at": issue.created_at.isoformat() if issue.created_at else None
            }
        except GithubException as e:
            logger.error(f"Error creating GitHub issue: {e}")
            return None
    
    def update_issue(self, issue_number: int, title: Optional[str] = None, 
                    body: Optional[str] = None, state: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Update a GitHub issue"""
        try:
            issue = self.repo.get_issue(issue_number)
            
            if title:
                issue.edit(title=title)
            if body:
                issue.edit(body=body)
            if state:
                issue.edit(state=state)
            
            return {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body,
                "state": issue.state,
                "html_url": issue.html_url,
                "updated_at": issue.updated_at.isoformat() if issue.updated_at else None
            }
        except GithubException as e:
            logger.error(f"Error updating GitHub issue: {e}")
            return None
    
    def get_pull_requests(self, state: str = "open", limit: int = 20) -> List[Dict[str, Any]]:
        """Get pull requests from the repository"""
        try:
            prs = self.repo.get_pulls(state=state)[:limit]
            return [
                {
                    "id": pr.id,
                    "number": pr.number,
                    "title": pr.title,
                    "body": pr.body,
                    "state": pr.state,
                    "head_branch": pr.head.ref,
                    "base_branch": pr.base.ref,
                    "created_at": pr.created_at.isoformat() if pr.created_at else None,
                    "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
                    "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                    "author": pr.user.login if pr.user else None,
                    "url": pr.html_url
                }
                for pr in prs
            ]
        except GithubException as e:
            logger.error(f"Error fetching pull requests: {e}")
            return []
    
    def get_workflow_run_logs(self, run_id: int) -> Optional[str]:
        """Get logs for a specific workflow run"""
        try:
            run = self.repo.get_workflow_run(run_id)
            # Note: This would require additional permissions and handling
            # For now, return the logs URL
            return run.logs_url
        except GithubException as e:
            logger.error(f"Error fetching workflow run logs: {e}")
            return None