""" Voice Levels header"""
import logging
import os
import time
from collections import OrderedDict
from dotenv import load_dotenv
# from cachetools import cached, cachedmethod, LRUCache, TTLCache, keys
from psycopg2.extensions import connection
from re import sub
from sys import stdout
from discord.ext import commands

load_dotenv()

""" # Stream gets "constipated", this helps unclog logging
if not os.path.isfile("discord.log"):
	with open("discord.log", "w"):
		pass

if os.path.getsize("discord.log") > 1.8 * 1024 * 1024:
	os.rename("discord.log", "discord.log.1")
	for i in range(5, 1, -1):
		if not os.path.isfile(f"discord.log.{i}"):
			break
		os.rename(f"discord.log.{i}", f"discord.log.{i+1}")

	with open("discord.log", "w"):
		pass
"""

log = logging.getLogger("discord")

logging_level = (
	{ k: v*10
	for k,v in zip(
		["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
		range(0,6)
		)
	}[os.getenv("BOT_LOG_LEVEL").upper()]
	if os.getenv("BOT_LOG_LEVEL") else
	logging.ERROR
)
log = logging.getLogger("discord")
log.setLevel(logging_level)
logging.getLogger("discord.http").setLevel(logging_level)

handler = logging.handlers.RotatingFileHandler(
	filename="discord.log",
	encoding="utf-8",
	maxBytes= int(os.getenv("BOT_LOG_FILESIZE", 4)) * 1024 * 1024,
	backupCount=2,
)
dt_fmt = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter("{asctime} [{levelname:<8}] {name}: {message}", dt_fmt, style="{")
handler.setFormatter(formatter)
log.addHandler(handler)

if os.getenv("BOT_PRINT", "").lower() == "yes":
	printer = logging.StreamHandler(stdout)
	printer.setFormatter(formatter)
	log.addHandler(printer)


# colours.py ------

if os.name == "nt": os.system("color")

_letters = ["k", "r", "g", "y", "b", "m", "c", "w", "K", "R", "G", "Y", "B", "M", "C", "W"]
class fg:
	"""
		Console foreground colouriser
		Usage:
			fg.color("string")
		k = black
		r = red
		g = green
		y = yellow
		b = blue
		m = magenta
		c = cyan
		w = white

			fg.d["colour"]("string")


		capital = bold (not working)
	"""
	d = {}
	for num, letter in enumerate(_letters[:8]):
		exec(letter+"= '\033["+str(num+30)+"m{}\033[0m'.format")
		d[letter] = "\033[{}m{}\033[0m".format(num+30, "{}").format
	for num, letter in enumerate(_letters[8:]):
		exec(letter+"= '\033["+str(num+30)+"m{}\033[0m'.format")
		d[letter] = "\033[{}m;1m{}\033[0m".format(num+38, "{}").format

class bg:
	"""
	Console background colouriser
		Usage:
			bg.color("string")
		k = black
		r = red
		g = green
		y = yellow
		b = blue
		m = magenta
		c = cyan
		w = white

			bg.d["colour"]("string")


		capital = bold (not working)
	"""
	d = {}
	for num, letter in enumerate(_letters):
		exec(letter+"= '\033["+str(num+40)+"m{}\033[0m'.format")
		d[letter] = "\033[{}m{}\033[0m".format(num+40, "{}").format

"""
	Console text formatter
		Usage:
			fm[int]("string")
		0 = reset
		1 = bold
		2 = darken
		3 = italic
		4 = underlined
		5 = blinking
		6 = un-inverse colour
		7 = inverse colour
		8 = hide
		9 = crossthrough
"""
fm = {
	**{i : "\033[{}m{{}}\033[0m".format(i).format for i in range(10)},
	"c":"\033[0m{}\033[0m".format,
	"u":"\033[4m{}\033[0m".format,
	"i":"\033[8m{}\033[0m".format,
	"bg":bg,
	"fg":fg,
}
# -----------------


def cogpr(name: str, bot: object, colour: str = "c") -> str:
	""" format cog start output """
	log.info(fg.d[colour]("Activated ")+ fg.d[colour](f"{bot.user.name} ")+ fg.m(name))


def get_token_old(conn: connection, recurse: int = 0) -> [str, bool]:
	""" static method? Gets token from database for run() """
	try:
		with conn.cursor() as cur:
			cur.execute("SELECT token FROM token")
			return [cur.fetchone()[0], False]
	except Exception as e: # psycopg2.errors.UndefinedTable
		import new_db
		conn.rollback() # Need to rollback after exception

		log.error(f"NO TOKEN IN DATABASE!")
		log.error("Edit new_db.py to insert bot token or run:")
		log.error("\t"+"UPDATE token SET token = 'BOT_TOKEN'")

		with conn.cursor() as cur:
			cur.execute(new_db.create_token)
			# 	cur.execute(new_db.detect)
			# 	has_tables = cur.fetchone()[0]

			# if not has_tables:
			# 	log.error("You do not have any tables in your database, setting up now")
			# 	with conn.cursor() as cur:
			cur.execute(new_db.create_vl)
		conn.commit()
	return [get_token(conn, recurse+1)[0] if recurse < 1 else "", True]


def get_token(conn: connection) -> str:
	""" Returns the bot token from environment variables, and bool for need_setup"""
	if not (token := os.getenv("BOT_TOKEN")):
		log.error(f"NO TOKEN IN ENVIRONMENT VARS!")
		log.error("Head to your Heroku dashboard->settings and add the config var BOT_TOKEN")
		log.error("If you're hosting locally, edit .env and update your BOT_TOKEN")

	# Init database if doesn't exist
	with conn.cursor() as cur:
		cur.execute("""
			SELECT EXISTS (
				SELECT FROM 
					information_schema.tables 
				WHERE 
					table_schema LIKE 'public' AND 
					table_type LIKE 'BASE TABLE' AND
					table_name = 'levels'
				);
		""")
		if not cur.fetchone()[0]:
			import new_db

			cur.execute(new_db.create_vl)
			conn.commit()
	return token

'''
class _prefix_factory:
	global len_bot_guilds  # rip

	def __init__(self, bot):
		self.bot = bot

	# @cachedmethod(cache=LRUCache(maxsize=len(bot.guilds)//1.5), key=lambda conn, server_id: keys.hashkey(server_id))
	@cachedmethod(cache=LRUCache(maxsize=len_bot_guilds//1.5), key=lambda conn, server_id: keys.hashkey(server_id)) # rip
	def _server_prefix(conn, server_id: int):
		with conn.cursor() as cur:
			cur.execute("SELECT TRIM(prefix) FROM prefixes WHERE id = %s", (str(server_id),))
			prefix = cur.fetchone()
		return ',,' if prefix is None else prefix[0]

class _prefix_factory_returner:
	def make_factory(self, bot):
		self._prefix_factory = _prefix_factory(bot)

_prefix_factory_returner = _prefix_factory_returner()
'''

class _server_prefix:
	cache_size = 1000
	cache = OrderedDict()
	default_prefix = os.getenv("BOT_PREFIX", ",,")

	def __call__(self, conn, server_id: int):
		if (prefix := self.cache.get(server_id)) is not None:
			self.cache.move_to_end(server_id)
			return prefix

		with conn.cursor() as cur:
			cur.execute("SELECT TRIM(prefix) FROM prefixes WHERE id = %s", (str(server_id),))
			prefix = cur.fetchone()

		self.cache[server_id] = self.default_prefix if prefix is None else prefix[0]
		while len(self.cache) > self.cache_size:
			self.cache.popitem(last=False)
		return self.cache[server_id]


server_prefix = _server_prefix()


async def get_prefix(bot, message):
	""" sets the bot's prefix """

	'''
	if not bot._prefix_factory_init:

		global len_bot_guilds  # rip
		len_bot_guilds = len(bot.guilds)  # rip

		prefix_factory_returner.make_factory(bot)

	_server_prefix = _prefix_factory_returner._prefix_factory._server_prefix
	'''

	if not bot.prefix_factory_init:
		server_prefix.cache_size = (len(bot.guilds) // 1.25) if len(bot.guilds) > 1000 else len(bot.guilds)
		bot.prefix_factory_init = True

	# no prefix needed if not in dm
	return commands.when_mentioned_or(
		server_prefix(bot.conn, message.guild.id) if message.guild else ''
	)(bot, message)
