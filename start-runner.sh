#!/bin/bash

# GitHub runner startup script
# Supports both PAT and GitHub App authentication

if [ -z "$GITHUB_REPO" ]; then
  echo "Error: GITHUB_REPO must be set"
  exit 1
fi

# Generate GitHub App token if using app authentication
if [ "$USE_GITHUB_APP" = "true" ]; then
  echo "Using GitHub App authentication..."
  
  python3 -c "
import base64, json, time, os
header = {'alg': 'RS256', 'typ': 'JWT'}
payload = {'iat': int(time.time()) - 60, 'exp': int(time.time()) + 600, 'iss': os.environ['GITHUB_APP_ID']}
header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
print(f'{header_b64}.{payload_b64}')
" > /tmp/jwt_unsigned.txt
  
  echo -n "$(cat /tmp/jwt_unsigned.txt)" | openssl dgst -sha256 -sign <(echo "$GITHUB_APP_PRIVATE_KEY") | base64 | tr -d '\n' | tr '/+' '_-' | tr -d '=' > /tmp/signature.txt
  JWT="$(cat /tmp/jwt_unsigned.txt).$(cat /tmp/signature.txt)"
  
  GITHUB_TOKEN=$(curl -s -X POST \
    -H "Authorization: Bearer $JWT" \
    -H "Accept: application/vnd.github.v3+json" \
    https://api.github.com/app/installations/${GITHUB_INSTALLATION_ID}/access_tokens | jq -r '.token')
fi

if [ -z "$GITHUB_TOKEN" ]; then
  echo "Error: GITHUB_TOKEN not available"
  exit 1
fi

# Get registration token
REGISTRATION_TOKEN=$(curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/$GITHUB_REPO/actions/runners/registration-token" | jq -r .token)

if [ -z "$REGISTRATION_TOKEN" ] || [ "$REGISTRATION_TOKEN" = "null" ]; then
  echo "Error: Failed to get registration token"
  exit 1
fi

# Configure runner
./config.sh --url "https://github.com/$GITHUB_REPO" \
  --token "$REGISTRATION_TOKEN" \
  --name "ecs-runner-$(hostname)" \
  --labels "ecs,mcp,cross-account" \
  --work _work \
  --unattended \
  --replace

# Run
./run.sh
