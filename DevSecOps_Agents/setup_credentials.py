#!/usr/bin/env python3
"""
Credential Setup Script for DevSecOps AI Monitoring System
This script helps users securely store their API keys and credentials using the password manager.
"""

import getpass
import sys
import os
from typing import Optional

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config import get_config, setup_password_manager, check_credentials_status

def setup_groq_credentials():
    """Setup Groq API credentials"""
    print("\n🔑 Setting up Groq API credentials...")
    
    # Check if already stored
    config = get_config()
    existing_key = config.groq.get_api_key()
    
    if existing_key:
        print("   ✅ Groq API key already configured")
        return True
    
    # Get API key from user
    print("   📝 Please enter your Groq API key:")
    print("   💡 Get your API key from: https://console.groq.com/keys")
    api_key = getpass.getpass("   Groq API Key: ").strip()
    
    if not api_key:
        print("   ❌ No API key provided")
        return False
    
    # Store in password manager
    try:
        config.groq.store_api_key(api_key)
        print("   ✅ Groq API key stored securely")
        return True
    except Exception as e:
        print(f"   ❌ Error storing API key: {e}")
        return False

def setup_github_credentials():
    """Setup GitHub API credentials"""
    print("\n🔑 Setting up GitHub API credentials...")
    
    # Check if already stored
    config = get_config()
    existing_token = config.github.get_token()
    
    if existing_token:
        print("   ✅ GitHub token already configured")
        return True
    
    # Get token from user
    print("   📝 Please enter your GitHub Personal Access Token:")
    print("   💡 Create a token at: https://github.com/settings/tokens")
    print("   🔧 Required permissions: repo, workflow, read:org")
    token = getpass.getpass("   GitHub Token: ").strip()
    
    if not token:
        print("   ❌ No token provided")
        return False
    
    # Store in password manager
    try:
        config.github.store_token(token)
        print("   ✅ GitHub token stored securely")
        return True
    except Exception as e:
        print(f"   ❌ Error storing token: {e}")
        return False

def setup_github_repository():
    """Setup GitHub repository information"""
    print("\n🔑 Setting up GitHub repository information...")
    
    config = get_config()
    
    # Check if repository is already configured
    existing_repo = config.github.get_repository()
    existing_owner = config.github.get_owner()
    
    if existing_repo and existing_owner:
        print("   ✅ GitHub repository and owner already configured")
        return True
    
    # Get repository information
    if not existing_repo:
        print("   📝 Please enter your GitHub repository:")
        print("   💡 Format: username/repository-name")
        repository = input("   Repository (e.g., myusername/myproject): ").strip()
        
        if repository:
            # Store in keyring instead of just environment variable
            try:
                config.github.store_repository(repository)
                print("   ✅ Repository stored securely")
            except Exception as e:
                print(f"   ❌ Error storing repository: {e}")
                return False
        else:
            print("   ⚠️  Repository not configured")
            return False
    
    if not existing_owner:
        print("   📝 Please enter your GitHub username:")
        owner = input("   Username: ").strip()
        
        if owner:
            # Store in keyring instead of just environment variable
            try:
                config.github.store_owner(owner)
                print("   ✅ Username stored securely")
            except Exception as e:
                print(f"   ❌ Error storing owner: {e}")
                return False
        else:
            print("   ⚠️  Username not configured")
            return False
    
    return True

def setup_slack_webhook():
    """Setup Slack webhook"""
    print("\n🔑 Setting up Slack webhook...")
    
    # Check if already stored
    config = get_config()
    existing_webhook = config.notifications.get_slack_webhook()
    
    if existing_webhook:
        print("   ✅ Slack webhook already configured")
        return True
    
    # Get webhook from user
    print("   📝 Please enter your Slack webhook URL (optional):")
    print("   💡 Create a webhook at: https://api.slack.com/apps")
    webhook = input("   Slack Webhook URL (press Enter to skip): ").strip()
    
    if not webhook:
        print("   ⏭️  Skipping Slack webhook setup")
        return True
    
    # Store in password manager
    try:
        config.notifications.store_slack_webhook(webhook)
        print("   ✅ Slack webhook stored securely")
        return True
    except Exception as e:
        print(f"   ❌ Error storing webhook: {e}")
        return False

def setup_teams_webhook():
    """Setup Microsoft Teams webhook"""
    print("\n🔑 Setting up Microsoft Teams webhook...")
    
    # Check if already stored
    config = get_config()
    existing_webhook = config.notifications.get_teams_webhook()
    
    if existing_webhook:
        print("   ✅ Teams webhook already configured")
        return True
    
    # Get webhook from user
    print("   📝 Please enter your Microsoft Teams webhook URL (optional):")
    print("   💡 Create a webhook in your Teams channel")
    webhook = input("   Teams Webhook URL (press Enter to skip): ").strip()
    
    if not webhook:
        print("   ⏭️  Skipping Teams webhook setup")
        return True
    
    # Store in password manager
    try:
        config.notifications.store_teams_webhook(webhook)
        print("   ✅ Teams webhook stored securely")
        return True
    except Exception as e:
        print(f"   ❌ Error storing webhook: {e}")
        return False

