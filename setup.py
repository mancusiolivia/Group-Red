#!/usr/bin/env python3
"""
Master setup script for Essay Testing System
Runs all database migrations and setup steps in one command.

Usage:
    python setup.py
    or
    python3 setup.py
"""
import sys
import os
import subprocess

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def run_script(script_path, description):
    """Run a Python script and handle errors"""
    print(f"\n{'='*60}")
    print(f"Step: {description}")
    print(f"{'='*60}")
    
    try:
        # Use the same Python interpreter
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=project_root,
            check=True,
            capture_output=False
        )
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error running {description}: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def check_env_file(skip_warning=False):
    """Check if .env file exists"""
    if skip_warning:
        return True
    env_path = os.path.join(project_root, ".env")
    if not os.path.exists(env_path):
        print("\n⚠️  WARNING: .env file not found!")
        print("Please create a .env file with your API key:")
        print("   TOGETHER_AI_API_KEY=your_api_key_here")
        print("\nContinuing with setup, but the server won't work without the API key.")
        return False
    return True

def main():
    """Run all setup steps"""
    print("="*60)
    print("Essay Testing System - Master Setup Script")
    print("="*60)
    print("\nThis script will:")
    print("  1. Initialize the database")
    print("  2. Run all database migrations")
    print("  3. Seed initial user data")
    print("  4. Assign classes to students")
    print("\nAll steps are idempotent (safe to run multiple times).")
    
    # Check for .env file (skip warning when run from setup.bat or --skip-env-check flag)
    skip_env_check = (
        '--skip-env-check' in sys.argv or 
        os.environ.get('SKIP_ENV_CHECK', '').lower() == 'true'
    )
    check_env_file(skip_warning=skip_env_check)
    
    # Define all setup steps
    setup_steps = [
        ("server/database/init.py", "Initialize database schema"),
        ("server/database/add_class_name_column.py", "Add class_name column migration"),
        ("server/database/add_time_limit_fields.py", "Add time limit fields migration"),
        ("server/database/add_instructor_grading_fields.py", "Add instructor grading fields migration"),
        ("server/database/add_number_of_questions_column.py", "Add number_of_questions column migration"),
        ("server/database/add_prevent_tab_switching.py", "Add prevent_tab_switching column migration"),
        ("server/database/seed_data.py", "Seed initial user data"),
        ("server/database/assign_classes_to_students.py", "Assign classes to students"),
    ]
    
    # Run all steps
    failed_steps = []
    for script_path, description in setup_steps:
        full_path = os.path.join(project_root, script_path)
        
        # Skip if script doesn't exist (for optional migrations)
        if not os.path.exists(full_path):
            print(f"\n⚠️  Skipping {description} (script not found: {script_path})")
            continue
        
        success = run_script(full_path, description)
        if not success:
            failed_steps.append(description)
    
    # Summary
    print("\n" + "="*60)
    print("Setup Summary")
    print("="*60)
    
    if failed_steps:
        print(f"\n✗ Setup completed with {len(failed_steps)} error(s):")
        for step in failed_steps:
            print(f"  - {step}")
        print("\nPlease review the errors above and fix them before starting the server.")
        sys.exit(1)
    else:
        print("\n✓ All setup steps completed successfully!")
        
        # Get database path for DBeaver instructions
        database_path = os.path.join(project_root, "data", "app.db")
        
        print("\n" + "="*60)
        print("⚠️  REQUIRED: DBeaver Database Connection")
        print("="*60)
        print("\n⚠️  IMPORTANT: You MUST connect to the database using DBeaver")
        print("   for the program to work properly!")
        print("\nDatabase location:")
        print(f"   {database_path}")
        print("\nDBeaver Connection Steps:")
        print("  1. Open DBeaver")
        print("  2. Click Database -> New Database Connection")
        print("  3. Choose SQLite")
        print("  4. Click Next")
        print("  5. For Database file, click Browse")
        print("  6. Navigate to the 'data' folder in your project directory")
        print("  7. Select 'app.db'")
        print("  8. Click Finish")
        print("\n" + "="*60)
        
        print("\nNext steps:")
        print("  1. Connect to database using DBeaver (REQUIRED - see above)")
        print("  2. Create a .env file with your API key:")
        print("     TOGETHER_AI_API_KEY=your_api_key_here")
        print("  3. Start the server:")
        print("     python run_server.py")
        print("     or")
        print("     python3 run_server.py")
        print("\nThe server will be available at: http://localhost:8000")
        print("\nDefault login credentials:")
        print("  Username: admin")
        print("  Password: admin123")
        print("  (See CREDENTIALS.txt for full list)")

if __name__ == "__main__":
    main()
