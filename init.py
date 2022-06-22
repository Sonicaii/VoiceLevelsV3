#!/usr/bin/env python3
import asyncio
import os
import psycopg2
import discord
from discord import Object
from discord.ext import commands
from discord.ext.commands import Context, Greedy
from datetime import datetime
from dotenv import load_dotenv
from typing import Any, Awaitable, Literal, Optional, Union
from header import cogpr, discord_escape, fm, get_token, get_prefix, log, refresh_conn, server_prefix

load_dotenv()

# Bot is a wrapper around discord.Client, therefore called bot instead of client
bot = commands.Bot(
	case_insensitive=True,
	help_command=None,
	command_prefix=get_prefix,
	intents=discord.Intents(
		**{i: True for i in [
			"message_content",
			"voice_states",
			"members",
			"integrations",
			"webhooks",
			"guilds",
			"messages",
		]}
	),
	description="""User levels based on time spent in voice channels.""",
)

# @bot.event
# async def on_message(message):
# 	# do some extra stuff here

# 	await bot.process_commands(message)

@bot.event
async def setup_hook():
	for ext in ["cogs."+i for i in [
			"levels",
			"misc",
			"help",
			"snipe",
		]]:

		await bot.load_extension(ext)

@bot.event
async def on_ready():
	cogpr("Main", bot, "Y")
	await bot.change_presence(
		activity=discord.Activity(
			name=f"for {os.getenv('BOT_PREFIX')} | Voice Levels V3",
			type=discord.ActivityType.watching,
		)
	)

	# INSERT INTO sudo VALUES ("discord id")
	with bot.conn.cursor() as cur:
		try:
			cur.execute("SELECT TRIM(id) FROM sudo")
			bot.sudo = [int(i[0]) for i in cur.fetchall()]
			if not bot.sudo:
				raise psycopg2.errors.UndefinedTable

		except psycopg2.errors.UndefinedTable:
			owner_id = (await bot.application_info()).owner.id
			cur.execute("INSERT INTO sudo VALUES %s", ((str(owner_id),),))
			bot.sudo = [int(owner_id)]
			bot.conn.commit()


@bot.event
async def on_guild_join(guild) -> None:  # Can be abused and rate limit the bot
	await bot.tree.sync(guild=guild)


@bot.command(name="reload", aliases=["r"])
async def reload(ctx: Context, cog: str):
	""" reloads a cog """

	if ctx.author.id not in bot.sudo or not cog:
		return

	msg = "Reloading cogs." + cog

	try:
		await bot.reload_extension(name="cogs." + cog)
	except Exception as e:
		msg = e

	log.warning(msg)
	return await ctx.send(msg)


@bot.command()
async def sync(ctx: Context, guilds: Greedy[Object], spec: Optional[Literal["~"]] = None) -> None:
	"""
	https://gist.github.com/AbstractUmbra/a9c188797ae194e592efe05fa129c57f
		Usage:
			`!sync` -> globally sync all commands (WARNING)
			`!sync ~` -> sync to current guild only.
			`!sync guild_id1 guild_id2` -> syncs specifically to these two guilds.
	"""
	if ctx.author.id not in bot.sudo:
		return

	if spec == "~" and ctx.guild:
		log.warning(f"{ctx.author.id}: {ctx.author.name} has requested to sync commands to guild {ctx.guild.id}: {ctx.guild.name}")
		await ctx.send("Syncing for this guild")
		return await ctx.bot.tree.sync(guild=ctx.guild)

	await ctx.send("Sycning global...")
	await ctx.bot.tree.sync()  # this bot only has global commands so this must be run
	log.warning(f"{ctx.author.id}: {ctx.author.name} synced global slash commands tree")


def deliver(obj: Union[commands.Context, discord.Interaction, Any]) -> Awaitable:
	""" returns an async function that will send message """
	return obj.response.send_message if isinstance(obj, discord.Interaction) else obj.send


def main():

	bot.cogpr = cogpr
	bot.deliver = deliver
	bot.discord_escape = discord_escape
	bot.fm = fm
	bot.start_time = datetime.now()

	# Prefix variables
	bot.prefix_factory_init = False
	bot.prefix_cache_pop = lambda i: server_prefix.cache.pop(i, None)
	bot.prefix_cache_size = lambda: server_prefix.cache_size
	bot.default_prefix = server_prefix.default_prefix
	bot.refresh_conn = refresh_conn

	# async with bot:
	bot.conn = bot.refresh_conn()
	token = get_token(bot.conn)
	try:
		bot.run(token, log_handler=None)
	except discord.errors.LoginFailure:
		log.error("Invalid token!")
		log.error("Please refresh or insert correct token into the database")
		log.error("\t"+"UPDATE token SET token = 'BOT_TOKEN'")

	bot.conn.close()


if __name__ == "__main__":
	main()
