# Voice Levels Rewrite Version 3
[![Discord 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Discord.py](https://img.shields.io/badge/discord.py-%20v2-yellow.svg)](https://github.com/Rapptz/discord.py/)
[![Pull Requests](https://img.shields.io/github/issues-pr/Sonicaii/VoiceLevelsV3)](https://github.com/Sonicaii/VoiceLevelsV3/pulls)
[![Issues](https://img.shields.io/github/issues/Sonicaii/VoiceLevelsV3)](https://github.com/Sonicaii/VoiceLevelsV3/issues)
[![Size](https://img.shields.io/github/repo-size/Sonicaii/VoiceLevelsV3)](/)

The new and improved **Voice Levels** discord.py bot with slash commands and Postgres database

### Requirements
Run `pip install -r requirements.txt`

<i><code>discord.py</code> v2 is currently in active development, with breaking changes from 1.0 &mdash; 
    <a href="https://discordpy.readthedocs.io/en/latest/migrating.html">see details here</a><br />Consider using a virtual environment if you are running multiple bots on different discord.py versions</i>
<details open><summary>&nbsp;<i>Packages:</i></summary>
    <ul>
        <li>
            <code>discord.py</code> <i>version 2.0</i><br />
        </li>
        <li><code>psycopg2</code></li>
        <li><code>python-dotenv</code></li>
    </ul>
    <b>Other requirements</b>
    <ul>
        <li><code>Postgres database</code></li>
    </ul>
</details>

# Bot usage options and instructions
These instructions shouldn't be too hard. If you need any help, contact me, details at the bottom.
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
3. Use make_env.py to create an .env file or set environment variables, set `DATABASE_URL` to your postgres database (uses ssl connection), `BOT_TOKEN` and `BOT_PREFIX` to your token and preferred default prefix
4. Enable [privileged intents](https://discord.com/developers/applications/). From Your Application -> Bot -> Privileged Gateway Intents, enable `PRESENCE INTENT`, `SERVER MEMBERS INTENT` and `MESSAGE CONTENT INTENT`
5. Run `init.py` to start bot (see below for instructions to run as a service in background)
6. Invite to your server(s) using this link, with your bot id:<br />
> `https://discord.com/api/oauth2/authorize?client_id=`**`YOUR_BOT_ID`**`&permissions=2684456000&scope=applications.commands%20bot`<br />Get ID under [applications -> Application ID](https://discord.com/developers/applications/)

### Running as linux service
> (tested on ubuntu 22.04, some commands may be different depending on your distro)
1. Edit .env, `BOT_PRINT=no` So it does not clog up systemctl output, you can get the logs of the bot from step 5 below.
2. Make a new service file.
> `sudo nano /lib/systemd/system/voicelevels.service`
> ```ini
> [Unit]
> Description=Voice Levels bot run service
> After=multi-user.target
> 
> [Service]
> Type=simple
> Environment=PYTHONUNBUFFERED=1
> Restart=on-failure
> RestartSec=60s
> WorkingDirectory=PATH TO BOT FOLDER
> ExecStart=/usr/bin/python3 PATH TO YOUR init.py
> 
> [Install]
> WantedBy=multi-user.target
> ```
3. Give proper permissions for service type files
> `sudo chmod 644 /lib/systemd/system/voicelevels.service`
4. Refresh system services list, enable (start service on boot) and start.
> `sudo systemctl daemon-reload && sudo systemctl enable voicelevels.service && sudo systemctl start voicelevels.service`
5. Check the service `sudo systemctl status voicelevels.service` and `tail discord.log`
6. Stop and restart as you wish with `sudo systemctl stop voicelevels.service` and `sudo systemctl restart voicelevels.service`

### Running in windows background (scuffed)
#### Using task scheduler (not working?)
1. Open task scheduler
2. Create a new basic task, give it a name e.g. "voicelevels"
3. Set trigger to "When the computer starts"
4. Set action to "Start a program"
5. Fill out `Program/script` path and `Start in` accordingly with init.py / pipenv run init.py and directory where the bot is
6. Open its properties and untick everything under `Conditions -> Power`, `Settings -> Stop` the task if it runs more than
7. Tick `Settings -> If the task fails, restart every:`
#### Using NSSM (not working?)
1. Install [NSSM](http://nssm.cc/download)
2. `nssm install voicelevels "path to python/pipenv" "path to init.py (run /path if you are using pipenv)"`
3. Start and stop service with `nssm start voicelevels` and `nssm stop voicelevels`
If you want to remove the service, stop it and run `nssm remove "voicelevels"`
#### start on boot (working!)
1. Press <kbd>windows</kbd> + <kbd>r</kbd> to bring up run
2. Type in `shell:startup` and press enter
3. Rename init.py to init.pyw to prevent a console window opening
4. Make a shortcut of init.pyw and drag it into that folder
5. To stop bot:
    - Run `[prefix]stop` in any Discord channel where the bot can see, or dm the bot `stop`
    - You can also find the python process and kill it from task manager

---
#### Voice Levels Bot was an original concept by Sonicaii#0123, began development in 2019
Thanks to everyone who spared their own time to help me, especially from the [discord.py discord server](https://discord.com/invite/dpy).
