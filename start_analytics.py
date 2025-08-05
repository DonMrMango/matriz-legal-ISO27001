#!/usr/bin/env python3
"""
Easy startup script for Matriz Legal Analytics System
"""

import os
import sys
import subprocess
import time

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import flask
        import flask_cors
        import sqlite3
        print("✅ Dependencies check passed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Install with: pip install -r requirements.txt")
        return False

def check_database():
    """Check if database exists"""
    db_path = "data_repository/repositorio.db"
    if os.path.exists(db_path):
        print("✅ Database found")
        return True
    else:
        print(f"❌ Database not found at {db_path}")
        return False

def check_env_file():
    """Check if .env file exists"""
    if os.path.exists(".env"):
        print("✅ Environment file found")
        return True
    else:
        print("❌ .env file not found")
        print("💡 Creating default .env file...")
        
        env_content = """# Admin token for analytics dashboard
ADMIN_TOKEN=admin_daniel_2024

# API Keys (add your actual keys here)
GROQ_API_KEY=your_groq_api_key_here
OPENAI_API_KEY=your_openai_api_key_here"""
        
        with open(".env", "w") as f:
            f.write(env_content)
        
        print("✅ Default .env file created")
        return True

def start_server():
    """Start the analytics server"""
    print("\n🚀 Starting Matriz Legal Analytics System...")
    print("📊 Admin Dashboard: http://localhost:5002/admin")
    print("🔑 Admin Token: admin_daniel_2024")
    print("⏹️  Press Ctrl+C to stop\n")
    
    try:
        # Start the server
        subprocess.run([sys.executable, "api/index.py"], check=True)
    except KeyboardInterrupt:
        print("\n✅ Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed to start: {e}")

def main():
    print("🔧 Matriz Legal Analytics System - Startup Check")
    print("=" * 50)
    
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Run checks
    deps_ok = check_dependencies()
    db_ok = check_database()
    env_ok = check_env_file()
    
    if not all([deps_ok, db_ok, env_ok]):
        print("\n❌ Pre-flight checks failed. Please fix the issues above.")
        return
    
    print("\n✅ All checks passed!")
    print("\n" + "=" * 50)
    
    # Start server
    start_server()

if __name__ == "__main__":
    main()