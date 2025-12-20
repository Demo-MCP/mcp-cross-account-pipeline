#!/bin/bash

# GitHub runner startup script
# Expects GITHUB_TOKEN and GITHUB_REPO environment variables

if [ -z "$GITHUB_TOKEN" ] || [ -z "$GITHUB_REPO" ]; then
  echo "Error: GITHUB_TOKEN and GITHUB_REPO must be set"
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
