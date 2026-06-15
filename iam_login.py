#!/usr/bin/env python3
"""
Login to AgentBase CR using IAM credentials.
Gets IAM token, then fetches CR credentials, and logs into Docker.
"""
import json
import os
import sys
import subprocess
import urllib.request
import urllib.parse

# Configuration - correct URLs from greennode-agentbase-skills
IAM_TOKEN_URL = "https://iam.api.vngcloud.vn/accounts-api/v2/auth/token"
CR_API_URL = "https://agentbase.api.vngcloud.vn/cr/api/v1"

# Load IAM credentials from .greennode.json
creds_file = ".greennode.json"
if not os.path.exists(creds_file):
    print(f"Error: {creds_file} not found", file=sys.stderr)
    sys.exit(1)

with open(creds_file) as f:
    creds = json.load(f)
    client_id = creds.get("client_id", "")
    client_secret = creds.get("client_secret", "")

if not client_id or not client_secret:
    print("Error: Missing client_id or client_secret", file=sys.stderr)
    sys.exit(1)

print(f"Client ID: {client_id[:8]}...")

# Get IAM token
print("\n1. Getting IAM token...")
data = urllib.parse.urlencode({
    "client_id": client_id,
    "client_secret": client_secret,
    "grant_type": "client_credentials"
}).encode()

req = urllib.request.Request(
    IAM_TOKEN_URL,
    data=data,
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)

try:
    with urllib.request.urlopen(req) as resp:
        token_data = json.loads(resp.read())
        access_token = token_data.get("access_token")
        if not access_token:
            print("Error: No access_token in response", file=sys.stderr)
            sys.exit(1)
        print(f"   Got IAM token (expires in {token_data.get('expires_in', '?')}s)")
except Exception as e:
    print(f"Error getting token: {e}", file=sys.stderr)
    sys.exit(1)

# Get CR credentials
print("\n2. Getting CR credentials...")
req = urllib.request.Request(
    f"{CR_API_URL}/registry-credential",
    headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
)

try:
    with urllib.request.urlopen(req) as resp:
        cred_data = json.loads(resp.read())
        username = cred_data.get("username")
        secret = cred_data.get("secret")

        if not username or not secret:
            print("Error: Missing username or secret", file=sys.stderr)
            sys.exit(1)

        print(f"   Username: {username}")
        print(f"   Secret: {secret[:8]}...")
except Exception as e:
    print(f"Error getting CR credentials: {e}", file=sys.stderr)
    sys.exit(1)

# Get repo info
print("\n3. Getting repo info...")
req = urllib.request.Request(
    f"{CR_API_URL}/repository",
    headers={"Authorization": f"Bearer {access_token}"}
)

try:
    with urllib.request.urlopen(req) as resp:
        repo_data = json.loads(resp.read())
        registry_url = repo_data.get("registryUrl", "vcr.vngcloud.vn")
        repo_name = repo_data.get("name", "")
        print(f"   Registry URL: {registry_url}")
        print(f"   Repo Name: {repo_name}")
except Exception as e:
    print(f"Error getting repo: {e}", file=sys.stderr)
    registry_url = "vcr.vngcloud.vn"
    repo_name = client_id  # fallback

# Docker login
print(f"\n4. Docker login to {registry_url}...")
cmd = ["docker", "login", registry_url, "-u", username, "--password-stdin"]
proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
stdout, _ = proc.communicate(input=secret)
print(stdout)

if proc.returncode != 0:
    print("\n❌ Docker login FAILED", file=sys.stderr)
    sys.exit(1)

print("\n✅ Docker login SUCCESS!")

# Tag and push instructions
print("\n" + "="*50)
print("NEXT STEPS:")
print("="*50)
print(f"\n# Tag image:")
print(f"docker tag contract-review:v2 {registry_url}/{repo_name}/contract-review:v2")
print(f"\n# Push image:")
print(f"docker push {registry_url}/{repo_name}/contract-review:v2")