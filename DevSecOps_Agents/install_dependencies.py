#!/usr/bin/env python3
"""
Dependency Installation Script for DevSecOps AI Monitoring System
This script handles the installation of dependencies with proper error handling.
"""

import subprocess
import sys
import os
from typing import List, Tuple

def run_command(command: List[str], description: str) -> Tuple[bool, str]:
    """Run a command and return success status and output"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"   ✅ {description} completed successfully")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"   ❌ {description} failed: {e}")
        print(f"   Error output: {e.stderr}")
        return False, e.stderr
    except Exception as e:
        print(f"   ❌ {description} failed: {e}")
        return False, str(e)

def install_numpy_fix():
    """Install numpy with proper error handling"""
    print("\n📦 Installing numpy (with fallback options)...")
    
    # Try different numpy versions
    numpy_versions = [
        "numpy==1.24.3",  # Pre-compiled version
        "numpy==1.23.5",  # Older stable version
        "numpy",           # Latest version
    ]
    
    for version in numpy_versions:
        success, output = run_command(
            [sys.executable, "-m", "pip", "install", version],
            f"Installing {version}"
        )
        if success:
            return True
    
    print("   ❌ All numpy installation attempts failed")
    print("   💡 Try installing Visual Studio Build Tools on Windows")
    print("   💡 Or use: pip install --only-binary=all numpy")
    return False

def install_requirements():
    """Install requirements with proper error handling"""
    print("\n📦 Installing Python dependencies...")
    
    # First, try to install numpy separately
    if not install_numpy_fix():
        print("   ⚠️  Continuing with other dependencies...")
    
    # Install other dependencies
    success, output = run_command(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        "Installing requirements.txt"
    )
    
    if not success:
        print("   💡 Try installing dependencies one by one:")
        print("   pip install groq langchain fastapi uvicorn")
        print("   pip install PyGithub kubernetes docker")
        print("   pip install keyring cryptography")
    
    return success

def install_keyring_backend():
    """Install appropriate keyring backend for the platform"""
    print("\n🔐 Installing keyring backend...")
    
    import platform
    system = platform.system().lower()
    
    if system == "windows":
        success, output = run_command(
            [sys.executable, "-m", "pip", "install", "keyring[backends.WindowsRegistry]"],
            "Installing Windows keyring backend"
        )
    elif system == "darwin":  # macOS
        success, output = run_command(
            [sys.executable, "-m", "pip", "install", "keyring[backends.macOS]"],
            "Installing macOS keyring backend"
        )
    else:  # Linux
        success, output = run_command(
            [sys.executable, "-m", "pip", "install", "keyring[backends.SecretService]"],
            "Installing Linux keyring backend"
        )
    
    return success

def main():
    """Main installation function"""
    print("🚀 DevSecOps AI Monitoring - Dependency Installation")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("requirements.txt"):
        print("❌ requirements.txt not found. Please run this script from the DevSecOps_Agents directory.")
        return False
    
    # Install keyring backend first
    install_keyring_backend()
    
    # Install requirements
    success = install_requirements()
    
    if success:
        print("\n🎉 Dependency installation completed successfully!")
        print("\n📋 Next steps:")
        print("   1. Run: python setup_credentials.py")
        print("   2. Run: python test_system.py")
        print("   3. Run: python main.py")
        return True
    else:
        print("\n⚠️  Some dependencies failed to install")
        print("   Please check the errors above and try again")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Installation interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1) 