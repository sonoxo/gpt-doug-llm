"""
FREE deployment: AWS Lambda free tier (1M requests/month, 400K GB-sec)
Deploy any GPT Doug agent as a serverless function — zero cost for demo.

Usage:
  zip function.zip lambda_handler.py
  aws lambda create-function --function-name zyra-sentinel --runtime python3.11 \
    --handler lambda_handler.handler --zip-file fileb://function.zip \
    --role arn:aws:iam::YOUR-ACCOUNT:role/lambda-role
"""
import json
import sys
import os

def handler(event, context):
    """AWS Lambda handler for GPT Doug agents.
    
    Routes by path:
      /sentinel  → run_home_scan()
      /review    → review_pr(event)
      /emergency → check_emergency_feeds()
    """
    path = event.get("path", "/sentinel")
    
    if path == "/sentinel":
        from hackathon.agents.sentinel_bot import run_home_scan
        result = run_home_scan()
    elif path == "/review":
        from hackathon.agents.code_reviewer import review_pr
        pr_data = json.loads(event.get("body", "{}"))
        result = review_pr(pr_data)
    elif path == "/emergency":
        from hackathon.agents.emergency_mesh import check_emergency_feeds
        result = check_emergency_feeds()
    else:
        result = {"error": f"unknown path: {path}"}
    
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(result, indent=2),
    }


if __name__ == "__main__":
    # Local test
    print(json.dumps(handler({"path": "/sentinel"}, None), indent=2))
