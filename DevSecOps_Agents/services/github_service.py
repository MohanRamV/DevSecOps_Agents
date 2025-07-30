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
    """
    def get_jobs_for_run(self, run):
        workflow_run = self.repo.get_workflow_run(run.id)
        return workflow_run.get_jobs()
    """

    def get_workflow_run_details(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific workflow run"""
        try:
            run = self.repo.get_workflow_run(run_id)
            
            # Get jobs for this run with robust error handling
            jobs = self._get_workflow_jobs(run)
            
            # Get artifacts with error handling
            artifacts = self._get_workflow_artifacts(run)
            
            # Get run details with safe attribute access
            run_details = self._extract_run_details(run, jobs, artifacts)
            
            return run_details
            
        except GithubException as e:
            logger.error(f"Error fetching workflow run details: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_workflow_run_details: {e}")
            return None
    
    def _get_workflow_jobs(self, run) -> List[Dict[str, Any]]:
        """Get jobs for a workflow run with robust error handling"""
        jobs = []
        try:
            # The correct method is to use the 'jobs' attribute on the WorkflowRun object
            if hasattr(run, 'jobs'):
                try:
                    # Check if jobs is a method or property
                    jobs_attr = getattr(run, 'jobs')
                    if callable(jobs_attr):
                        # It's a method, call it
                        job_list = jobs_attr()
                        logger.debug(f"Using run.jobs() method for run {run.id}")
                    else:
                        # It's a property, use it directly
                        job_list = jobs_attr
                        logger.debug(f"Using run.jobs property for run {run.id}")
                    
                    # Process each job
                    for job in job_list:
                        try:
                            job_data = self._extract_job_details(job)
                            jobs.append(job_data)
                        except Exception as e:
                            logger.warning(f"Error processing job in run {run.id}: {e}")
                            continue
                    
                    logger.info(f"Successfully retrieved {len(jobs)} jobs for run {run.id}")
                    
                except Exception as e:
                    logger.error(f"Failed to get jobs for run {run.id}: {e}")
            else:
                logger.warning(f"WorkflowRun object does not have 'jobs' attribute for run {run.id}")
                    
        except Exception as e:
            logger.error(f"Could not fetch jobs for run {run.id}: {e}")
        
        return jobs
    
    def _extract_job_details(self, job) -> Dict[str, Any]:
        """Extract details from a job object with safe attribute access"""
        try:
            job_data = {
                "id": getattr(job, 'id', None),
                "name": getattr(job, 'name', None),
                "status": getattr(job, 'status', None),
                "conclusion": getattr(job, 'conclusion', None),
                "started_at": None,
                "completed_at": None,
                "duration": None,
                "steps": []
            }
            
            # Handle datetime fields safely
            started_at = getattr(job, 'started_at', None)
            completed_at = getattr(job, 'completed_at', None)
            
            if started_at and hasattr(started_at, 'isoformat'):
                job_data["started_at"] = started_at.isoformat()
            
            if completed_at and hasattr(completed_at, 'isoformat'):
                job_data["completed_at"] = completed_at.isoformat()
            
            # Calculate duration if we have both times
            if job_data["started_at"] and job_data["completed_at"]:
                try:
                    from datetime import datetime
                    start_dt = datetime.fromisoformat(job_data["started_at"].replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(job_data["completed_at"].replace('Z', '+00:00'))
                    job_data["duration"] = (end_dt - start_dt).total_seconds()
                except Exception as e:
                    logger.debug(f"Could not calculate job duration: {e}")
            
            # Get steps for this job
            try:
                if hasattr(job, 'get_steps'):
                    steps = job.get_steps()
                    for step in steps:
                        step_data = {
                            "name": getattr(step, 'name', None),
                            "status": getattr(step, 'status', None),
                            "conclusion": getattr(step, 'conclusion', None),
                            "started_at": getattr(step, 'started_at', None),
                            "completed_at": getattr(step, 'completed_at', None),
                            "number": getattr(step, 'number', None)
                        }
                        
                        # Convert datetime fields
                        for time_field in ['started_at', 'completed_at']:
                            if step_data[time_field] and hasattr(step_data[time_field], 'isoformat'):
                                step_data[time_field] = step_data[time_field].isoformat()
                        
                        job_data["steps"].append(step_data)
            except Exception as e:
                logger.debug(f"Could not get steps for job: {e}")
            
            return job_data
            
        except Exception as e:
            logger.warning(f"Error extracting job details: {e}")
            return {"id": None, "name": "Unknown", "status": "unknown", "steps": []}
    
    def _get_workflow_artifacts(self, run) -> List[Dict[str, Any]]:
        """Get artifacts for a workflow run with error handling"""
        artifacts = []
        try:
            if hasattr(run, 'get_artifacts'):
                for artifact in run.get_artifacts():
                    try:
                        artifact_data = {
                            "id": getattr(artifact, 'id', None),
                            "name": getattr(artifact, 'name', None),
                            "size_in_bytes": getattr(artifact, 'size_in_bytes', None),
                            "created_at": None,
                            "expires_at": None
                        }
                        
                        # Handle datetime fields
                        created_at = getattr(artifact, 'created_at', None)
                        expires_at = getattr(artifact, 'expires_at', None)
                        
                        if created_at and hasattr(created_at, 'isoformat'):
                            artifact_data["created_at"] = created_at.isoformat()
                        
                        if expires_at and hasattr(expires_at, 'isoformat'):
                            artifact_data["expires_at"] = expires_at.isoformat()
                        
                        artifacts.append(artifact_data)
                    except Exception as e:
                        logger.debug(f"Error processing artifact: {e}")
                        continue
        except Exception as e:
            logger.warning(f"Could not fetch artifacts for run {run.id}: {e}")
        
        return artifacts
    
    def _extract_run_details(self, run, jobs: List[Dict[str, Any]], artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract run details with safe attribute access"""
        try:
            # Try different attribute names for start/end times
            started_at = None
            completed_at = None
            
            # Try common attribute names for start time
            for attr_name in ['run_started_at', 'started_at', 'created_at']:
                if hasattr(run, attr_name):
                    started_at = getattr(run, attr_name)
                    break
            
            # Try common attribute names for completion time
            for attr_name in ['run_completed_at', 'completed_at', 'updated_at']:
                if hasattr(run, attr_name):
                    completed_at = getattr(run, attr_name)
                    break
            
            run_details = {
                "id": getattr(run, 'id', None),
                "name": getattr(run, 'name', None),
                "status": getattr(run, 'status', None),
                "conclusion": getattr(run, 'conclusion', None),
                "created_at": getattr(run, 'created_at', None),
                "updated_at": getattr(run, 'updated_at', None),
                "started_at": started_at,
                "completed_at": completed_at,
                "branch": getattr(run, 'head_branch', None),
                "commit_sha": getattr(run, 'head_sha', None),
                "commit_message": None,
                "actor": None,
                "jobs": jobs,
                "artifacts": artifacts,
                "logs_url": getattr(run, 'logs_url', None),
                "html_url": getattr(run, 'html_url', None)
            }
            
            # Handle commit message safely
            if hasattr(run, 'head_commit') and run.head_commit:
                run_details["commit_message"] = getattr(run.head_commit, 'message', None)
            
            # Handle actor safely
            if hasattr(run, 'actor') and run.actor:
                run_details["actor"] = getattr(run.actor, 'login', None)
            
            # Convert datetime objects to ISO format
            for key in ['created_at', 'updated_at', 'started_at', 'completed_at']:
                if run_details[key] and hasattr(run_details[key], 'isoformat'):
                    run_details[key] = run_details[key].isoformat()
            
            # Calculate duration if we have both start and end times
            if run_details["started_at"] and run_details["completed_at"]:
                try:
                    from datetime import datetime
                    start_dt = datetime.fromisoformat(run_details["started_at"].replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(run_details["completed_at"].replace('Z', '+00:00'))
                    run_details["duration"] = (end_dt - start_dt).total_seconds()
                except Exception as e:
                    logger.debug(f"Could not calculate duration: {e}")
                    run_details["duration"] = None
            else:
                run_details["duration"] = None
            
            return run_details
            
        except Exception as e:
            logger.error(f"Error extracting run details: {e}")
            return {
                "id": getattr(run, 'id', None),
                "name": getattr(run, 'name', None),
                "status": "unknown",
                "jobs": jobs,
                "artifacts": artifacts
            }
    
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