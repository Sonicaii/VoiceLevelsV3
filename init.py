import psycopg2
import discord
from discord import app_commands
from discord.ext import tasks, commands

from header import (
	ferror,
	get_token,
	get_prefix
)

# Bot is a wrapper around discord.Client, therefore called bot instead of client
bot = commands.Bot(
	command_prefix="!", # get.prefix,
	case_insensitive=True,
	intents=intents,
	description="""User levels based on time spent in voice channels."""
)

async def main():
	print("Connecting to database...")

	if bot.db_url := os.environ.get("DATABASE_URL"):
		ferror("You do not have Heroku Postgress in Add-ons, or it was misconfigured")

	with psycopg2.connect(bot.db_url, sslmode='require') as bot.conn:
		print("Connected to database")
		async with client:
			for ext in ["cogs."+i for i in [
					# "levels",
					"misc",
					"help",
					"snipe",
				]]:
				print(f"loading extension: {ext}")
				await bot.load_extension(ext)
			
			await client.start(get.token())

if __name__ == "__main__":
	asyncio.run(main())
