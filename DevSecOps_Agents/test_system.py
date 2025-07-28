#!/usr/bin/env python3
"""
Test script for DevSecOps AI Monitoring System
This script demonstrates the basic functionality of the monitoring agents.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config import get_config, check_credentials_status
from models.database import init_db, SessionLocal
from agents.pipeline_monitor_agent import PipelineMonitorAgent
from agents.deployment_monitor_agent import DeploymentMonitorAgent
from agents.notification_agent import NotificationAgent
from sqlalchemy import text

async def test_pipeline_monitor():
    """Test the pipeline monitoring agent"""
    print("🧪 Testing Pipeline Monitor Agent...")
    
    try:
        agent = PipelineMonitorAgent()
        
        # Test agent info
        info = agent.get_agent_info()
        print(f"   Agent: {info['name']}")
        print(f"   Type: {info['type']}")
        print(f"   Description: {info['description']}")
        
        # Test health check
        health = await agent.health_check()
        print(f"   Health Status: {health['status']}")
        
        # Note: Full monitoring requires GitHub token and repository access
        print("   ⚠️  Full monitoring requires GitHub configuration")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def test_deployment_monitor():
    """Test the deployment monitoring agent"""
    print("🧪 Testing Deployment Monitor Agent...")
    
    try:
        agent = DeploymentMonitorAgent()
        
        # Test agent info
        info = agent.get_agent_info()
        print(f"   Agent: {info['name']}")
        print(f"   Type: {info['type']}")
        print(f"   Description: {info['description']}")
        
        # Test health check
        health = await agent.health_check()
        print(f"   Health Status: {health['status']}")
        
        # Note: Full monitoring requires Kubernetes access
        print("   ⚠️  Full monitoring requires Kubernetes configuration")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def test_notification_agent():
    """Test the notification agent"""
    print("🧪 Testing Notification Agent...")
    
    try:
        agent = NotificationAgent()
        
        # Test agent info
        info = agent.get_agent_info()
        print(f"   Agent: {info['name']}")
        print(f"   Type: {info['type']}")
        print(f"   Description: {info['description']}")
        
        # Test health check
        health = await agent.health_check()
        print(f"   Health Status: {health['status']}")
        
        # Note: Full notifications require webhook/email configuration
        print("   ⚠️  Full notifications require webhook/email configuration")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def test_database():
    """Test database functionality"""
    print("🧪 Testing Database...")
    
    try:
        # Initialize database
        init_db()
        print("   ✅ Database initialized")
        
        # Test database connection
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        print("   ✅ Database connection successful")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def test_configuration():
    """Test configuration loading"""
    print("🧪 Testing Configuration...")
    
    try:
        config = get_config()
        
        print(f"   Environment: {config.environment}")
        print(f"   API Host: {config.api_host}")
        print(f"   API Port: {config.api_port}")
        print(f"   Check Interval: {config.monitoring.check_interval}s")
        print(f"   Alert Threshold: {config.monitoring.alert_threshold}")
        
        # Check credential status
        credentials_status = check_credentials_status()
        
        print("\n   📋 Credential Status:")
        for credential, status in credentials_status.items():
            status_icon = "✅" if status else "❌"
            print(f"      {status_icon} {credential}")
        
        # Check if essential credentials are configured
        missing_essential = []
        if not credentials_status["groq_api_key"]:
            missing_essential.append("Groq API Key")
        if not credentials_status["github_token"]:
            missing_essential.append("GitHub Token")
        if not credentials_status["github_repository"]:
            missing_essential.append("GitHub Repository")
        if not credentials_status["github_owner"]:
            missing_essential.append("GitHub Owner")
        
        if missing_essential:
            print(f"\n   ⚠️  Missing essential configurations: {', '.join(missing_essential)}")
        else:
            print("\n   ✅ All essential configurations present")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def run_demo():
    """Run a demonstration of the system"""
    print("🚀 DevSecOps AI Monitoring System - Demo")
    print("=" * 50)
    
    # Test configuration
    config_ok = await test_configuration()
    print()
    
    # Test database
    db_ok = await test_database()
    print()
    
    # Test agents
    pipeline_ok = await test_pipeline_monitor()
    print()
    
    deployment_ok = await test_deployment_monitor()
    print()
    
    notification_ok = await test_notification_agent()
    print()
    
    # Summary
    print("📊 Test Summary")
    print("=" * 50)
    print(f"Configuration: {'✅' if config_ok else '❌'}")
    print(f"Database: {'✅' if db_ok else '❌'}")
    print(f"Pipeline Monitor: {'✅' if pipeline_ok else '❌'}")
    print(f"Deployment Monitor: {'✅' if deployment_ok else '❌'}")
    print(f"Notification Agent: {'✅' if notification_ok else '❌'}")
    
    all_tests_passed = all([config_ok, db_ok, pipeline_ok, deployment_ok, notification_ok])
    
    if all_tests_passed:
        print("\n🎉 All basic tests passed! System is ready for configuration.")
        print("\nNext steps:")
        print("1. Run: python setup_credentials.py")
        print("2. Configure your GitHub token, Groq API key, and notification settings")
        print("3. Run 'python main.py' to start the monitoring system")
    else:
        print("\n⚠️  Some tests failed. Please check the configuration and dependencies.")
    
    return all_tests_passed

def main():
    """Main entry point"""
    try:
        # Run the demo
        success = asyncio.run(run_demo())
        
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 