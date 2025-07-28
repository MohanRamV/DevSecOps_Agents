import os
import keyring
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

load_dotenv()

class GroqConfig(BaseSettings):
    """Groq API configuration"""
    api_key: Optional[str] = Field(None, env="GROQ_API_KEY")
    model: str = Field("llama3-8b-8192", env="GROQ_MODEL")  # Free model
    temperature: float = Field(0.1, env="GROQ_TEMPERATURE")
    max_tokens: int = Field(2000, env="GROQ_MAX_TOKENS")
    
    def get_api_key(self) -> Optional[str]:
        """Get API key from password manager or environment"""
        # Try password manager first
        stored_key = keyring.get_password("devsecops_monitoring", "groq_api_key")
        if stored_key:
            return stored_key
        # Fallback to environment variable
        if self.api_key and self.api_key != "your_groq_api_key_here":
            return self.api_key
        return None
    
    def store_api_key(self, api_key: str):
        """Store API key in password manager"""
        keyring.set_password("devsecops_monitoring", "groq_api_key", api_key)

class GitHubConfig(BaseSettings):
    """GitHub API configuration"""
    token: Optional[str] = Field(None, env="GITHUB_TOKEN")
    repository: Optional[str] = Field(None, env="GITHUB_REPOSITORY")
    owner: Optional[str] = Field(None, env="GITHUB_OWNER")
    webhook_secret: Optional[str] = Field(None, env="GITHUB_WEBHOOK_SECRET")
    
    def get_token(self) -> Optional[str]:
        """Get token from password manager or environment"""
        stored_token = keyring.get_password("devsecops_monitoring", "github_token")
        if stored_token:
            return stored_token
        # Fallback to environment variable
        if self.token and self.token != "your_github_personal_access_token_here":
            return self.token
        return None
    
    def store_token(self, token: str):
        """Store token in password manager"""
        keyring.set_password("devsecops_monitoring", "github_token", token)
        
    def store_repository(self, repository: str):
        keyring.set_password("devsecops_monitoring", "github_repository", repository)

    def store_owner(self, owner: str):
        keyring.set_password("devsecops_monitoring", "github_owner", owner)

    def get_repository(self):
        return keyring.get_password("devsecops_monitoring", "github_repository") or self.repository

    def get_owner(self):
        return keyring.get_password("devsecops_monitoring", "github_owner") or self.owner


class KubernetesConfig(BaseSettings):
    """Kubernetes configuration"""
    config_path: Optional[str] = Field(None, env="KUBECONFIG")
    namespace: str = Field("default", env="K8S_NAMESPACE")
    context: Optional[str] = Field(None, env="K8S_CONTEXT")

class DatabaseConfig(BaseSettings):
    """Database configuration"""
    url: str = Field("sqlite:///./cicd_monitoring.db", env="DATABASE_URL")
    echo: bool = Field(False, env="DATABASE_ECHO")

class MonitoringConfig(BaseSettings):
    """Monitoring configuration"""
    check_interval: int = Field(300, env="CHECK_INTERVAL")  # 5 minutes
    alert_threshold: int = Field(3, env="ALERT_THRESHOLD")  # 3 failures
    retention_days: int = Field(30, env="RETENTION_DAYS")

class NotificationConfig(BaseSettings):
    """Notification configuration"""
    slack_webhook: Optional[str] = Field(None, env="SLACK_WEBHOOK")
    email_smtp: Optional[str] = Field(None, env="EMAIL_SMTP")
    email_user: Optional[str] = Field(None, env="EMAIL_USER")
    email_password: Optional[str] = Field(None, env="EMAIL_PASSWORD")
    teams_webhook: Optional[str] = Field(None, env="TEAMS_WEBHOOK")
    
    def get_slack_webhook(self) -> Optional[str]:
        """Get Slack webhook from password manager or environment"""
        stored_webhook = keyring.get_password("devsecops_monitoring", "slack_webhook")
        if stored_webhook:
            return stored_webhook
        return self.slack_webhook
    
    def store_slack_webhook(self, webhook: str):
        """Store Slack webhook in password manager"""
        keyring.set_password("devsecops_monitoring", "slack_webhook", webhook)
    
    def get_teams_webhook(self) -> Optional[str]:
        """Get Teams webhook from password manager or environment"""
        stored_webhook = keyring.get_password("devsecops_monitoring", "teams_webhook")
        if stored_webhook:
            return stored_webhook
        return self.teams_webhook
    
    def store_teams_webhook(self, webhook: str):
        """Store Teams webhook in password manager"""
        keyring.set_password("devsecops_monitoring", "teams_webhook", webhook)
    
    def get_email_password(self) -> Optional[str]:
        """Get email password from password manager or environment"""
        stored_password = keyring.get_password("devsecops_monitoring", "email_password")
        if stored_password:
            return stored_password
        return self.email_password
    
    def store_email_password(self, password: str):
        """Store email password in password manager"""
        keyring.set_password("devsecops_monitoring", "email_password", password)

class Config(BaseSettings):
    """Main configuration class"""
    # Environment
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    
    # API settings
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")
    
    # GitHub
    github: GitHubConfig = GitHubConfig()
    
    # Groq
    groq: GroqConfig = GroqConfig()
    
    # Kubernetes
    kubernetes: KubernetesConfig = KubernetesConfig()
    
    # Database
    database: DatabaseConfig = DatabaseConfig()
    
    # Monitoring
    monitoring: MonitoringConfig = MonitoringConfig()
    
    # Notifications
    notifications: NotificationConfig = NotificationConfig()
    
    # Agent settings
    max_concurrent_agents: int = Field(5, env="MAX_CONCURRENT_AGENTS")
    agent_timeout: int = Field(300, env="AGENT_TIMEOUT")  # 5 minutes
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"  # Allow extra fields to prevent validation errors

# Global config instance
config = Config()

def get_config() -> Config:
    """Get the global configuration instance"""
    return config

def setup_password_manager():
    """Setup password manager for secure credential storage"""
    try:
        # Test password manager functionality
        keyring.set_password("devsecops_monitoring", "test", "test_value")
        test_value = keyring.get_password("devsecops_monitoring", "test")
        if test_value == "test_value":
            keyring.delete_password("devsecops_monitoring", "test")
            return True
        return False
    except Exception as e:
        print(f"Password manager setup failed: {e}")
        return False

def check_credentials_status() -> Dict[str, bool]:
    """Check the status of all credentials"""
    config = get_config()
    
    # Reload environment variables
    load_dotenv()
    
    status = {
        "groq_api_key": config.groq.get_api_key() is not None,
        "github_token": config.github.get_token() is not None,
        "github_repository": config.github.get_repository() is not None,
        "github_owner": config.github.get_owner() is not None,
        "slack_webhook": config.notifications.get_slack_webhook() is not None,
        "teams_webhook": config.notifications.get_teams_webhook() is not None,
        "email_configured": (
            # Check environment variables first, then config
            (os.getenv("EMAIL_SMTP") or config.notifications.email_smtp) is not None and 
            (os.getenv("EMAIL_USER") or config.notifications.email_user) is not None and 
            config.notifications.get_email_password() is not None
        )
    }
    
    return status