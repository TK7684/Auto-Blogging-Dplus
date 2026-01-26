#!/usr/bin/env python3
"""
Test script to verify the fixes for the Post Optimization & Maintenance bot
and the Auto-Blogging Daily issues.
"""

import os
import sys
import json
from datetime import datetime

# Fix Windows console encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_vertex_model_configuration():
    """Test that the Vertex AI model configuration is correct."""
    print("=" * 60)
    print("Testing Vertex AI Model Configuration")
    print("=" * 60)
    
    from vertex_utils import get_model_name_from_env, create_vertex_model
    
    # Test with default fallback
    model_name = get_model_name_from_env("gemini-2.0-flash-exp")
    print(f"Model name from env: {model_name}")
    
    # Test model creation
    try:
        model = create_vertex_model(model_name)
        print(f"[OK] Successfully created Vertex AI model: {model_name}")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to create Vertex AI model: {e}")
        return False

def test_git_workflow():
    """Test that the git workflow configuration is correct."""
    print("\n" + "=" * 60)
    print("Testing Git Workflow Configuration")
    print("=" * 60)
    
    # Check workflow files for git pull before push
    workflow_files = [
        ".github/workflows/maintenance.yml",
        ".github/workflows/auto_blog.yml",
        ".github/workflows/auto_blog_weekly.yml"
    ]
    
    all_good = True
    for workflow_file in workflow_files:
        if os.path.exists(workflow_file):
            with open(workflow_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if "git pull --rebase origin master" in content:
                    print(f"[OK] {workflow_file} has git pull before push")
                else:
                    print(f"[FAIL] {workflow_file} missing git pull before push")
                    all_good = False
        else:
            print(f"[FAIL] {workflow_file} not found")
            all_good = False
    
    return all_good

def test_publisher_fix():
    """Test that the publisher fix is in place."""
    print("\n" + "=" * 60)
    print("Testing Publisher Fix")
    print("=" * 60)
    
    with open("publisher.py", 'r', encoding='utf-8') as f:
        content = f.read()
        if "requests.post(url, json=data, auth=self.auth)" in content:
            print("[OK] Publisher uses POST method for updates (WordPress REST API)")
            return True
        else:
            print("[FAIL] Publisher method not updated correctly")
            return False

def test_post_history():
    """Test post history tracking."""
    print("\n" + "=" * 60)
    print("Testing Post History Tracking")
    print("=" * 60)
    
    history_file = "post_history.json"
    
    # Initialize empty history if it doesn't exist
    if not os.path.exists(history_file):
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        print(f"[OK] Created empty {history_file}")
    
    # Test reading/writing to history
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        # Add a test entry
        test_key = "__test_entry__"
        history[test_key] = datetime.now().isoformat()
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4)
        
        print(f"[OK] Successfully updated {history_file}")
        
        # Clean up test entry
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        if test_key in history:
            del history[test_key]
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4)
        
        return True
    except Exception as e:
        print(f"[FAIL] Error with {history_file}: {e}")
        return False

def test_weekly_workflow():
    """Test weekly workflow specific fixes."""
    print("\n" + "=" * 60)
    print("Testing Weekly Workflow Fixes")
    print("=" * 60)
    
    with open("main.py", 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Check model consistency
    if 'secondary_model = "gemini-2.0-flash-exp"' in content:
        print("[OK] Weekly mode uses consistent model")
        model_ok = True
    else:
        print("[FAIL] Weekly mode model configuration inconsistent")
        model_ok = False
    
    # Check RSS URL updates
    if 'pantip.com' in content and 'kapook.com' in content:
        print("[OK] RSS URLs updated to more reliable sources")
        rss_ok = True
    else:
        print("[FAIL] RSS URLs not updated")
        rss_ok = False
    
    return model_ok and rss_ok

def test_rate_limiting():
    """Test rate limiting improvements."""
    print("\n" + "=" * 60)
    print("Testing Rate Limiting Improvements")
    print("=" * 60)
    
    with open("vertex_utils.py", 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Check conservative limits (updated to 5 to avoid 429 errors)
    if ('requests_per_minute=5' in content or 'requests_per_minute=8' in content) and 'requests_per_day=1500' in content:
        print("[OK] Rate limiting set to conservative values")
        rate_ok = True
    else:
        print("[FAIL] Rate limiting not conservative enough")
        rate_ok = False
    
    # Check circuit breaker buffer
    if 'rate_limiter.requests_per_day * 0.95' in content:
        print("[OK] Circuit breaker has 5% buffer")
        buffer_ok = True
    else:
        print("[FAIL] Circuit breaker missing buffer")
        buffer_ok = False
    
    return rate_ok and buffer_ok

def test_maintenance_error_handling():
    """Test maintenance error handling."""
    print("\n" + "=" * 60)
    print("Testing Maintenance Error Handling")
    print("=" * 60)
    
    with open("maintenance_agent.py", 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Check error handling
    if 'update_success = self.publisher.update_post' in content and 'try:' in content:
        print("[OK] Maintenance has proper error handling")
        error_ok = True
    else:
        print("[FAIL] Maintenance missing error handling")
        error_ok = False
    
    # Check SEO update error handling
    if 'except Exception as seo_e:' in content:
        print("[OK] SEO updates have error handling")
        seo_ok = True
    else:
        print("[FAIL] SEO updates missing error handling")
        seo_ok = False
    
    return error_ok and seo_ok

def main():
    """Run all tests."""
    print("Running tests for Auto-Blogging-DPLUS fixes...\n")
    
    results = {
        "Vertex Model Configuration": test_vertex_model_configuration(),
        "Git Workflow": test_git_workflow(),
        "Publisher Fix": test_publisher_fix(),
        "Post History": test_post_history(),
        "Weekly Workflow": test_weekly_workflow(),
        "Rate Limiting": test_rate_limiting(),
        "Maintenance Error Handling": test_maintenance_error_handling()
    }
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results.items():
        status = "[PASSED]" if result else "[FAILED]"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n[SUCCESS] All tests passed! The fixes should resolve the issues.")
    else:
        print("\n[WARNING] Some tests failed. Please review the issues above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)