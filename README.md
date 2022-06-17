# Voice Levels Rewrite Version 3

The new and improved **Voice Levels** discord.py bot with slash commands and Postgres database

## Hosting on Heroku:

1. Make Heroku account and deploy!<br />[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/Sonicaii/VoiceLevelsV3/)
2. Install the [Heroku Postgres Add-on](https://dashboard.heroku.com/provision-addon?addonServiceId=6c67493d-8fc2-4cd4-9161-4f1ec11cbe69&planId=062a1cc7-f79f-404c-9f91-135f70175577) for the database
3. Create a discord application on [Discord Developer Portal](https://discord.com/developers/applications)
4. Get new bot token in the [discord developer dashboard -> Bot -> (Add bot if you don't have one) / get / reset token](https://discord.com/developers/applications) 
5. Add new config env var with your bot token. [Heroku Application -> Settings -> Config Vars](https://dashboard.heroku.com/apps/)
6. Invite to your server(s) using this link, with your bot id:<br />
> `https://discord.com/api/oauth2/authorize?client_id=`**`YOUR_BOT_ID`**`&permissions=2684456000&scope=applications.commands%20bot`<br />Get ID under [applications -> Application ID](https://discord.com/developers/applications/)
7. enable python dyno to start the bot in the resources dab

## Hosting on local machine / server
1. Download code
2. Follow steps 2 to 4 above
3. Edit new_db.py and insert your token and chosen bot prefix (You can remove them for security reasons after the bot's first run)
4. Add DATABASE_URL to your postgres database (uses ssl connection) in the .env file or as environment variable
5. Run init.py to start bot
