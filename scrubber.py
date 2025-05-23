import os
import re
import requests
from git import Repo

# Configuration
base_dir = r"C:\CryptoBot"  # Directory containing CryptoBot files
github_username = "steady-mongoose"  # Your GitHub username
github_token = os.getenv("GITHUB_TOKEN")  # Retrieve token from environment variable
if not github_token:
    print("Error: GITHUB_TOKEN environment variable not set")
    exit(1)
repo_name = "CryptoBotAudit20250522"  # Repository name

# Step 1: Sanitize .env
env_file = os.path.join(base_dir, ".env")
if os.path.exists(env_file):
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        sanitized_lines = []
        for line in lines:
            if '=' in line and not line.startswith('#'):
                key, _ = line.split('=', 1)
                sanitized_lines.append(f"{key}=xxx\n")
            else:
                sanitized_lines.append(line)
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(sanitized_lines)
        print(f"Sanitized {env_file}")
    except Exception as e:
        print(f"Error sanitizing {env_file}: {e}")
else:
    print(f".env file not found at {env_file}")

# Step 2: Sanitize code files
def sanitize_code_file(file_path):
    if not file_path.endswith(('.py', '.js', '.json')):  # Include .json for configs
        return
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Replace ccxt.binance API keys and secrets
        pattern = r"ccxt\.binance\(\{['\"]apiKey['\"]: ['\"][^'\"]+['\"], ['\"]secret['\"]: ['\"][^'\"]+['\"]\}\)"
        replacement = "ccxt.binance({'apiKey': 'xxx', 'secret': 'xxx'})"
        sanitized_content = re.sub(pattern, replacement, content)
        # Replace generic API keys and tokens
        token_pattern = r"(['\"])(token|key|secret|apiKey|apiSecret)\1:\s*\1[a-zA-Z0-9_%-]+\1"
        sanitized_content = re.sub(token_pattern, r'\1\2\1: \1xxx\1', sanitized_content)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(sanitized_content)
        print(f"Sanitized {file_path}")
    except Exception as e:
        print(f"Error sanitizing {file_path}: {e}")

# Walk through files, excluding venv
exclude_dirs = [os.path.join(base_dir, "venv"), os.path.join(base_dir, "venv", "Lib", "site-packages")]
for root, _, files in os.walk(base_dir):
    if any(exclude_dir in root for exclude_dir in exclude_dirs):
        continue
    for file in files:
        sanitize_code_file(os.path.join(root, file))

# Step 3: Create .gitignore
gitignore_content = """
*.key
*.pem
.env.bak
__pycache__/
*.pyc
*.log
venv/
"""
try:
    with open(os.path.join(base_dir, ".gitignore"), 'w', encoding='utf-8') as f:
        f.write(gitignore_content)
    print("Created .gitignore")
except Exception as e:
    print(f"Error creating .gitignore: {e}")

# Step 4: Create GitHub repository
try:
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
    # Delete existing repository if it exists
    delete_response = requests.delete(f"https://api.github.com/repos/{github_username}/{repo_name}", headers=headers)
    if delete_response.status_code == 204:
        print(f"Deleted existing repository {repo_name}")
    else:
        print(f"Failed to delete existing repository: {delete_response.status_code} - {delete_response.text}")
    # Create new repository
    repo_data = {
        "name": repo_name,
        "description": "CryptoBot files for audit",
        "private": False,  # Set to True for private repo
        "auto_init": True,
        "gitignore_template": "Python"
    }
    response = requests.post("https://api.github.com/user/repos", json=repo_data, headers=headers)
    if response.status_code == 201:
        github_repo_url = response.json()["clone_url"]
        print(f"Created repository: {github_repo_url}")
    else:
        print(f"Failed to create repository: {response.text}")
        exit(1)
except Exception as e:
    print(f"Error creating GitHub repository: {e}")
    exit(1)

# Step 5: Initialize and push to GitHub
try:
    repo = Repo.init(base_dir)
    print("Initialized Git repository")
    # Explicitly set the branch to 'main' before committing
    repo.git.checkout("-b", "main")
    repo.git.add(all=True)
    repo.index.commit("Add sanitized CryptoBot files for audit")
    try:
        remote = repo.create_remote("origin", github_repo_url)
    except Exception:
        repo.delete_remote(repo.remote("origin"))
        remote = repo.create_remote("origin", github_repo_url)
    auth_url = f"https://{github_username}:{github_token}@github.com/{github_username}/{repo_name}.git"
    repo.git.push("--force", auth_url, "main")  # Force push to overwrite remote main branch
    print("Pushed to GitHub")
except Exception as e:
    print(f"Error pushing to GitHub: {e}")
    exit(1)

print(f"Repository URL: {github_repo_url}")