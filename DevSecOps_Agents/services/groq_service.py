import json
from typing import Dict, Any, Optional, List
from groq import Groq
from loguru import logger

from config.config import get_config

class GroqService:
    """Service for interacting with Groq API"""
    
    def __init__(self):
        self.config = get_config()
        api_key = self.config.groq.get_api_key()
        if not api_key:
            raise ValueError("Groq API key not configured. Please run setup_credentials.py first.")
        self.client = Groq(api_key=api_key)
        
    def get_available_models(self) -> List[str]:
        """Get list of available Groq models"""
        return [
            "llama3-8b-8192",      # Free model - 8B parameters
            "llama3-70b-8192",     # Free model - 70B parameters
            "mixtral-8x7b-32768",  # Free model - Mixtral
            "gemma2-9b-it",        # Free model - Gemma2
            "llama2-70b-4096",     # Free model - Llama2
        ]
    
    def analyze_pipeline_failure(self, context: Dict[str, Any]) -> str:
        """Analyze pipeline failure using Groq"""
        try:
            system_prompt = """You are a DevOps expert analyzing CI/CD pipeline issues. 
            Provide clear, actionable insights about the problem and potential solutions.
            Focus on practical recommendations that can be implemented immediately."""
            
            user_prompt = f"""
            Analyze this pipeline failure and provide insights:
            
            Context: {json.dumps(context, indent=2)}
            
            Please provide:
            1. Root cause analysis
            2. Severity assessment
            3. Immediate actions to take
            4. Long-term improvements
            
            Be concise but comprehensive.
            """
            
            response = self.client.chat.completions.create(
                model=self.config.groq.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.config.groq.temperature,
                max_tokens=self.config.groq.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error analyzing pipeline failure with Groq: {e}")
            return "Unable to generate analysis due to technical issues."
    
    def analyze_deployment_failure(self, context: Dict[str, Any]) -> str:
        """Analyze deployment failure using Groq"""
        try:
            system_prompt = """You are a Kubernetes expert analyzing deployment issues. 
            Provide clear, actionable insights about the problem and potential solutions.
            Focus on practical recommendations that can be implemented immediately."""
            
            user_prompt = f"""
            Analyze this Kubernetes deployment failure and provide insights:
            
            Context: {json.dumps(context, indent=2)}
            
            Please provide:
            1. Root cause analysis
            2. Severity assessment
            3. Immediate actions to take
            4. Long-term improvements
            
            Be concise but comprehensive.
            """
            
            response = self.client.chat.completions.create(
                model=self.config.groq.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.config.groq.temperature,
                max_tokens=self.config.groq.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error analyzing deployment failure with Groq: {e}")
            return "Unable to generate analysis due to technical issues."
    
    def generate_fixes(self, context: Dict[str, Any], analysis: str) -> Dict[str, Any]:
        """Generate suggested fixes using Groq"""
        try:
            system_prompt = """You are a DevOps expert providing specific, actionable fixes for CI/CD issues.
            Provide fixes in a structured JSON format with clear steps."""
            
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
            
            Return only valid JSON.
            """
            
            response = self.client.chat.completions.create(
                model=self.config.groq.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.config.groq.temperature,
                max_tokens=self.config.groq.max_tokens
            )
            
            try:
                return json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                return {
                    "immediate_fixes": [{"title": "Review logs", "description": "Review the logs for specific errors", "steps": ["Check logs", "Identify error patterns"]}],
                    "long_term_improvements": [{"title": "Improve monitoring", "description": "Implement better monitoring and alerting", "priority": "medium"}]
                }
                
        except Exception as e:
            logger.error(f"Error generating fixes with Groq: {e}")
            return {
                "immediate_fixes": [],
                "long_term_improvements": []
            }
    
    def create_notification_message(self, issue: Dict[str, Any], channel: str) -> str:
        """Create notification message using Groq"""
        try:
            system_prompt = f"""You are a DevOps expert creating notification messages for {channel} channel.
            Create clear, actionable messages that inform about CI/CD issues and provide next steps."""
            
            user_prompt = f"""
            Create a notification message for this issue:
            
            Issue: {issue.get('title', 'Unknown Issue')}
            Description: {issue.get('description', 'No description')}
            Severity: {issue.get('severity', 'Unknown')}
            Type: {issue.get('issue_type', 'Unknown')}
            Analysis: {issue.get('ai_analysis', 'No analysis available')}
            
            The message should:
            1. Be concise but informative
            2. Include the key problem
            3. Suggest immediate actions
            4. Be appropriate for {channel} channel
            
            Keep it under 200 words.
            """
            
            response = self.client.chat.completions.create(
                model=self.config.groq.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error creating notification message with Groq: {e}")
            # Fallback message
            return f"""
Issue: {issue.get('title', 'Unknown Issue')}
Description: {issue.get('description', 'No description')}
Severity: {issue.get('severity', 'Unknown').upper()}
Status: {issue.get('status', 'Unknown').upper()}

Please review this issue and take appropriate action.
            """.strip()
    
    def determine_severity(self, context: Dict[str, Any]) -> str:
        """Determine issue severity using Groq"""
        try:
            system_prompt = """You are a DevOps expert assessing issue severity.
            Return only: "critical", "high", "medium", or "low" based on the context."""
            
            user_prompt = f"""
            Assess the severity of this issue:
            
            Context: {json.dumps(context, indent=2)}
            
            Consider:
            - Impact on production
            - Number of users affected
            - Security implications
            - Business criticality
            
            Return only: critical, high, medium, or low
            """
            
            response = self.client.chat.completions.create(
                model=self.config.groq.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            severity = response.choices[0].message.content.strip().lower()
            
            # Validate severity
            valid_severities = ["critical", "high", "medium", "low"]
            if severity in valid_severities:
                return severity
            else:
                return "medium"  # Default fallback
                
        except Exception as e:
            logger.error(f"Error determining severity with Groq: {e}")
            return "medium"  # Default fallback
    
    def test_connection(self) -> bool:
        """Test Groq API connection"""
        try:
            response = self.client.chat.completions.create(
                model=self.config.groq.model,
                messages=[
                    {"role": "user", "content": "Test connection"}
                ],
                max_tokens=10
            )
            return True
        except Exception as e:
            logger.error(f"Groq connection test failed: {e}")
            return False 