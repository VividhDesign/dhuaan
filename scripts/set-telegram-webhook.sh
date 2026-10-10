#!/usr/bin/env bash
# Point the Telegram bot at our API. Needs /dhuaan/telegram_token in SSM (put it there yourself:
#   aws ssm put-parameter --name /dhuaan/telegram_token --type SecureString --value "<token>"
# ). Creates /dhuaan/telegram_secret and /dhuaan/run_key if missing.
set -euo pipefail
for p in /dhuaan/telegram_secret /dhuaan/run_key; do
  aws ssm get-parameter --name "$p" >/dev/null 2>&1 || \
    aws ssm put-parameter --name "$p" --type SecureString --value "$(openssl rand -hex 24)" >/dev/null
done
TOKEN=$(aws ssm get-parameter --name /dhuaan/telegram_token --with-decryption --query Parameter.Value --output text)
SECRET=$(aws ssm get-parameter --name /dhuaan/telegram_secret --with-decryption --query Parameter.Value --output text)
API=$(aws cloudformation describe-stacks --stack-name dhuaan --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)
curl -s "https://api.telegram.org/bot${TOKEN}/setWebhook" -d "url=${API}/api/telegram/webhook" -d "secret_token=${SECRET}" -d 'allowed_updates=["message"]'; echo
curl -s "https://api.telegram.org/bot${TOKEN}/setMyCommands" -H 'Content-Type: application/json' -d '{"commands":[{"command":"now","description":"Smoke forecast for your area"},{"command":"school","description":"Morning indoor/outdoor call for schools"},{"command":"hotspots","description":"Top fire clusters now"},{"command":"hindi","description":"हिंदी में"},{"command":"stop","description":"Unsubscribe"}]}'; echo