def setup_email_credentials():
    """Setup email credentials"""
    print("\n🔑 Setting up email credentials...")
    
    # Check if already stored
    config = get_config()
    existing_password = config.notifications.get_email_password()
    
    if existing_password and config.notifications.email_smtp and config.notifications.email_user:
        print("   ✅ Email credentials already configured")
        return True
    
    # Get email settings from user
    print("   📝 Please enter your email settings (optional):")
    smtp_server = input("   SMTP Server (e.g., smtp.gmail.com:587): ").strip()
    
    if not smtp_server:
        print("   ⏭️  Skipping email setup")
        return True
    
    email_user = input("   Email Address: ").strip()
    email_password = getpass.getpass("   Email Password/App Password: ").strip()
    
    if not email_user or not email_password:
        print("   ❌ Email credentials incomplete")
        return False
    
    # Store password in password manager and update environment variables
    try:
        config.notifications.store_email_password(email_password)
        
        # Also set environment variables for SMTP server and user
        os.environ["EMAIL_SMTP"] = smtp_server
        os.environ["EMAIL_USER"] = email_user
        
        # Write to .env file to persist these settings
        env_file_path = ".env"
        env_updates = [
            f"EMAIL_SMTP={smtp_server}",
            f"EMAIL_USER={email_user}"
        ]
        
        # Read existing .env file
        existing_env = []
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                existing_env = f.readlines()
        
        # Update or add the new environment variables
        updated_env = []
        env_keys_to_update = {"EMAIL_SMTP", "EMAIL_USER"}
        updated_keys = set()
        
        for line in existing_env:
            if '=' in line:
                key = line.split('=')[0].strip()
                if key in env_keys_to_update:
                    if key == "EMAIL_SMTP":
                        updated_env.append(f"EMAIL_SMTP={smtp_server}\n")
                    elif key == "EMAIL_USER":
                        updated_env.append(f"EMAIL_USER={email_user}\n")
                    updated_keys.add(key)
                else:
                    updated_env.append(line)
            else:
                updated_env.append(line)
        
        # Add any missing environment variables
        for key in env_keys_to_update - updated_keys:
            if key == "EMAIL_SMTP":
                updated_env.append(f"EMAIL_SMTP={smtp_server}\n")
            elif key == "EMAIL_USER":
                updated_env.append(f"EMAIL_USER={email_user}\n")
        
        # Write back to .env file
        with open(env_file_path, 'w') as f:
            f.writelines(updated_env)
        
        print("   ✅ Email credentials stored securely")
        return True
    except Exception as e:
        print(f"   ❌ Error storing email credentials: {e}")
        return False

def test_credentials():
    """Test the configured credentials"""
    print("\n🧪 Testing configured credentials...")
    
    config = get_config()
    
    # Test Groq
    try:
        from services.groq_service import GroqService
        groq_service = GroqService()
        if groq_service.test_connection():
            print("   ✅ Groq API connection successful")
        else:
            print("   ❌ Groq API connection failed")
    except Exception as e:
        print(f"   ❌ Groq API test error: {e}")
    
    # Test GitHub
    try:
        from services.github_service import GitHubService
        github_service = GitHubService()
        repo_stats = github_service.get_repository_stats()
        if repo_stats:
            print("   ✅ GitHub API connection successful")
        else:
            print("   ❌ GitHub API connection failed")
    except Exception as e:
        print(f"   ❌ GitHub API test error: {e}")

def show_credential_status():
    """Show current credential status"""
    print("\n📋 Current Credential Status:")
    credentials_status = check_credentials_status()
    
    for credential, status in credentials_status.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {credential}")

def main():
    """Main credential setup function"""
    print("🔐 DevSecOps AI Monitoring - Credential Setup")
    print("=" * 50)
    
    # Test password manager
    print("\n🔧 Testing password manager...")
    if setup_password_manager():
        print("   ✅ Password manager working correctly")
    else:
        print("   ❌ Password manager setup failed")
        print("   💡 Make sure you have a keyring backend installed")
        print("   💡 On Windows: pip install keyring[backends.WindowsRegistry]")
        print("   💡 On macOS: pip install keyring[backends.macOS]")
        print("   💡 On Linux: pip install keyring[backends.SecretService]")
        return False
    
    # Show current status
    show_credential_status()
    
    # Setup credentials
    success = True
    
    success &= setup_groq_credentials()
    success &= setup_github_credentials()
    success &= setup_github_repository()
    success &= setup_slack_webhook()
    success &= setup_teams_webhook()
    success &= setup_email_credentials()
    
    if success:
        print("\n🎉 Credential setup completed successfully!")
        print("\n📋 Final Status:")
        show_credential_status()
        
        # Test credentials
        test_credentials()
        
        print("\n🚀 Next steps:")
        print("   1. Run: python test_system.py")
        print("   2. Run: python main.py")
        print("   3. Access the API at: http://localhost:8000")
        
        return True
    else:
        print("\n⚠️  Some credentials failed to configure")
        print("   Please check the errors above and try again")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Setup interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)