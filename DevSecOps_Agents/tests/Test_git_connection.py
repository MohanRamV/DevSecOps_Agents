#!/usr/bin/env python3
"""
GitHub Connection Test - Run from project root directory
"""

import sys
import os

def test_github_connection():
    """Test GitHub connection with detailed diagnostics"""
    print("🔍 GitHub Connection Test")
    print("=" * 50)
    
    # Test 1: Import configuration
    print("🧪 Test 1: Importing configuration...")
    try:
        from config.config import get_config
        config = get_config()
        print("✅ Configuration imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import configuration: {e}")
        print("💡 Make sure you're running this from the project root directory")
        return False
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False
    
    # Test 2: Check credentials
    print("\n🧪 Test 2: Checking stored credentials...")
    try:
        from config.config import check_credentials_status
        status = check_credentials_status()
        
        for credential, is_configured in status.items():
            status_icon = "✅" if is_configured else "❌"
            print(f"   {status_icon} {credential}")
        
        if not status['github_token']:
            print("❌ GitHub token not configured")
            return False
        if not status['github_repository']:
            print("❌ GitHub repository not configured")
            return False
        if not status['github_owner']:
            print("❌ GitHub owner not configured")
            return False
            
    except Exception as e:
        print(f"❌ Error checking credentials: {e}")
        return False
    
    # Test 3: Test GitHub API authentication
    print("\n🧪 Test 3: Testing GitHub API authentication...")
    try:
        from github import Github, GithubException
        
        token = config.github.get_token()
        github = Github(token)
        
        user = github.get_user()
        print(f"✅ Authenticated as: {user.login}")
        print(f"   Account type: {user.type}")
        print(f"   Public repos: {user.public_repos}")
        
    except GithubException as e:
        print(f"❌ GitHub authentication failed: {e}")
        print("💡 Check your GitHub token permissions")
        return False
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return False
    
    # Test 4: Test repository access
    print("\n🧪 Test 4: Testing repository access...")
    try:
        repository = config.github.get_repository()
        owner = config.github.get_owner()
        
        print(f"📁 Accessing: {owner}/{repository}")
        
        repo = github.get_repo(f"{repository}")
        print(f"✅ Repository found: {repo.full_name}")
        print(f"   Description: {repo.description or 'No description'}")
        print(f"   Language: {repo.language or 'Not specified'}")
        print(f"   Private: {'Yes' if repo.private else 'No'}")
        print(f"   Default branch: {repo.default_branch}")
        print(f"   Stars: {repo.stargazers_count}")
        
    except GithubException as e:
        print(f"❌ Repository access failed: {e}")
        print(f"   HTTP Status: {e.status}")
        
        if e.status == 404:
            print("\n💡 Repository not found (404). Possible solutions:")
            print("   1. Verify repository exists: https://github.com/MohanRamV/DevSecOps_Agents")
            print("   2. Check if repository is private and token has 'repo' scope")
            print("   3. Verify repository name spelling")
            
            # Try to list user's repositories
            print("\n🔍 Searching for your repositories...")
            try:
                repos = list(github.get_user().get_repos()[:10])
                print("   Your accessible repositories:")
                for repo in repos:
                    visibility = "🔒" if repo.private else "🌐"
                    print(f"   {visibility} {repo.full_name}")
            except:
                pass
                
        elif e.status == 403:
            print("\n💡 Access forbidden (403). Possible solutions:")
            print("   1. Token lacks required permissions")
            print("   2. Add 'repo' scope to your token")
            print("   3. Update token at: https://github.com/settings/tokens")
        
        return False
    except Exception as e:
        print(f"❌ Repository access error: {e}")
        return False
    
    # Test 5: Test GitHub service
    print("\n🧪 Test 5: Testing GitHub service...")
    try:
        from services.github_service import GitHubService
        
        github_service = GitHubService()
        repo_stats = github_service.get_repository_stats()
        
        if repo_stats:
            print("✅ GitHub service working correctly")
            print(f"   Repository: {repo_stats['full_name']}")
            print(f"   Language: {repo_stats['language']}")
            print(f"   Stars: {repo_stats['stars']}")
        else:
            print("❌ GitHub service failed to get repository stats")
            return False
            
    except Exception as e:
        print(f"❌ GitHub service error: {e}")
        return False
    
    print("\n🎉 All GitHub tests passed successfully!")
    return True

def fix_common_issues():
    """Suggest fixes for common issues"""
    print("\n🔧 Common Issue Fixes:")
    print("=" * 30)
    print("1. Run from project root: cd /path/to/DevSecOps_Agents")
    print("2. Setup credentials: python setup_credentials.py")
    print("3. Check token scopes at: https://github.com/settings/tokens")
    print("4. Required scopes: repo, workflow, read:org")
    print("5. Verify repository exists: https://github.com/MohanRamV/DevSecOps_Agents")

def main():
    """Main function"""
    try:
        if test_github_connection():
            print("\n✅ GitHub connection is working properly!")
        else:
            print("\n❌ GitHub connection has issues")
            fix_common_issues()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        fix_common_issues()

if __name__ == "__main__":
    main()