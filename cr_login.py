#!/usr/bin/env python3
"""
Simple script to login to AgentBase Container Registry without jq
"""
import json
import os
import sys
import requests
from base64 import b64encode

# Load credentials
GREENNODE_DIR = ".greennode"
creds_file = os.path.join(GREENNODE_DIR, "credentials.json")

if os.path.exists(creds_file):
    with open(creds_file) as f:
        creds = json.load(f)
        client_id = creds.get("client_id", "")
        client_secret = creds.get("client_secret", "")
else:
    # Try .greennode.json
    greennode_file = ".greennode.json"
    if os.path.exists(greennode_file):
        with open(greennode_file) as f:
            creds = json.load(f)
            client_id = creds.get("client_id", "")
            client_secret = creds.get("client_secret", "")
    else:
        print("Error: No credentials file found", file=sys.stderr)
        sys.exit(1)

if not client_id or not client_secret:
    print("Error: Missing client_id or client_secret", file=sys.stderr)
    sys.exit(1)

# Get IAM token
print("Getting IAM token...")
resp = requests.post(
    "https://iamapi.vngcloud.vn/identity-api/v1/oauth2/token",
    data={
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    },
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)

if resp.status_code != 200:
    print(f"Error getting token: {resp.status_code} - {resp.text}", file=sys.stderr)
    sys.exit(1)

token_data = resp.json()
access_token = token_data.get("access_token")
if not access_token:
    print("Error: No access_token in response", file=sys.stderr)
    sys.exit(1)

print(f"Got IAM token (expires in {token_data.get('expires_in', '?')}s)")

# Get CR credentials
print("Getting CR credentials...")
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

resp = requests.get(
    "https://agentbase.api.vngcloud.vn/cr/api/v1/registry-credential",
    headers=headers
)

if resp.status_code != 200:
    print(f"Error getting CR credentials: {resp.status_code} - {resp.text}", file=sys.stderr)
    sys.exit(1)

cred_data = resp.json()
username = cred_data.get("username")
secret = cred_data.get("secret")

if not username or not secret:
    print("Error: Missing username or secret in response", file=sys.stderr)
    print(json.dumps(cred_data, indent=2), file=sys.stderr)
    sys.exit(1)

print(f"Username: {username}")
print(f"Secret: {secret[:8]}...")

# Get repo info
print("\nGetting repo info...")
resp = requests.get(
    "https://agentbase.api.vngcloud.vn/cr/api/v1/repository",
    headers=headers
)

if resp.status_code != 200:
    print(f"Error getting repo: {resp.status_code} - {resp.text}", file=sys.stderr)
    sys.exit(1)

repo_data = resp.json()
registry_url = repo_data.get("registryUrl", "vcr.vngcloud.vn")
repo_name = repo_data.get("name", "")

print(f"Registry URL: {registry_url}")
print(f"Repo Name: {repo_name}")

# Docker login
print("\n=== Docker Login ===")
print(f"Run this command to login:")
print(f"docker login {registry_url} -u {username} -p {secret}")

# Try to login automatically
print("\nTrying auto-login...")
login_cmd = f"docker login {registry_url} -u {username} --password-stdin"
import subprocess
proc = subprocess.Popen(
    login_cmd.split() + [secret],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)
stdout, _ = proc.communicate()
print(stdout)
if proc.returncode == 0:
    print("\n✅ Docker login SUCCESS!")
else:
    print("\n⚠️ Docker login failed, please run manually:")
    print(f"echo {secret} | docker login {registry_url} -u {username} --password-stdin")

print("\n=== Next Steps ===")
print(f"1. Build: docker build --platform linux/amd64 -t contract-review:v2 .")
print(f"2. Tag: docker tag contract-review:v2 {registry_url}/{repo_name}/contract-review:v2")
print(f"3. Push: docker push {registry_url}/{repo_name}/contract-review:v2")