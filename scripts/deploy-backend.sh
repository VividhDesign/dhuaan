#!/usr/bin/env bash
# Build and deploy the Dhuaan backend stack (first time: run with --guided).
set -euo pipefail
cd "$(dirname "$0")/../backend"
SAM="${SAM:-$(command -v sam || echo "$HOME/.local/bin/sam")}"
"$SAM" build
"$SAM" deploy "$@"
aws cloudformation describe-stacks --stack-name dhuaan --query "Stacks[0].Outputs" --output table
