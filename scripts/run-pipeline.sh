#!/usr/bin/env bash
# Start one pipeline run now and wait for it to finish.
set -euo pipefail
ARN=$(aws cloudformation describe-stacks --stack-name dhuaan --query "Stacks[0].Outputs[?OutputKey=='PipelineArn'].OutputValue" --output text)
EXEC=$(aws stepfunctions start-execution --state-machine-arn "$ARN" --name "manual-$(date +%s)" --query executionArn --output text)
echo "started $EXEC"
while true; do
  S=$(aws stepfunctions describe-execution --execution-arn "$EXEC" --query status --output text)
  [ "$S" != "RUNNING" ] && break
  sleep 5
done
echo "status: $S"
DATA=$(aws cloudformation describe-stacks --stack-name dhuaan --query "Stacks[0].Outputs[?OutputKey=='DataUrl'].OutputValue" --output text)
curl -s "$DATA/latest/meta.json"; echo
