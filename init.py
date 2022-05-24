import asyncio
import math
import os
import psycopg2
import time, datetime
import discord
from discord import app_commands, Object
from discord.ext import tasks, commands
from discord.ext.commands import Context, Greedy
from typing import Optional, Literal

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
	command_prefix=get_prefix,
	intents=discord.Intents(**{i:True for i in [  # TODO !!! ADD VOICE CHANNEL DETECTION IN INTENTS
		"message_content",
		"voice_states",
		"members",
		"integrations",
		"webhooks",
		"guilds",
		"messages",
	]}),
	description="""User levels based on time spent in voice channels."""
)

@bot.event
async def on_ready():
	print("READY!")
	cogpr("Main", bot)
	await bot.change_presence(activity=discord.Activity(
		name="Testing",
		type=discord.ActivityType.playing
	))


@bot.event
async def on_guild_join(guild):  # Can be abused and rate limit the bot
	await bot.tree.sync(guild=guild)


@bot.command()
# @commands.is_owner()
async def sync(ctx: Context, guilds: Greedy[Object], spec: Optional[Literal["~"]] = None) -> None:
	"""
		Usage:
			`!sync` -> globally sync all commands (WARNING)
			`!sync ~! -> sync to current guild only.
			`!sync guild_id1 guild_id2` -> syncs specifically to these two guilds.
	"""
	print(f"Syncing for {ctx.guild.id}")
	if not guilds:
		if spec == "~":
			fmt = await bot.tree.sync(guild=ctx.guild)
		else:
			fmt = await bot.tree.sync()

		await ctx.send(
			f"Synced {len(fmt)} commands {'globally' if spec is not None else 'to the current guild.'}"
		)
		return

	fmt = 0
	for guild in guilds:
		try:
			await bot.tree.sync(guild=guild)
		except discord.HTTPException:
			pass
		else:
			fmt += 1

	await ctx.send(f"Synced the tree to {fmt}/{len(guilds)} guilds.")


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
					"misc",
					# "help",
					# "snipe",
				]]:
				print(f"loading extension: {ext}")
				await bot.load_extension(ext)
			
			await bot.start(get_token(bot.conn))


if __name__ == "__main__":
	asyncio.run(main())
