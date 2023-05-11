# UX for EdmonBrain

This is an exploration on how to interact with the LLM tools in this repo

## Deploy to Cloud Run

### Add secrets to Secret Manager

* OPENAI_API_KEY
* DISCORD_URL

### Run Cloud Build

Run from the root directory of this repository

```
gcloud builds submit --config cloudbuild.yaml . \
  --substitutions=_IMAGE_NAME=edmonbrain,_SERVICE_NAME=edmonbrain-app,_REGION=europe-west3,_GCS_BUCKET=bucket-to-store-vectorstore
```

Or preferably set up a Cloud Build Trigger for each git commit


## WebApp

Can be used to configure the vectorstore index

Run locally:

```
python3 ./webapp/app.py   
```

## Discord bot

can only accept inputs and outputs

```
echo 'export DISCORD_URL=https://discord.com/api/webhooks/12345/xxxx' >> ~/.zshenv
source ~/.zshenv
```

## Slackbot

Can only accept inputs and outputs

```
echo 'export SLACK_BOT_TOKEN=XXXX' >> ~/.zshenv
source ~/.zshenv
```