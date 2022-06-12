# Voice Levels Rewrite Version 3

The new and improved **Voice Levels** discord.py bot with slash commands and Postgres database

## Hosting on Heroku:
1. Create a discord application on [Discord Developer Portal](https://discord.com/developers/applications)
2. Make Heroku account and deploy!<br />[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/Sonicaii/VoiceLevelsV3/)
3. Install the [Heroku Postgres Add-on](https://dashboard.heroku.com/provision-addon?addonServiceId=6c67493d-8fc2-4cd4-9161-4f1ec11cbe69&planId=062a1cc7-f79f-404c-9f91-135f70175577) for the database
4. add new config env var in dashboard with bot token, found [here]()
5. Invite to your server(s) using this link:<br />
> `https://discord.com/api/oauth2/authorize?client_id=`**`YOUR_BOT_ID`**`&permissions=2684456000&scope=applications.commands%20bot`<br />Get ID under [applications -> Application ID](https://discord.com/developers/applications/)
7. enable python dyno to start the bot
