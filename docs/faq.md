# Hard questions, straight answers

**Is the Smoke Index a PM2.5 forecast?**
No. It's a relative 0–100 index of how much farm-fire smoke the wind is carrying over a place, built from fire intensity (FRP), distance, time and mixing height. PM2.5 also includes traffic, dust and industry. We say "relative" everywhere, in the app, the bot and the alerts.

**How do you know it works?**
Two ways. First, the replay of 31 Oct 2025 uses only the fires known at 20:30 IST and the winds as forecast then. It predicted smoke over north Delhi from about 03:30 on 1 Nov. Observed: Delhi's AQI rose from 218 to 251 that day, and the worst station was Wazirpur in north-west Delhi, the side the plume reached first ([CPCB via The Daily Guardian](https://thedailyguardian.com/india/delhi-aqi-on-novenmebr-1-2025-delhi-breathes-polluted-air-again-aqi-touches-251-mark-677349/)). Second, the physics is unit-tested: wind direction convention, straight-line advection, kernel normalisation and calibration. One day is not a validation study. The next step is a season-long backtest against CPCB hourly data.

**Why not just use an AQI app?**
AQI apps tell you the air is bad when you're already breathing it, and they can't tell you why. Dhuaan tells you hours ahead, says which fires the smoke comes from, and reaches you on Telegram without opening an app.

**Couldn't ChatGPT or Gemini do this?**
No. It needs fresh satellite detections every few hours, a wind-field model and a pipeline that runs at 3 AM and messages people. A chatbot doesn't watch the sky.

**Today Delhi shows "no smoke". Is it broken?**
No. On 10 Oct 2026 most fires were in Pakistan Punjab and the winds were blowing west. That is the correct answer for that day, and the replay shows what a bad night looks like.

**Aren't you blaming farmers?**
No. We never identify a farm or a farmer. Clusters are ~11 km cells named after the nearest district HQ. The hotspot ranking is for sending help (residue machinery, field teams) where it reduces the most exposure.

**Why include fires in Pakistan?**
Smoke doesn't stop at borders. On 31 Oct 2025, 577 of 1,209 detections were across the border, and some of that smoke reached Amritsar and Jalandhar first.

**Why Telegram and not WhatsApp?**
The WhatsApp Business API needs Meta business verification, which isn't possible in a weekend. The alert engine is channel-agnostic: it already sends Telegram and email (SNS), and WhatsApp through AWS End User Messaging Social is the next channel.

**What does it cost to run?**
Almost nothing. Six Lambda runs every 3 hours, a few MB in S3, on-demand DynamoDB and API Gateway requests. The model takes under 2 seconds per run.

**What breaks it?**
Fires lit after the afternoon satellite pass are only seen on the next pass. Cloud cover hides fires. Single-level winds miss vertical wind shear. Fixed decay and spread are simplifications. These are listed on the About page.

**Why didn't you use Bedrock more?**
The forecast is physics, and an LLM shouldn't make up smoke numbers. Bulletins are generated from the run's own numbers. We planned Bedrock (Amazon Nova) only to polish the wording, and our new AWS account still had Bedrock locked during the event.
