#!/bin/bash

# Test the metrics Lambda function with sample data
LAMBDA_URL="https://rfxerphsxr44xq6ltyk7y6gaki0vudaw.lambda-url.us-east-1.on.aws"
RUN_ID="test-$(date +%s)"

echo "Testing metrics Lambda with run_id: $RUN_ID"

# Test job start
echo "1. Testing /job/start..."
curl -X POST "$LAMBDA_URL/job/start" \
  -H "Content-Type: application/json" \
  -d "{
    \"run_id\": \"$RUN_ID\",
    \"repository\": \"Demo-MCP/mcp-cross-account-pipeline\",
    \"organization\": \"Demo-MCP\",
    \"branch\": \"main\",
    \"workflow_name\": \"Test Workflow\",
    \"job_name\": \"test-job\",
    \"runner_name\": \"self-hosted\",
    \"job_start_time\": \"$(date -Iseconds)\",
    \"job_status\": \"RUNNING\"
  }"

echo -e "\n\n2. Testing /job/end..."
sleep 2

# Test job end
curl -X POST "$LAMBDA_URL/job/end" \
  -H "Content-Type: application/json" \
  -d "{
    \"run_id\": \"$RUN_ID\",
    \"job_end_time\": \"$(date -Iseconds)\",
    \"job_status\": \"SUCCEEDED\",
    \"job_duration_seconds\": 5
  }"

echo -e "\n\n✅ Test completed for run_id: $RUN_ID"
echo "Run query_metrics.py to verify data was written to RDS"
