import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

from config.config import get_config
from models.database import Deployment, PipelineIssue, AgentAction, SessionLocal
from services.groq_service import GroqService
from agents.base_agent import BaseAgent

class DeploymentMonitorAgent(BaseAgent):
    """Agent for monitoring Kubernetes deployments and detecting issues"""
    
    def __init__(self):
        super().__init__("DeploymentMonitorAgent")
        self.config = get_config()
        self.groq_service = GroqService()
        
        # Initialize Kubernetes client
        try:
            if self.config.kubernetes.config_path:
                k8s_config.load_kube_config(config_file=self.config.kubernetes.config_path)
            else:
                # Try in-cluster config first, fallback to default kubeconfig
                try:
                    k8s_config.load_incluster_config()
                except k8s_config.ConfigException:
                    # Not running in cluster, try default kubeconfig
                    try:
                        k8s_config.load_kube_config()
                    except k8s_config.ConfigException:
                        logger.warning("No Kubernetes configuration found. Deployment monitoring will be disabled.")
                        self.k8s_apps_v1 = None
                        self.k8s_core_v1 = None
                        self.k8s_networking_v1 = None
                        return
            
            self.k8s_apps_v1 = client.AppsV1Api()
            self.k8s_core_v1 = client.CoreV1Api()
            self.k8s_networking_v1 = client.NetworkingV1Api()
            logger.info("Kubernetes client initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Kubernetes client: {e}")
            self.k8s_apps_v1 = None
            self.k8s_core_v1 = None
            self.k8s_networking_v1 = None
    
    async def monitor_deployments(self) -> List[Dict[str, Any]]:
        """Monitor Kubernetes deployments and detect issues"""
        logger.info("Starting deployment monitoring...")
        
        if not self.k8s_apps_v1:
            logger.warning("Kubernetes client not initialized. Deployment monitoring is disabled. Please configure Kubernetes access or set KUBECONFIG environment variable.")
            return []
        
        try:
            issues_found = []
            
            # Get all deployments in the namespace
            deployments = self.k8s_apps_v1.list_namespaced_deployment(
                namespace=self.config.kubernetes.namespace
            )
            
            for deployment in deployments.items:
                # Check if we already processed this deployment recently
                db = SessionLocal()
                try:
                    existing_deployment = db.query(Deployment).filter(
                        Deployment.deployment_name == deployment.metadata.name
                    ).order_by(Deployment.updated_at.desc()).first()
                    
                    # Update deployment information
                    deployment_data = {
                        "deployment_name": deployment.metadata.name,
                        "namespace": deployment.metadata.namespace,
                        "image_tag": deployment.spec.template.spec.containers[0].image if deployment.spec.template.spec.containers else None,
                        "status": self._get_deployment_status(deployment),
                        "replicas": deployment.spec.replicas,
                        "available_replicas": deployment.status.available_replicas,
                        "ready_replicas": deployment.status.ready_replicas,
                        "kubernetes_data": {
                            "uid": deployment.metadata.uid,
                            "generation": deployment.metadata.generation,
                            "observed_generation": deployment.status.observed_generation,
                            "conditions": [
                                {
                                    "type": condition.type,
                                    "status": condition.status,
                                    "reason": condition.reason,
                                    "message": condition.message
                                }
                                for condition in deployment.status.conditions or []
                            ]
                        }
                    }
                    
                    # Save or update deployment
                    if existing_deployment:
                        existing_deployment.image_tag = deployment_data["image_tag"]
                        existing_deployment.status = deployment_data["status"]
                        existing_deployment.replicas = deployment_data["replicas"]
                        existing_deployment.available_replicas = deployment_data["available_replicas"]
                        existing_deployment.ready_replicas = deployment_data["ready_replicas"]
                        existing_deployment.kubernetes_data = deployment_data["kubernetes_data"]
                        existing_deployment.updated_at = datetime.utcnow()
                        db_deployment = existing_deployment
                    else:
                        db_deployment = Deployment(**deployment_data)
                        db.add(db_deployment)
                    
                    db.commit()
                    db.refresh(db_deployment)
                    
                    # Analyze deployment for issues
                    issues = await self._analyze_deployment(db_deployment, deployment)
                    issues_found.extend(issues)
                    
                except Exception as e:
                    logger.error(f"Error processing deployment {deployment.metadata.name}: {e}")
                    db.rollback()
                finally:
                    db.close()
            
            logger.info(f"Deployment monitoring completed. Found {len(issues_found)} issues.")
            return issues_found
            
        except Exception as e:
            logger.error(f"Error in deployment monitoring: {e}")
            return []
    
    def _get_deployment_status(self, deployment) -> str:
        """Determine deployment status based on conditions"""
        if not deployment.status.conditions:
            return "unknown"
        
        for condition in deployment.status.conditions:
            if condition.type == "Available" and condition.status == "True":
                return "running"
            elif condition.type == "Progressing" and condition.status == "False":
                return "failed"
            elif condition.type == "ReplicaFailure" and condition.status == "True":
                return "failed"
        
        return "pending"
    
    async def _analyze_deployment(self, db_deployment: Deployment, k8s_deployment) -> List[Dict[str, Any]]:
        """Analyze a deployment for potential issues"""
        issues = []
        
        # Check for failed deployments
        if db_deployment.status == "failed":
            issue = await self._analyze_deployment_failure(db_deployment, k8s_deployment)
            if issue:
                issues.append(issue)
        
        # Check for scaling issues
        scaling_issues = await self._check_scaling_issues(db_deployment, k8s_deployment)
        issues.extend(scaling_issues)
        
        # Check for resource issues
        resource_issues = await self._check_resource_issues(db_deployment, k8s_deployment)
        issues.extend(resource_issues)
        
        # Check for health issues
        health_issues = await self._check_health_issues(db_deployment, k8s_deployment)
        issues.extend(health_issues)
        
        return issues
    
    async def _analyze_deployment_failure(self, db_deployment: Deployment, k8s_deployment) -> Optional[Dict[str, Any]]:
        """Analyze a failed deployment"""
        try:
            # Get deployment conditions
            conditions = db_deployment.kubernetes_data.get("conditions", [])
            
            # Get pod events for more context
            pod_events = await self._get_pod_events(k8s_deployment.metadata.name)
            
            # Prepare context for AI analysis
            context = {
                "deployment": {
                    "name": db_deployment.deployment_name,
                    "namespace": db_deployment.namespace,
                    "image_tag": db_deployment.image_tag,
                    "status": db_deployment.status,
                    "replicas": db_deployment.replicas,
                    "available_replicas": db_deployment.available_replicas,
                    "ready_replicas": db_deployment.ready_replicas
                },
                "conditions": conditions,
                "pod_events": pod_events
            }
            
            # Use Groq to analyze the failure
            analysis = self.groq_service.analyze_deployment_failure(context)
            
            # Determine severity
            severity = self._determine_deployment_severity(conditions, pod_events)
            
            # Create issue
            issue = PipelineIssue(
                pipeline_run_id=None,  # Will be linked later if available
                issue_type="deployment_failure",
                severity=severity,
                title=f"Deployment failure: {db_deployment.deployment_name}",
                description=f"Deployment {db_deployment.deployment_name} failed to deploy successfully",
                affected_jobs=[{"deployment": db_deployment.deployment_name, "namespace": db_deployment.namespace}],
                error_logs=json.dumps({"conditions": conditions, "pod_events": pod_events}, indent=2),
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
                    issue_id=issue.id,
                    action_data={
                        "issue_type": "deployment_failure",
                        "severity": severity,
                        "deployment_name": db_deployment.deployment_name
                    },
                    status="completed",
                    result={"issue_id": issue.id}
                )
                db.add(action)
                db.commit()
                
                return issue.to_dict()
                
            except Exception as e:
                logger.error(f"Error saving deployment failure analysis: {e}")
                db.rollback()
                return None
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error analyzing deployment failure: {e}")
            return None
    
    async def _check_scaling_issues(self, db_deployment: Deployment, k8s_deployment) -> List[Dict[str, Any]]:
        """Check for scaling-related issues"""
        issues = []
        
        # Check if desired replicas are not available
        if db_deployment.replicas and db_deployment.available_replicas:
            if db_deployment.available_replicas < db_deployment.replicas:
                issue = PipelineIssue(
                    pipeline_run_id=None,
                    issue_type="scaling_issue",
                    severity="medium",
                    title=f"Scaling issue: {db_deployment.deployment_name}",
                    description=f"Deployment has {db_deployment.available_replicas}/{db_deployment.replicas} replicas available",
                    affected_jobs=[{"deployment": db_deployment.deployment_name}],
                    ai_analysis="Deployment is not running the desired number of replicas. This may indicate resource constraints or pod startup issues.",
                    suggested_fixes={
                        "check_resources": "Check if there are sufficient cluster resources",
                        "check_pod_logs": "Review pod logs for startup issues",
                        "check_image": "Verify the container image is accessible and valid"
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
                    logger.error(f"Error saving scaling issue: {e}")
                    db.rollback()
                finally:
                    db.close()
        
        return issues
    
    async def _check_resource_issues(self, db_deployment: Deployment, k8s_deployment) -> List[Dict[str, Any]]:
        """Check for resource-related issues"""
        issues = []
        
        # Check pod resource requests and limits
        if k8s_deployment.spec.template.spec.containers:
            for container in k8s_deployment.spec.template.spec.containers:
                if not container.resources or not container.resources.requests:
                    issue = PipelineIssue(
                        pipeline_run_id=None,
                        issue_type="resource_configuration",
                        severity="low",
                        title=f"Missing resource requests: {db_deployment.deployment_name}",
                        description=f"Container {container.name} is missing resource requests",
                        affected_jobs=[{"deployment": db_deployment.deployment_name, "container": container.name}],
                        ai_analysis="Missing resource requests can lead to resource contention and unpredictable performance.",
                        suggested_fixes={
                            "add_requests": "Add resource requests to the container specification",
                            "set_limits": "Consider adding resource limits as well"
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
                        logger.error(f"Error saving resource issue: {e}")
                        db.rollback()
                    finally:
                        db.close()
        
        return issues
    
    async def _check_health_issues(self, db_deployment: Deployment, k8s_deployment) -> List[Dict[str, Any]]:
        """Check for health-related issues"""
        issues = []
        
        # Check if health checks are configured
        if k8s_deployment.spec.template.spec.containers:
            for container in k8s_deployment.spec.template.spec.containers:
                if not container.liveness_probe and not container.readiness_probe:
                    issue = PipelineIssue(
                        pipeline_run_id=None,
                        issue_type="health_check_missing",
                        severity="medium",
                        title=f"Missing health checks: {db_deployment.deployment_name}",
                        description=f"Container {container.name} is missing health checks",
                        affected_jobs=[{"deployment": db_deployment.deployment_name, "container": container.name}],
                        ai_analysis="Missing health checks can lead to undetected application failures and poor user experience.",
                        suggested_fixes={
                            "add_liveness_probe": "Add liveness probe to detect deadlocked applications",
                            "add_readiness_probe": "Add readiness probe to ensure traffic is only sent to ready pods"
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
                        logger.error(f"Error saving health issue: {e}")
                        db.rollback()
                    finally:
                        db.close()
        
        return issues
    
    async def _get_pod_events(self, deployment_name: str) -> List[Dict[str, Any]]:
        """Get events for pods in a deployment"""
        try:
            if not self.k8s_core_v1:
                return []
            
            # Get pods for this deployment
            pods = self.k8s_core_v1.list_namespaced_pod(
                namespace=self.config.kubernetes.namespace,
                label_selector=f"app={deployment_name}"
            )
            
            events = []
            for pod in pods.items:
                pod_events = self.k8s_core_v1.list_namespaced_event(
                    namespace=self.config.kubernetes.namespace,
                    field_selector=f"involvedObject.name={pod.metadata.name}"
                )
                
                for event in pod_events.items:
                    events.append({
                        "pod_name": pod.metadata.name,
                        "type": event.type,
                        "reason": event.reason,
                        "message": event.message,
                        "count": event.count,
                        "first_timestamp": event.first_timestamp.isoformat() if event.first_timestamp else None,
                        "last_timestamp": event.last_timestamp.isoformat() if event.last_timestamp else None
                    })
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting pod events: {e}")
            return []
    
    async def _get_ai_analysis(self, analysis_type: str, context: Dict[str, Any], prompt: str) -> str:
        """Get AI analysis for deployment issues"""
        try:
            system_prompt = f"""You are a Kubernetes expert analyzing deployment issues. 
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
    
    async def _generate_deployment_fixes(self, context: Dict[str, Any], analysis: str) -> Dict[str, Any]:
        """Generate suggested fixes for deployment issues"""
        try:
            system_prompt = """You are a Kubernetes expert providing specific, actionable fixes for deployment issues.
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
                    "immediate_fixes": [{"title": "Check pod logs", "description": "Review pod logs for specific errors", "steps": ["kubectl logs <pod-name>", "Check for error patterns"]}],
                    "long_term_improvements": [{"title": "Improve monitoring", "description": "Implement better monitoring and alerting", "priority": "medium"}]
                }
                
        except Exception as e:
            logger.error(f"Error generating deployment fixes: {e}")
            return {
                "immediate_fixes": [],
                "long_term_improvements": []
            }
    
    def _determine_deployment_severity(self, conditions: List[Dict[str, Any]], pod_events: List[Dict[str, Any]]) -> str:
        """Determine issue severity based on deployment conditions and events"""
        # Check for critical conditions
        for condition in conditions:
            if condition.get("type") == "Available" and condition.get("status") == "False":
                return "critical"
            elif condition.get("type") == "Progressing" and condition.get("status") == "False":
                return "high"
        
        # Check for critical events
        for event in pod_events:
            if event.get("type") == "Warning" and "Failed" in event.get("reason", ""):
                return "high"
            elif event.get("type") == "Normal" and "Scheduled" not in event.get("reason", ""):
                return "medium"
        
        return "low"
    
    async def run(self) -> Dict[str, Any]:
        """Main entry point for the deployment monitor agent"""
        logger.info("Starting Deployment Monitor Agent...")
        
        start_time = datetime.utcnow()
        
        try:
            # Monitor deployments
            issues = await self.monitor_deployments()
            
            # Generate summary
            summary = {
                "agent_name": self.name,
                "start_time": start_time.isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "issues_found": len(issues),
                "issues": issues,
                "status": "completed"
            }
            
            logger.info(f"Deployment Monitor Agent completed. Found {len(issues)} issues.")
            return summary
            
        except Exception as e:
            logger.error(f"Error in Deployment Monitor Agent: {e}")
            return {
                "agent_name": self.name,
                "start_time": start_time.isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "error": str(e),
                "status": "failed"
            } 