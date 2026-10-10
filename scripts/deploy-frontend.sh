#!/usr/bin/env bash
# Build the web app against the deployed stack and publish it to AWS Amplify Hosting (manual deploy, no Git).
set -euo pipefail
cd "$(dirname "$0")/../frontend"
out() { aws cloudformation describe-stacks --stack-name dhuaan --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
export VITE_DATA_URL="$(out DataUrl)/latest"
export VITE_API_URL="$(out ApiUrl)"
export VITE_TG_BOT="${VITE_TG_BOT:-DhuaanSmokeBot}"
npm run build
(cd dist && rm -f ../dist.zip && zip -qr ../dist.zip .)
ID_FILE=../scripts/amplify-app-id
if [ ! -s "$ID_FILE" ]; then
  aws amplify create-app --name dhuaan --platform WEB --query app.appId --output text > "$ID_FILE"
  aws amplify create-branch --app-id "$(cat "$ID_FILE")" --branch-name main >/dev/null
  aws amplify update-app --app-id "$(cat "$ID_FILE")" --custom-rules '[{"source":"</^[^.]+$|\\.(?!(css|gif|ico|jpg|jpeg|js|png|txt|svg|woff|woff2|ttf|map|json|geojson|webp|mp3|webmanifest)$)([^.]+$)/>","target":"/index.html","status":"200"}]' >/dev/null
fi
APP_ID=$(cat "$ID_FILE")
read -r JOB_ID UPLOAD_URL < <(aws amplify create-deployment --app-id "$APP_ID" --branch-name main --query '[jobId,zipUploadUrl]' --output text)
curl -sS -H "Content-Type: application/zip" --upload-file dist.zip "$UPLOAD_URL"
aws amplify start-deployment --app-id "$APP_ID" --branch-name main --job-id "$JOB_ID" >/dev/null
echo "Deploying → https://main.$APP_ID.amplifyapp.com"
