""" Voice Levels header"""
from psycopg2.extensions import connection
import time
from discord.ext import commands

# colours.py ------
letters = ["k", "r", "g", "y", "b", "m", "c", "w", "K", "R", "G", "Y", "B", "M", "C", "W"]
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
	for num, letter in enumerate(letters[:8]):
		exec(letter+"= '\033["+str(num+30)+"m{}\033[0m'.format")
		d[letter] = "\033[{}m{}\033[0m".format(num+30, "{}").format
	for num, letter in enumerate(letters[8:]):
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
	for num, letter in enumerate(letters):
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
	"i":"\033[8m{}\033[0m".format
}
# -----------------

def printr(*args):
	""" prints and returns """
	print(*args)
	return [*args]


def ferror(*text: str):
	""" indents """
	return printr(">\t! "+str(*text))


def cogpr(name: str, bot: object, colour: str="c") -> str:
	""" format cog start output"""
	return printr(fg.d[colour](f"\n{bot.user.name} ")+name+fg.d[colour](" Activated")+f"\n{time.ctime()}")


def printv(level, *args):
	""" TODO depricate, relace with logging module """
	if type(level) == int:
		print(*args)
	else:
		print(level, *args)


def get_token(conn: connection, recurse: int = 0) -> [str, bool]:
	""" static method? Gets token from token.txt for run() """
	try:
		with conn.cursor() as cur:
			cur.execute("SELECT token FROM token")
			return [cur.fetchone()[0], False]
	except Exception: # psycopg2.errors.UndefinedTable
		import new_db
		conn.rollback() # Need to rollback after exception

		ferror(f"NO TOKEN IN DATABASE!")
		ferror("Edit new_db.py to insert bot token or run:")
		ferror("\t"+"INSERT INTO token (token) VALUES ('BOT_TOKEN');")

		with conn.cursor() as cur:
			cur.execute(new_db.create_token)
			cur.execute(new_db.detect)
			has_tables = cur.fetchone()[0]

		if not has_tables:
			ferror("You do not have any tables in your database, setting up now")
			with conn.cursor() as cur:
				cur.execute(new_db.create_vl)

	return [get_token(conn, recurse+1)[0] if recurse < 1 else "", True]


async def get_prefix(bot, message):
	""" sets the bot's prefix """

	prefixes = [',,', '<@708260446242734130>', '<@!708260446242734130>']
	if not message.guild: prefixes.append('')
	# no prefix needed if not in dm

	return commands.when_mentioned_or(*prefixes)(bot, message)
