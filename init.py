import asyncio
import math
import os
import psycopg2
import time, datetime
import discord
from discord import app_commands, Object
from discord.app_commands import Choice
from discord.ext import tasks, commands
from discord.ext.commands import Context, Greedy
from typing import List, Literal, Optional, Union

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
	description="""Yeah"""
)

# @bot.event
# async def on_message(message):
# 	# do some extra stuff here

# 	await bot.process_commands(message)

@bot.event
async def on_ready():
	cogpr("Main", bot)
	await bot.change_presence(activity=discord.Activity(
		name="Testing",
		type=discord.ActivityType.playing
	))


@bot.event
async def on_guild_join(guild):  # Can be abused and rate limit the bot
	await bot.tree.sync(guild=guild)

class Ping(commands.Cog):

	# def __init__(self, bot: commands.Bot) -> None: self.bot = bot  # Doesn't even need it

	@app_commands.command(name="ping", description="current latency of bot")
	async def ping(self, interaction: discord.Interaction):
		await interaction.response.send_message(f"Current latency is {round(bot.latency * 1000)}ms")

	@app_commands.command(name="hi", description="respond")
	async def hi(self, interaction: discord. Interaction):
		await interaction.response.send_message(f"Hello")


@bot.command()
# @commands.is_owner()
async def sync(ctx: Context, guilds: Greedy[Object], spec: Optional[Literal["~"]] = None) -> None:
	"""
		Usage:
			`!sync` -> globally sync all commands (WARNING)
			`!sync ~` -> sync to current guild only.
			`!sync guild_id1 guild_id2` -> syncs specifically to these two guilds.
	"""
	try:
		print(f"Syncing from {ctx.guild.id}", guilds[0].id)
	except IndexError:
		pass
	if not guilds:
		if spec == "~":
			fmt = await ctx.bot.tree.sync(guild=discord.Object(id=ctx.guild.id))
		else:
			fmt = await ctx.bot.tree.sync()

		await ctx.send(
			f"Synced {len(fmt)} commands {'to the current guild.' if spec == '~' else 'globally'}\n" +
			"\n".join([i.name for i in fmt])
		)
		return

	fmt = 0
	for guild in guilds:
		try:
			await ctx.bot.tree.sync(guild=guild)
		except discord.HTTPException:
			pass
		else:
			fmt += 1

	await ctx.send(f"Synced the tree to {fmt}/{len(guilds)} guilds.")
'''
@bot.command()
async def sync(ctx: Context, guilds: Greedy[int], *, spec: Optional[Literal["~"]] = None) -> None:
	"""
		Usage:
			`!sync` -> globally sync all commands (WARNING)
			`!sync ~` -> sync to current guild only.
			`!sync guild_id1 guild_id2` -> syncs specifically to these two guilds.
	"""
	if not guilds and spec is not None:
		if spec == "~":
			fmt = await bot.tree.sync(guild=ctx.guild)
		else:
			fmt = await bot.tree.sync()

		await ctx.send(
			f"Synced {len(fmt)} {'globally' if spec is None else 'to the current guild.'}"
		)
		return

	assert guilds is not None
	fmt = 0
	for guild in guilds:
		try:
			await ctx.bot.tree.sync(guild=discord.Object(id=guild))
		except discord.HTTPException:
			pass
		else:
			fmt += 1

	await ctx.send(f"Synced the tree to {fmt}.")
		'''
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
				]]:
				print(f"loading extension: {ext}")
				await bot.load_extension(ext)
			await bot.add_cog(Ping())
			await bot.start(get_token(bot.conn))


if __name__ == "__main__":
	asyncio.run(main())
