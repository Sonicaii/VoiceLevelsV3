import asyncio
import math
import os
import psycopg2
import time, datetime
import discord
from discord import app_commands
from discord.ext import tasks, commands

from header import (
	ferror,
	get_token,
	get_prefix,
	cogpr,
	printv,
)

from preset import printv

print("Creating commands.Bot object")
# Bot is a wrapper around discord.Client, therefore called bot instead of client
bot = commands.Bot(
	case_insensitive=True,
	help_command=None,
	command_prefix="!", # get_prefix,
	intents=discord.Intents(**{i:True for i in [
		"message_content",
		"voice_states",
		"members"
	]}),
	description="""User levels based on time spent in voice channels."""
)

@bot.event
async def on_message(message):
	if message.author == client.user:
		return

	if message.content.startswith('$hello'):
		await message.channel.send('Hello!')

@bot.event
async def on_ready():
	print("READY!")
	cogpr("Main", client)
	await bot.change_presence(activity=discord.Activity(
		name="Testing",
		type=discord.ActivityType.playing
	))

async def main():
	print("Connecting to database...")

	bot.db_url = os.environ.get("DATABASE_URL")
	if not bot.db_url:
		ferror("You do not have Heroku Postgress in Add-ons, or it was misconfigured")

	with psycopg2.connect(bot.db_url, sslmode='require') as bot.conn:
		print("Connected to database")
		async with bot:
			for ext in ["cogs."+i for i in [
					# "levels",
					# "misc",
					# "help",
					# "snipe",
					"simple"
				]]:
				print(f"loading extension: {ext}")
				await bot.load_extension(ext)
			
			await bot.start(get_token(bot.conn))


if __name__ == "__main__":
	asyncio.run(main())
