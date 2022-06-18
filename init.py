import asyncio
import logging
import logging.handlers
import os
import psycopg2
import discord
from discord import Object
from discord.ext import commands
from discord.ext.commands import Context, Greedy
from dotenv import load_dotenv
from typing import Any, Literal, Optional, Union

load_dotenv()

from header import cogpr, get_token, get_prefix, log, server_prefix


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
	cogpr("Main", bot)
	await bot.change_presence(
		activity=discord.Activity(
			name=f"for {os.environ.get('BOT_PREFIX')} / Voice Levels V3",
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
async def on_guild_join(guild):  # Can be abused and rate limit the bot
	await bot.tree.sync(guild=guild)


@bot.command()
async def sync(ctx: Context, guilds: Greedy[Object], spec: Optional[Literal["~"]] = None):
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
	log.warning(f"{ctx.author.id}: {ctx.author.name} synced global slash commands tree")


def deliver(obj: Union[commands.Context, discord.Interaction, Any]):
	""" returns an async function that will send message """
	return obj.response.send_message if isinstance(obj, discord.Interaction) else obj.send


def refresh_conn(self):
	self.conn = psycopg2.connect(os.environ.get("DATABASE_URL"), sslmode="require")


def main():
	log.debug("Connecting to database...")

	db_url = os.environ.get("DATABASE_URL")
	if not db_url:
		log.error("You do not have Heroku Postgress in Add-ons, or it was misconfigured")

	bot.conn = psycopg2.connect(db_url, sslmode="require")

	log.debug("Connected to database")
	# async with bot:

	bot.cogpr = cogpr
	bot.deliver = deliver
	bot.refresh_conn = refresh_conn
	bot.prefix_factory_init = False
	bot.prefix_cache_pop = lambda i: server_prefix.cache.pop(i, None)
	bot.prefix_cache_size = lambda: server_prefix.cache_size

	token = get_token(bot.conn)
	try:
		bot.run(token, log_handler=None)
	except discord.errors.LoginFailure:
		log.error("Invalid token!")
		log.error("Please refresh or insert correct token into the database")
		log.error("\t"+"UPDATE token SET token = 'BOT_TOKEN'")

	bot.conn.close()


if __name__ == "__main__":
	# asyncio.run(main())
	main()
