import asyncio
import json
import time, datetime
import discord
from discord.ext import tasks, commands
from psycopg2.extras import Json
from typing import Optional
from math import modf
from re import findall

def get_level_f(seconds: int) -> (int, str):
	""" function gets the level in (level: int, percentage to next level: str) """
	d, i = modf((0.75*((seconds/360)**0.5)+0.05*seconds/360)/4)
	return int(i), d

	if seconds <= 21600: # 6 hours
		return int(seconds/180), (str(seconds/180 - int(seconds/180)).split(".")[1]+"0")[:2]
	elif seconds <= 86400: # 24 hours
		return 120 + int((seconds - 21600)*80/64800), (str((seconds - 21600)*80/64800 - int((seconds - 21600)*80/64800)).split(".")[1]+"0")[:2]
	else: # seconds <= 604800: # 7 days
		return 200 + int(seconds/6048), (str(seconds/6048+200 - int(seconds/6048+200)).split(".")[1]+"0")[:2]


def get_level(seconds: int) -> int:
	""" function gets level in int """
	return get_level_f(seconds)[0]

def l2(id: int) -> str:
	return str(id)[-2:]

class Levels(commands.Cog):
	""" Main cog that handles detecting, processing and displaying levels """

	def __init__(self, bot):
		# bot initialisation
		self.bot = bot
		self.deliver = bot.deliver
		self.lock = asyncio.Lock()
		self.updater.start()

		# list of users who recently disconnected
		self.user_actions = set()
		self.user_joins = {}
		self.user_updates = {
			str(i).zfill(2): {} for i in range(100)
		}
		# '00': {}, '01': {}, '02': {}, ... , '97': {}, '98': {}, 99': {}


	async def writeInData(self) -> None:
		""" this function writes the data into the database """

		class user: ... # looks better lol

		# Get data
		with self.bot.conn.cursor() as cur:
			occupied = tuple(k for k, v in self.user_updates.items() if v)
			if not occupied: return

			cur.execute("SELECT right_two, json_contents FROM levels WHERE right_two IN %s", (occupied,))
			results = cur.fetchall()
			for right_two, json_contents in results:
				for user.id, user.time in self.user_updates[right_two].items():
					try:
						json_contents[str(user.id)] += user.time
					except KeyError:
						json_contents[str(user.id)] = user.time

			# don't even try to sql inject only with discord user id and time in seconds
			"""
				Manual import
				>>> var = {"id": time, "id": time ... }
				>>> results = [(str(i).zfill(2), {},) for i in range(100)]
				>>> for k, v in var.items():
				>>> 	results[int(k[-2:])][1][k] = v
			"""
			cur.execute(
				"""
					UPDATE levels SET
						json_contents = c.json_contents
					FROM (values
						%s
					) AS c(right_two, json_contents)
					WHERE levels.right_two::bpchar = c.right_two::bpchar;
				""" % ", ".join([f"('{r_t}'::bpchar, '{json.dumps(v)}'::json)" for r_t, v in results])

				# Json(v) gets inferred as type records
				# , [tuple( (r_t, Json(v)) for r_t, v in results)]

			)
			# { ", ".join(["('"+r_t+"'::bpchar, '"+json.dumps(v)+"'::json)" for r_t, v in results]) }

		self.user_updates = {
			str(i).zfill(2): {} for i in range(100)
		}
		# '00': {}, '01': {}, '02': {}, ... , '97': {}, '98': {}, 99': {}

		self.user_actions.clear()

		self.bot.conn.commit()

	@commands.Cog.listener()
	async def on_ready(self):

		self.bot.cogpr("Levels", self.bot)

		# reset when activated, prevents faulty overnight join times?
		class ctx:
			async def send(*args, **kwargs): pass
			class author:
				id = self.bot.sudo[-1]

		await self._update(ctx)


	@commands.Cog.listener()
	async def on_voice_state_update(self, member, before, after):
		""" Voice Updates """
		# ! @todo: search algorithms
		
		"""
		1. check if it was a disconnect/ reconnect/ move
		2. check if they have a previous join time ( make one if not )
		3. check if they have an update time ( make on if not )
		4. add their time.now - time.previous join to their update
		5. delete their join time if their action was leave ( after.channel == None )
		6. update their join time to current time
		"""
		await self._on_voice_state_update(member, before, after)

	async def _on_voice_state_update(self, member, before, after):

		if before.channel == after.channel or (member.id not in self.user_joins and after.channel == None):
			# name of the channel unchanged: not a disconnect or move
			# disconnected while no record of inital connection
			return

		self.user_actions.add(member.id)

		# add if not exist
		if member.id not in self.user_joins:
			self.user_joins[member.id]: int = int(time.time())
			return

		# add if not exist
		if member.id not in self.user_updates[l2(member.id)]:
			self.user_updates[l2(member.id)][member.id]: int = 0

		# add duration
		self.user_updates[l2(member.id)][member.id] += int(time.time()) - self.user_joins[member.id]

		# if it was not a leave: restart the count
		# starts the count if it was a first time join
		self.user_joins[member.id] = int(time.time())

		# removes from needing updates
		if after.channel == None:
			del self.user_joins[member.id]

		return


	@commands.hybrid_command(name="total", description="Shows total time in seconds")
	async def total(self, ctx: commands.Context, user: Optional[discord.User] = None):
		""" Return's the user's time in seconds """
		await self._total(ctx, user)

	@commands.hybrid_command(name="seconds", description="Shows total time in seconds")
	async def seconds(self, ctx: commands.Context, user: Optional[discord.User] = None):
		await self._total(ctx, user)

	async def _total(self, ctx, user):
		lookup = ctx.author if user is None else user

		# opens the corresponding file\
		with self.bot.conn.cursor() as cur:
			cur.execute("SELECT json_contents FROM levels WHERE right_two = %s", (l2(lookup.id),))
			user_times = cur.fetchone()[0]  # wow it already converted from json to py objects!
			
		if str(lookup.id) not in user_times:
			# record does not exist
			return await self.deliver(ctx)(f"<@!{lookup.id}> has no time saved yet.")

		# gets live info and the user times
		current_user_time = \
			user_times[str(lookup.id)] + int(time.time()) - self.user_joins[lookup.id] \
		if lookup.id in self.user_joins else \
			user_times[str(lookup.id)]

		return await self.deliver(ctx)(f"{lookup.name} has spent {current_user_time} seconds in voice channels")

	@commands.hybrid_command(name="level", description="Gets the time spent in voice channel of a specified user")
	async def level(self, ctx: commands.Context, user: Optional[str] = None):
		""" returns human ctx text """
		await self._level(ctx, user)

	@commands.hybrid_command(name="info", description="Gets the time spent in voice channel of a specified user")
	async def info(self, ctx: commands.Context, user: Optional[str] = None):
		await self._level(ctx, user)

	@commands.hybrid_command(name="time", description="Gets the time spent in voice channel of a specified user")
	async def time(self, ctx: commands.Context, user: Optional[str] = None):
		await self._level(ctx, user)

	async def _level(self, ctx, user):
		lookup = ctx.author if ctx.interaction is None else ctx.interaction.user
		if user is not None:
			if len(ctx.message.mentions) > 0:
				lookup = ctx.message.mentions[0]
			elif user.isdigit():
				lookup = discord.Object(id=int(user))
				lookup.name = user
			else:
				fa = lambda string: findall(r"(?<=[<@#!:a-z])(\d+)", string)
				if   lk := fa(ctx.message.content): pass
				elif lk := fa(user): pass
				else: lk = False
				
				if lk:
					lookup = discord.Object(id=lk[0])
					lookup.name = user
				else:
					return await self.deliver(ctx)(f"Invalid input")

		# opens the corresponding part
		with self.bot.conn.cursor() as cur:
			cur.execute("SELECT json_contents FROM levels WHERE right_two = %s", (l2(lookup.id),))
			user_times = cur.fetchone()[0]  # wow it already converted from json to py objects!

		if str(lookup.id) not in user_times:
			# record does not exist
			return await self.deliver(ctx)(f"{lookup.name} has no time saved yet.")

		# gets live info and the user times
		# current_user_times
		total_seconds = user_times[str(lookup.id)]
		if lookup.id in self.user_joins:
			total_seconds += int(time.time()) - self.user_joins[lookup.id]
		if lookup.id in self.user_updates[l2(lookup.id)]:
			total_seconds += self.user_updates[l2(lookup.id)][lookup.id]

		cut = datetime.timedelta(seconds=total_seconds)
		hours, minutes, seconds = str(cut).split()[-1].split(":")

		return await self.deliver(ctx)(f"{lookup.name} has spent {cut.days} days, {hours} hours, {minutes.lstrip('0')} minutes and {seconds.lstrip('0')} seconds on call: level {get_level(total_seconds)}")


	@commands.hybrid_command(name="all", description="Leaderboard for this server")
	async def all(self, ctx: commands.Context, page: Optional[int] = 1):
		if type(page) != int and not page.isdigit: page = 1
		if ctx.author.id in self.bot.sudo:
			async with ctx.channel.typing():
				with self.bot.conn.cursor() as cur:
					cur.execute("SELECT json_contents FROM levels")
					large_dict = {k: v for d in [i[0] for i in cur.fetchall()] for k, v in d.items()}.items()

				total_pages = len(large_dict)//20+1
				total_members = len(large_dict)

				if page > total_pages: return await self.deliver(ctx)(f"Nothing on page {page}. Total {total_pages} pages")

				sorted_d = {int(i): j for i, j in sorted(large_dict, key=lambda item: item[1], reverse=True)}
				dict_nicknames = {}
				for server in self.bot.guilds:
					dict_nicknames.update({int(member.id): member.name for member in server.members})

				return await self.deliver(ctx)(self._format_top(sorted_d, dict_nicknames, page))

		await self._top(ctx, page)


	@commands.hybrid_command(name="top", description="Leaderboard for this server")
	async def top(self, ctx: commands.Context, page: Optional[int] = 1):
		""" leaderboard of the server's times """
		await self._top(ctx, page)

	@commands.hybrid_command(name="leaderboard", description="Leaderboard for this server")
	async def leaderboard(self, ctx: commands.Context, page: Optional[int] = 1):
		await self._top(ctx, page)

	async def _top(self, ctx, page):

		if type(page) != int and not page.isdigit: page = 1
		sorted_d = {}

		# Typing in the channel
		async with ctx.channel.typing():

			with self.bot.conn.cursor() as cur:
				cur.execute("SELECT json_contents FROM levels WHERE right_two IN %s", (tuple(set(l2(i.id) for i in ctx.guild.members)),))
				large_dict = {k: v for d in [i[0] for i in cur.fetchall()] for k, v in d.items()}.items()
			
			list_of_ids = [i.id for i in ctx.guild.members]
			for k, v in sorted(large_dict, key=lambda item: item[1], reverse=True):
				if int(k) in list_of_ids:
					sorted_d[int(k)] = v

			dict_nicknames = {i.id: i.display_name for i in ctx.guild.members}
			total_pages = len(sorted_d)//20+1

			if page > total_pages: return await self.deliver(ctx)(f"Nothing on page {page}. Total {total_pages} pages")

			await self.deliver(ctx)(self._format_top(sorted_d, dict_nicknames, page))

	def _format_top(self, sorted_d, dict_nicknames, page):

		formatted = """Leaderboard of global scores from users of this server\n>>> ```md\n#Rank  Hours   Level    Name\n"""
		for member_id, member_seconds in list(sorted_d.items())[(page-1)*20:page*20]:
			try:
				nickname = dict_nicknames[member_id]
			except KeyError:
				nickname = member_id
			formatted += f""" {str(cnt := list(sorted_d).index(member_id) + 1)+".":<5}{round(member_seconds/60/60,2):<7} [ {get_level(member_seconds):<4} ]( {nickname} )\n"""
		return formatted+"```"

	@commands.command(pass_context=True)
	async def update(self, ctx):
		""" manually run through all channels and update into data.json """
		await self._update(ctx)

	async def _update(self, ctx):
		if ctx.author.id not in self.bot.sudo:
			return

		copy = self.user_updates.copy()

		async with self.lock:
			await self.writeInData() # Update everyone who is currently in

		for server in self.bot.guilds: # list of guilds
			for details in server.channels: # list of server channels
				if str(details.type) == "voice":
					if details.voice_states:
						for id in details.voice_states: # dict { id : info}
							self.user_joins[id] = int(time.time())
							self.user_actions.add(id)

		async with self.lock:
			await self.writeInData()
		
		# print("\nCalled an update:",ctx.author.id, "\n\tUser joins:", self.user_joins, "\n\tUser updates:", copy)

		return await ctx.send("Updated")

	@tasks.loop(minutes=5.0)
	async def updater(self):
		async with self.lock:
			await self.writeInData()


# cog setup
async def setup(bot):
	await bot.add_cog(Levels(bot))
