"""
GitHub Push Script for UMKM Copilot
Server-side push to GitHub using GitHub Contents API
"""
import os
import json
import base64
import requests
from datetime import datetime

REPO = "mjfendin/UMKM-COPILOT"
BRANCH = "main"
PROJECT_DIR = "/root/umkm-copilot"

# Files to exclude
EXCLUDE = ['.env', '.env.local', '.env.production', '.vercel/', 'instance/', 
           '__pycache__', '.pyc', '.db', '.DS_Store', 'venv/']

def should_include(filepath):
    for ex in EXCLUDE:
        if ex in filepath:
            return False
    return True

def get_all_files():
    """Get all project files"""
    files = []
    for root, dirs, filenames in os.walk(PROJECT_DIR):
        # Skip excluded directories
        skip = False
        for ex in EXCLUDE:
            if ex in root:
                skip = True
                break
        if skip:
            continue
        
        for filename in filenames:
            if should_include(filename):
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, PROJECT_DIR)
                if should_include(rel_path):
                    files.append(rel_path)
    return sorted(files)

def get_file_sha(token, filepath):
    """Get file SHA if it exists (for updates)"""
    url = f"https://api.github.com/repos/{REPO}/contents/{filepath}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    try:
        r = requests.get(url, headers=headers, params={"ref": BRANCH})
        if r.status_code == 200:
            return r.json().get("sha")
    except:
        pass
    return None

def upload_file(token, filepath, content, encoding="utf-8"):
    """Upload or update a file"""
    url = f"https://api.github.com/repos/{REPO}/contents/{filepath}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github+json"
    }
    
    # Get existing file SHA (for updates)
    sha = get_file_sha(token, filepath)
    
    # Prepare content
    if encoding == "utf-8":
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    else:
        encoded_content = base64.b64encode(content).decode("utf-8")
    
    body = {
        "message": f"Update {filepath}",
        "content": encoded_content,
        "branch": BRANCH
    }
    if sha:
        body["sha"] = sha
    
    r = requests.put(url, headers=headers, json=body)
    return r.status_code in [200, 201]

def push_all(token):
    """Push all files to GitHub"""
    results = {
        "success": [],
        "failed": [],
        "skipped": []
    }
    
    files = get_all_files()
    print(f"Found {len(files)} files to push")
    
    for i, filepath in enumerate(files):
        full_path = os.path.join(PROJECT_DIR, filepath)
        
        try:
            # Read file content
            with open(full_path, "rb") as f:
                content = f.read()
            
            # Try UTF-8 first
            try:
                content_str = content.decode("utf-8")
                success = upload_file(token, filepath, content_str, "utf-8")
            except UnicodeDecodeError:
                # Binary file
                success = upload_file(token, filepath, content, "base64")
            
            if success:
                results["success"].append(filepath)
                print(f"[{i+1}/{len(files)}] ✅ {filepath}")
            else:
                results["failed"].append(filepath)
                print(f"[{i+1}/{len(files)}] ❌ {filepath}")
                
        except Exception as e:
            results["failed"].append(f"{filepath}: {str(e)}")
            print(f"[{i+1}/{len(files)}] ❌ {filepath}: {e}")
    
    return results

if __name__ == "__main__":
    import sys
    token = sys.argv[1] if len(sys.argv) > 1 else None
    if not token:
        print("Usage: python3 push_github.py <GITHUB_TOKEN>")
        sys.exit(1)
    
    results = push_all(token)
    print(f"\n✅ Success: {len(results['success'])}")
    print(f"❌ Failed: {len(results['failed'])}")
    print(f"Total: {len(results['success']) + len(results['failed'])}")
