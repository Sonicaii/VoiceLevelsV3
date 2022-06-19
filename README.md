# Voice Levels Rewrite Version 3
[![Discord 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Discord.py](https://img.shields.io/badge/discord.py-%20v2-yellow.svg)](https://github.com/Rapptz/discord.py/)

The new and improved **Voice Levels** discord.py bot with slash commands and Postgres database

#### Requirements
Run `pipenv`/`pip install -r requirements.txt`
- discord.py version 2.0
    - (Currently in active development, with breaking changes from 1.0, consider using pipenv if you have the original discord.py installed)
- psycopg2
- python-dotenv
##### Other requirements
- Postgres database

## Hosting on Heroku:

1. Make Heroku account and deploy!<br />[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/Sonicaii/VoiceLevelsV3/)
2. Install the [Heroku Postgres Add-on](https://dashboard.heroku.com/provision-addon?addonServiceId=6c67493d-8fc2-4cd4-9161-4f1ec11cbe69&planId=062a1cc7-f79f-404c-9f91-135f70175577) for the database
3. Create a discord application on [Discord Developer Portal](https://discord.com/developers/applications)
4. Get new bot token from Discord Developer Portal -> Your Application -> Bot -> (Add bot if you don't have one) / get / reset token
5. Add new enviornment variable on heroku as `BOT_TOKEN` with your bot token and `BOT_PREFIX` with your desired prefix. [Heroku Application -> Settings -> Config Vars](https://dashboard.heroku.com/apps/). `DATABASE_URL` should be already set from installing the Add-on.
6. Enable [privileged intents](https://discord.com/developers/applications/). From Your Application -> Bot -> Privileged Gateway Intents, enable `PRESENCE INTENT`, `SERVER MEMBERS INTENT` and `MESSAGE CONTENT INTENT`
7. enable python dyno to start the bot in the resources tab
8. Invite to your server(s) using this link, with your bot id:<br />
> `https://discord.com/api/oauth2/authorize?client_id=`**`YOUR_BOT_ID`**`&permissions=2684456000&scope=applications.commands%20bot`<br />Get ID under [applications -> Application ID](https://discord.com/developers/applications/)



## Hosting on local machine / server
1. Download code
2. Create a discord application on [Discord Developer Portal](https://discord.com/developers/applications)
4. Get new bot token from Discord Developer Portal -> Your Application -> Bot -> (Add bot if you don't have one) / get / reset token
3. Edit .env file or environment variables, setting `DATABASE_URL` to your postgres database (uses ssl connection), `BOT_TOKEN` and `BOT_PREFIX` to your token and preferred default prefix
4. Enable [privileged intents](https://discord.com/developers/applications/). From Your Application -> Bot -> Privileged Gateway Intents, enable `PRESENCE INTENT`, `SERVER MEMBERS INTENT` and `MESSAGE CONTENT INTENT`
5. Run `init.py` to start bot or `pipenv run init.py` (see below for instructions to run as a service in background)
6. Invite to your server(s) using this link, with your bot id:<br />
> `https://discord.com/api/oauth2/authorize?client_id=`**`YOUR_BOT_ID`**`&permissions=2684456000&scope=applications.commands%20bot`<br />Get ID under [applications -> Application ID](https://discord.com/developers/applications/)

### Running as linux service
> (tested on ubuntu 22.04)
1. edit .env, `BOT_PRINT=no` So it does not clog up systemctl output, you can get the logs of the bot from step 5 below.
2. Make a new service file.
> `sudo nano /lib/systemd/system/voicelevels.service`
```ini
[Unit]
Description=Voice Levels bot run service
After=multi-user.target

[Service]
Type=simple
Environment=PYTHONUNBUFFERED=1
WorkingDirectory=PATH TO BOT FOLDER
ExecStart=/usr/bin/python3 PATH TO YOUR init.py

[Install]
WantedBy=multi-user.target
```
3. Give proper permissions for service type files
> `sudo chmod 644 /lib/systemd/system/voicelevels.service`
4. Refresh system services list, enable and start.
> `sudo systemctl daemon-reload && sudo systemctl enable voicelevels.service && sudo systemctl start voicelevels.service`
5. Check the service `sudo systemctl status voicelevels.service` and `tail discord.log`
6. Stop and restart as you wish with `sudo systemctl stop voicelevels.service` and `sudo systemctl restart voicelevels.service`
