""" Voice Levels header"""
from psycopg2.extensions import connection


def printr(*args):
	""" prints and returns """
	print(*args)
	return [*args]


def ferror(*text: str):
	""" indents """
	return printr(">\t! "+str(*text))


def cogpr(self, name: str, client: object, colour: str="c") -> str:
	""" format cog start output"""
	return fg.d[colour](f"\n{client.user.name} ")+name+fg.d[colour](" Activated")+f"\n{time.ctime()}"


def printv(self, level, *args):
	""" TODO depricate, relace with logging module """
	if type(level) == int:
		print(*args)
	else:
		print(level, *args)


def get_token(conn: connection, recurse: int = 0) -> str:
	""" static method? Gets token from token.txt for run() """
	try:
		with conn.cursor() as cur:
			cur.execute("SELECT token FROM token")
			return cur.fetchone()[0]
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

	return get_token(conn, recurse+1) if recurse < 1 else ""


async def get_prefix(bot, message):
	""" sets the bot's prefix """

	prefixes = [
		'..', '<@695805789050241034>', '<@!695805789050241034>'
	] if message.guild else [
		'..', '<@695805789050241034>', '<@!695805789050241034>', '']
	# no prefix needed if not in dm

	return commands.when_mentioned_or(*prefixes)(bot, message)
