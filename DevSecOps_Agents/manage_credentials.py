#!/usr/bin/env python3
"""
Credential Management Script for DevSecOps AI Monitoring System
This script helps users view, update, and delete their stored credentials.
"""

import getpass
import sys
import os
from typing import Optional

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config import get_config, check_credentials_status, setup_password_manager
import keyring

def show_credential_status():
    """Show current credential status"""
    print("\n📋 Current Credential Status:")
    credentials_status = check_credentials_status()
    
    for credential, status in credentials_status.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {credential}")

def view_stored_credentials():
    """View stored credentials (masked)"""
    print("\n🔍 Stored Credentials (masked):")
    
    config = get_config()
    
    # Check each credential
    credentials = [
        ("Groq API Key", config.groq.get_api_key()),
        ("GitHub Token", config.github.get_token()),
        ("GitHub Repository", config.github.get_repository()),
        ("GitHub Owner", config.github.get_owner()),
        ("Slack Webhook", config.notifications.get_slack_webhook()),
        ("Teams Webhook", config.notifications.get_teams_webhook()),
        ("Email Password", config.notifications.get_email_password()),
    ]
    
    for name, value in credentials:
        if value:
            # Show first 4 and last 4 characters for sensitive data
            if "password" in name.lower() or "key" in name.lower() or "token" in name.lower() or "webhook" in name.lower():
                masked = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "*" * len(value)
                print(f"   {name}: {masked}")
            else:
                # For repository and owner, show full value as they're not sensitive
                print(f"   {name}: {value}")
        else:
            print(f"   {name}: Not stored")

def update_groq_credentials():
    """Update Groq API credentials"""
    print("\n🔑 Updating Groq API credentials...")
    
    config = get_config()
    
    # Get new API key
    print("   📝 Please enter your new Groq API key:")
    print("   💡 Get your API key from: https://console.groq.com/keys")
    api_key = getpass.getpass("   Groq API Key: ").strip()
    
    if not api_key:
        print("   ❌ No API key provided")
        return False
    
    # Store in password manager
    try:
        config.groq.store_api_key(api_key)
        print("   ✅ Groq API key updated successfully")
        return True
    except Exception as e:
        print(f"   ❌ Error storing API key: {e}")
        return False

def update_github_credentials():
    """Update GitHub API credentials"""
    print("\n🔑 Updating GitHub API credentials...")
    
    config = get_config()
    
    # Get new token
    print("   📝 Please enter your new GitHub Personal Access Token:")
    print("   💡 Create a token at: https://github.com/settings/tokens")
    print("   🔧 Required permissions: repo, workflow, read:org")
    token = getpass.getpass("   GitHub Token: ").strip()
    
    if not token:
        print("   ❌ No token provided")
        return False
    
    # Store in password manager
    try:
        config.github.store_token(token)
        print("   ✅ GitHub token updated successfully")
        return True
    except Exception as e:
        print(f"   ❌ Error storing token: {e}")
        return False

def update_github_repository():
    """Update GitHub repository information"""
    print("\n🔑 Updating GitHub repository information...")
    
    config = get_config()
    
    # Get repository information
    print("   📝 Please enter your GitHub repository:")
    print("   💡 Format: username/repository-name")
    repository = input("   Repository (e.g., myusername/myproject): ").strip()
    
    if not repository:
        print("   ❌ No repository provided")
        return False
    
    print("   📝 Please enter your GitHub username:")
    owner = input("   Username: ").strip()
    
    if not owner:
        print("   ❌ No username provided")
        return False
    
    # Store in keyring
    try:
        config.github.store_repository(repository)
        config.github.store_owner(owner)
        print("   ✅ GitHub repository information updated successfully")
        return True
    except Exception as e:
        print(f"   ❌ Error storing repository information: {e}")
        return False

def delete_credential(credential_name: str):
    """Delete a specific credential"""
    print(f"\n🗑️  Deleting {credential_name}...")
    
    try:
        keyring.delete_password("devsecops_monitoring", credential_name.lower().replace(" ", "_"))
        print(f"   ✅ {credential_name} deleted successfully")
        return True
    except Exception as e:
        print(f"   ❌ Error deleting {credential_name}: {e}")
        return False

