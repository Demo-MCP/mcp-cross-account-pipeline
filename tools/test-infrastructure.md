# Test Infrastructure

This is a test CloudFormation template to demonstrate the MCP pipeline.

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Test stack for MCP analysis'

Resources:
  TestBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub 'mcp-test-bucket-${AWS::AccountId}'
      
  TestRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
```

This template creates a simple S3 bucket and IAM role for testing.
