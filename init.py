import asyncio
import os
import psycopg2
import discord
from discord import Object
from discord.ext import commands
from discord.ext.commands import Context, Greedy
from typing import Any, Literal, Optional, Union

from header import (
	ferror,
	get_token,
	get_prefix,
	_server_prefix,
	cogpr
)

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

# @bot.event
# async def on_message(message):
# 	# do some extra stuff here

# 	await bot.process_commands(message)

@bot.event
async def on_ready():
	cogpr("Main", bot)
	await bot.change_presence(activity=discord.Activity(
		name="for ,, / Voice Levels V3",
		type=discord.ActivityType.watching
	))

	# INSERT INTO sudo VALUES ('discord id')
	with bot.conn.cursor() as cur:
		try:
			cur.execute("SELECT TRIM(id) FROM sudo")
			bot.sudo = [int(i[0]) for i in cur.fetchall()]
			print(bot.sudo)
			if not bot.sudo:
				raise psycopg2.errors.UndefinedTable
		except psycopg2.errors.UndefinedTable:
			owner_id = (await bot.application_info()).owner.id
			print(f"owner id: {owner_id}")

			cur.execute("INSERT INTO sudo VALUES %s", ((str(owner_id),),))
			bot.sudo = [int(owner_id)]
			bot.conn.commit()
			print(bot.sudo)


@bot.event
async def on_guild_join(guild):  # Can be abused and rate limit the bot
	await bot.tree.sync(guild=guild)


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

	await ctx.send("Sycning global...")
	await ctx.bot.tree.sync()  # this bot only has global commands so this must be run


def deliver(obj: Union[commands.Context, discord.Interaction, Any]):
	""" returns an async function that will send message """
	return obj.response.send_message if isinstance(obj, discord.Interaction) else obj.send


def refresh_conn(self):
	self.conn = psycopg2.connect(os.environ.get("DATABASE_URL"), sslmode='require')

async def main():
	print("Connecting to database...")

	db_url = os.environ.get("DATABASE_URL")
	if not db_url:
		ferror("You do not have Heroku Postgress in Add-ons, or it was misconfigured")

	bot.conn = psycopg2.connect(db_url, sslmode='require')

	print("Connected to database")
	async with bot:

		bot.cogpr = cogpr
		bot.deliver = deliver
		bot.refresh_conn = refresh_conn
		bot._prefix_factory_init = False
		bot._prefix_cache_pop = lambda i: _server_prefix.cache.pop(i, None)
		bot._prefix_cache_size = lambda: _server_prefix.cache_size

		for ext in ["cogs."+i for i in [
				"levels",
				"misc",
				"help",
				"snipe",
			]]:
			
			await bot.load_extension(ext)

		token, bot.need_setup = get_token(bot.conn)
		try:
			await bot.start(token)
		except discord.errors.LoginFailure as e:
			ferror("Invalid token! Please refresh or insert correct token into the database")
			ferror("\t"+"UPDATE token SET token = 'BOT_TOKEN'")

	bot.conn.close()

if __name__ == "__main__":
	asyncio.run(main())