def clear_all_credentials():
    """Clear all stored credentials"""
    print("\n🗑️  Clearing all stored credentials...")
    
    credentials = [
        "groq_api_key",
        "github_token", 
        "github_repository",
        "github_owner",
        "slack_webhook",
        "teams_webhook",
        "email_password"
    ]
    
    success = True
    for credential in credentials:
        try:
            keyring.delete_password("devsecops_monitoring", credential)
            print(f"   ✅ Deleted {credential}")
        except Exception as e:
            print(f"   ❌ Error deleting {credential}: {e}")
            success = False
    
    if success:
        print("   ✅ All credentials cleared successfully")
    else:
        print("   ⚠️  Some credentials could not be cleared")
    
    return success

def export_credentials():
    """Export credentials to environment variables (for backup)"""
    print("\n📤 Exporting credentials to environment variables...")
    
    config = get_config()
    
    env_vars = []
    
    # Get all credentials
    groq_key = config.groq.get_api_key()
    github_token = config.github.get_token()
    github_repository = config.github.get_repository()
    github_owner = config.github.get_owner()
    slack_webhook = config.notifications.get_slack_webhook()
    teams_webhook = config.notifications.get_teams_webhook()
    email_password = config.notifications.get_email_password()
    
    if groq_key:
        env_vars.append(f"GROQ_API_KEY={groq_key}")
    if github_token:
        env_vars.append(f"GITHUB_TOKEN={github_token}")
    if github_repository:
        env_vars.append(f"GITHUB_REPOSITORY={github_repository}")
    if github_owner:
        env_vars.append(f"GITHUB_OWNER={github_owner}")
    if slack_webhook:
        env_vars.append(f"SLACK_WEBHOOK={slack_webhook}")
    if teams_webhook:
        env_vars.append(f"TEAMS_WEBHOOK={teams_webhook}")
    if email_password:
        env_vars.append(f"EMAIL_PASSWORD={email_password}")
    
    if env_vars:
        print("   📝 Add these to your .env file:")
        for var in env_vars:
            print(f"   {var}")
    else:
        print("   ⚠️  No credentials to export")
    
    return True

def main():
    """Main credential management function"""
    print("🔐 DevSecOps AI Monitoring - Credential Management")
    print("=" * 60)
    
    # Test password manager
    if not setup_password_manager():
        print("❌ Password manager not working. Please check your keyring installation.")
        return False
    
    while True:
        print("\n📋 Available Actions:")
        print("   1. Show credential status")
        print("   2. View stored credentials (masked)")
        print("   3. Update Groq API key")
        print("   4. Update GitHub token")
        print("   5. Update GitHub repository info")
        print("   6. Delete specific credential")
        print("   7. Clear all credentials")
        print("   8. Export credentials to .env")
        print("   9. Exit")
        
        choice = input("\n🔧 Select an action (1-9): ").strip()
        
        if choice == "1":
            show_credential_status()
        elif choice == "2":
            view_stored_credentials()
        elif choice == "3":
            update_groq_credentials()
        elif choice == "4":
            update_github_credentials()
        elif choice == "5":
            update_github_repository()
        elif choice == "6":
            print("\n🗑️  Available credentials to delete:")
            print("   1. Groq API Key")
            print("   2. GitHub Token")
            print("   3. GitHub Repository")
            print("   4. GitHub Owner")
            print("   5. Slack Webhook")
            print("   6. Teams Webhook")
            print("   7. Email Password")
            
            cred_choice = input("   Select credential to delete (1-7): ").strip()
            
            credential_map = {
                "1": "groq_api_key",
                "2": "github_token",
                "3": "github_repository",
                "4": "github_owner",
                "5": "slack_webhook",
                "6": "teams_webhook",
                "7": "email_password"
            }
            
            if cred_choice in credential_map:
                delete_credential(credential_map[cred_choice])
            else:
                print("   ❌ Invalid choice")
        elif choice == "7":
            confirm = input("   ⚠️  Are you sure you want to clear ALL credentials? (y/N): ").strip().lower()
            if confirm == "y":
                clear_all_credentials()
            else:
                print("   ⏭️  Operation cancelled")
        elif choice == "8":
            export_credentials()
        elif choice == "9":
            print("\n👋 Goodbye!")
            break
        else:
            print("   ❌ Invalid choice. Please select 1-9.")
        
        input("\n   Press Enter to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Management interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)