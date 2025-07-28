import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy.orm import Session

from config.config import get_config
from models.database import PipelineRun, PipelineIssue, AgentAction, get_db, SessionLocal
from services.github_service import GitHubService
from services.groq_service import GroqService
from agents.base_agent import BaseAgent

class PipelineMonitorAgent(BaseAgent):
    """Agent for monitoring CI/CD pipelines and detecting issues"""
    
    def __init__(self):
        super().__init__("PipelineMonitorAgent")
        self.config = get_config()
        self.github_service = GitHubService()
        self.groq_service = GroqService()
        
    async def monitor_pipeline_runs(self) -> List[Dict[str, Any]]:
        """Monitor recent pipeline runs and detect issues"""
        logger.info("Starting pipeline monitoring...")
        
        try:
            # Get recent workflow runs
            workflow_runs = self.github_service.get_workflow_runs(limit=20)
            
            issues_found = []
            
            for run in workflow_runs:
                # Check if we already processed this run
                db = SessionLocal()
                try:
                    existing_run = db.query(PipelineRun).filter(
                        PipelineRun.run_id == str(run.id)
                    ).first()
                    
                    if existing_run:
                        logger.debug(f"Run {run.id} already processed, skipping...")
                        continue
                    
                    # Get detailed run information
                    run_details = self.github_service.get_workflow_run_details(run.id)
                    if not run_details:
                        continue
                    
                    # Store run in database
                    pipeline_run = PipelineRun(
                        run_id=str(run.id),
                        workflow_name=run.name,
                        status=run.status,
                        conclusion=run.conclusion,
                        created_at=datetime.fromisoformat(run_details["created_at"].replace('Z', '+00:00')) if run_details["created_at"] else None,
                        updated_at=datetime.fromisoformat(run_details["updated_at"].replace('Z', '+00:00')) if run_details["updated_at"] else None,
                        started_at=datetime.fromisoformat(run_details["started_at"].replace('Z', '+00:00')) if run_details["started_at"] else None,
                        completed_at=datetime.fromisoformat(run_details["completed_at"].replace('Z', '+00:00')) if run_details["completed_at"] else None,
                        duration=run_details["duration"],
                        branch=run_details["branch"],
                        commit_sha=run_details["commit_sha"],
                        commit_message=run_details["commit_message"],
                        actor=run_details["actor"],
                        jobs_data=run_details["jobs"],
                        artifacts=run_details["artifacts"]
                    )
                    
                    db.add(pipeline_run)
                    db.commit()
                    db.refresh(pipeline_run)
                    
                    # Analyze run for issues
                    issues = await self._analyze_pipeline_run(pipeline_run, run_details)
                    issues_found.extend(issues)
                    
                except Exception as e:
                    logger.error(f"Error processing run {run.id}: {e}")
                    db.rollback()
                finally:
                    db.close()
            
            logger.info(f"Pipeline monitoring completed. Found {len(issues_found)} issues.")
            return issues_found
            
        except Exception as e:
            logger.error(f"Error in pipeline monitoring: {e}")
            return []
    
    async def _analyze_pipeline_run(self, pipeline_run: PipelineRun, run_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze a pipeline run for potential issues"""
        issues = []
        
        # Check for failed runs
        if run_details["conclusion"] == "failure":
            issue = await self._analyze_failure(pipeline_run, run_details)
            if issue:
                issues.append(issue)
        
        # Check for long-running jobs
        long_running_issues = await self._check_long_running_jobs(pipeline_run, run_details)
        issues.extend(long_running_issues)
        
        # Check for security vulnerabilities
        security_issues = await self._check_security_issues(pipeline_run, run_details)
        issues.extend(security_issues)
        
        # Check for performance issues
        performance_issues = await self._check_performance_issues(pipeline_run, run_details)
        issues.extend(performance_issues)
        
        return issues
    
    async def _analyze_failure(self, pipeline_run: PipelineRun, run_details: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze a failed pipeline run"""
        try:
            # Get failed jobs
            failed_jobs = [
                job for job in run_details["jobs"]
                if job["conclusion"] == "failure"
            ]
            
            if not failed_jobs:
                return None
            
            # Prepare context for AI analysis
            context = {
                "pipeline_run": {
                    "id": pipeline_run.run_id,
                    "workflow": pipeline_run.workflow_name,
                    "branch": pipeline_run.branch,
                    "commit_sha": pipeline_run.commit_sha,
                    "commit_message": pipeline_run.commit_message,
                    "actor": pipeline_run.actor,
                    "duration": pipeline_run.duration
                },
                "failed_jobs": failed_jobs
            }
            
            # Use Groq to analyze the failure
            analysis = self.groq_service.analyze_pipeline_failure(context)
            
            # Determine severity based on AI analysis and job types
            severity = self._determine_severity(failed_jobs, analysis)
            
            # Create issue
            issue = PipelineIssue(
                pipeline_run_id=pipeline_run.id,
                issue_type="pipeline_failure",
                severity=severity,
                title=f"Pipeline failure in {pipeline_run.workflow_name}",
                description=f"Pipeline run {pipeline_run.run_id} failed with {len(failed_jobs)} failed jobs",
                affected_jobs=failed_jobs,
                error_logs=json.dumps(failed_jobs, indent=2),
                ai_analysis=analysis,
                suggested_fixes=self.groq_service.generate_fixes(context, analysis)
            )
            
            # Save to database
            db = SessionLocal()
            try:
                db.add(issue)
                db.commit()
                db.refresh(issue)
                
                # Create agent action
                action = AgentAction(
                    agent_name=self.name,
                    action_type="issue_detection",
                    pipeline_run_id=pipeline_run.id,
                    issue_id=issue.id,
                    action_data={
                        "issue_type": "pipeline_failure",
                        "severity": severity,
                        "failed_jobs_count": len(failed_jobs)
                    },
                    status="completed",
                    result={"issue_id": issue.id}
                )
                db.add(action)
                db.commit()
                
                return issue.to_dict()
                
            except Exception as e:
                logger.error(f"Error saving failure analysis: {e}")
                db.rollback()
                return None
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error analyzing failure: {e}")
            return None
    
    async def _check_long_running_jobs(self, pipeline_run: PipelineRun, run_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for jobs that are taking too long to complete"""
        issues = []
        
        # Define thresholds (in seconds)
        thresholds = {
            "test": 600,  # 10 minutes
            "build": 900,  # 15 minutes
            "deploy": 1200,  # 20 minutes
            "default": 1800  # 30 minutes
        }
        
        for job in run_details["jobs"]:
            if job["duration"] and job["duration"] > thresholds.get(job["name"].lower(), thresholds["default"]):
                issue = PipelineIssue(
                    pipeline_run_id=pipeline_run.id,
                    issue_type="long_running_job",
                    severity="medium",
                    title=f"Long running job: {job['name']}",
                    description=f"Job {job['name']} took {job['duration']} seconds to complete",
                    affected_jobs=[job],
                    ai_analysis=f"Job {job['name']} exceeded the expected duration threshold. This may indicate performance issues or resource constraints.",
                    suggested_fixes={
                        "optimize_job": "Consider optimizing the job steps or parallelizing tasks",
                        "increase_resources": "Consider using larger runners or more resources",
                        "cache_dependencies": "Implement caching for dependencies and build artifacts"
                    }
                )
                
                # Save to database
                db = SessionLocal()
                try:
                    db.add(issue)
                    db.commit()
                    db.refresh(issue)
                    issues.append(issue.to_dict())
                except Exception as e:
                    logger.error(f"Error saving long running job issue: {e}")
                    db.rollback()
                finally:
                    db.close()
        
        return issues
    
    async def _check_security_issues(self, pipeline_run: PipelineRun, run_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for security-related issues in the pipeline"""
        issues = []
        
        # Look for security-related job failures
        security_jobs = ["security-scan", "vulnerability-scan", "trivy", "bandit", "safety"]
        
        for job in run_details["jobs"]:
            if any(sec_job in job["name"].lower() for sec_job in security_jobs):
                if job["conclusion"] == "failure":
                    issue = PipelineIssue(
                        pipeline_run_id=pipeline_run.id,
                        issue_type="security_vulnerability",
                        severity="high",
                        title=f"Security scan failed: {job['name']}",
                        description=f"Security scan job {job['name']} failed, potential vulnerabilities detected",
                        affected_jobs=[job],
                        ai_analysis="Security scan failure indicates potential vulnerabilities in the codebase or dependencies. Immediate attention required.",
                        suggested_fixes={
                            "review_logs": "Review the security scan logs for specific vulnerabilities",
                            "update_dependencies": "Update vulnerable dependencies to latest secure versions",
                            "code_review": "Review code changes for potential security issues"
                        }
                    )
                    
                    # Save to database
                    db = SessionLocal()
                    try:
                        db.add(issue)
                        db.commit()
                        db.refresh(issue)
                        issues.append(issue.to_dict())
                    except Exception as e:
                        logger.error(f"Error saving security issue: {e}")
                        db.rollback()
                    finally:
                        db.close()
        
        return issues
    
    async def _check_performance_issues(self, pipeline_run: PipelineRun, run_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for performance-related issues"""
        issues = []
        
        # Check overall pipeline duration
        if pipeline_run.duration and pipeline_run.duration > 3600:  # 1 hour
            issue = PipelineIssue(
                pipeline_run_id=pipeline_run.id,
                issue_type="pipeline_performance",
                severity="medium",
                title="Pipeline performance degradation",
                description=f"Pipeline took {pipeline_run.duration} seconds to complete",
                affected_jobs=run_details["jobs"],
                ai_analysis="Pipeline duration exceeds optimal thresholds. Consider optimizing job execution and resource allocation.",
                suggested_fixes={
                    "parallel_jobs": "Run independent jobs in parallel",
                    "optimize_steps": "Review and optimize individual job steps",
                    "caching": "Implement comprehensive caching strategy"
                }
            )
            
            # Save to database
            db = SessionLocal()
            try:
                db.add(issue)
                db.commit()
                db.refresh(issue)
                issues.append(issue.to_dict())
            except Exception as e:
                logger.error(f"Error saving performance issue: {e}")
                db.rollback()
            finally:
                db.close()
        
        return issues
    
    async def _get_ai_analysis(self, analysis_type: str, context: Dict[str, Any], prompt: str) -> str:
        """Get AI analysis for pipeline issues"""
        try:
            system_prompt = f"""You are a DevOps expert analyzing CI/CD pipeline issues. 
            Provide clear, actionable insights about the problem and potential solutions.
            Focus on practical recommendations that can be implemented immediately."""
            
            user_prompt = f"""
            Context: {json.dumps(context, indent=2)}
            
            {prompt}
            
            Please provide:
            1. Root cause analysis
            2. Severity assessment
            3. Immediate actions to take
            4. Long-term improvements
            """
            
            response = self.openai_client.chat.completions.create(
                model=self.config.openai.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.config.openai.temperature,
                max_tokens=self.config.openai.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error getting AI analysis: {e}")
            return "Unable to generate AI analysis due to technical issues."
    
    async def _generate_fixes(self, context: Dict[str, Any], analysis: str) -> Dict[str, Any]:
        """Generate suggested fixes based on AI analysis"""
        try:
            system_prompt = """You are a DevOps expert providing specific, actionable fixes for CI/CD pipeline issues.
            Provide fixes in a structured format with clear steps."""
            
            user_prompt = f"""
            Based on this analysis: {analysis}
            
            Context: {json.dumps(context, indent=2)}
            
            Provide specific, actionable fixes in JSON format with the following structure:
            {{
                "immediate_fixes": [
                    {{"title": "Fix title", "description": "Detailed description", "steps": ["step1", "step2"]}}
                ],
                "long_term_improvements": [
                    {{"title": "Improvement title", "description": "Detailed description", "priority": "high/medium/low"}}
                ]
            }}
            """
            
            response = self.openai_client.chat.completions.create(
                model=self.config.openai.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.config.openai.temperature,
                max_tokens=self.config.openai.max_tokens
            )
            
            try:
                return json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                return {
                    "immediate_fixes": [{"title": "Review logs", "description": "Review the pipeline logs for specific errors", "steps": ["Check job logs", "Identify error patterns"]}],
                    "long_term_improvements": [{"title": "Improve monitoring", "description": "Implement better monitoring and alerting", "priority": "medium"}]
                }
                
        except Exception as e:
            logger.error(f"Error generating fixes: {e}")
            return {
                "immediate_fixes": [],
                "long_term_improvements": []
            }
    
    def _determine_severity(self, failed_jobs: List[Dict[str, Any]], analysis: str) -> str:
        """Determine issue severity based on failed jobs and analysis"""
        # Use Groq to determine severity
        context = {
            "failed_jobs": failed_jobs,
            "analysis": analysis
        }
        return self.groq_service.determine_severity(context)
    
    async def run(self) -> Dict[str, Any]:
        """Main entry point for the pipeline monitor agent"""
        logger.info("Starting Pipeline Monitor Agent...")
        
        start_time = datetime.utcnow()
        
        try:
            # Monitor pipeline runs
            issues = await self.monitor_pipeline_runs()
            
            # Generate summary
            summary = {
                "agent_name": self.name,
                "start_time": start_time.isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "issues_found": len(issues),
                "issues": issues,
                "status": "completed"
            }
            
            logger.info(f"Pipeline Monitor Agent completed. Found {len(issues)} issues.")
            return summary
            
        except Exception as e:
            logger.error(f"Error in Pipeline Monitor Agent: {e}")
            return {
                "agent_name": self.name,
                "start_time": start_time.isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "error": str(e),
                "status": "failed"
            } 