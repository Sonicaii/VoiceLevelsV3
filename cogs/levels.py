if __name__ == "__main__":
	exit()
	# exits if not imported

from __main__ import *
from psycopg2.extras import Json


def get_level_f(seconds: int) -> tuple:
	""" function gets the level in (level: int, percentage to next level: str) """
	d, i = math.modf((0.75*((seconds/360)**0.5)+0.05*seconds/360)/4)
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

class Levels(commands.Cog):
	""" Main cog that handles detecting, processing and displaying levels """

	def __init__(self, bot):
		# bot initialisation
		self.bot = bot
		self.lock = asyncio.Lock()
		self.updater.start()

		# list of users who recently disconnected
		self.user_actions = []
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
			occupied = (k for k, v in self.user_updates.items() if v)
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
			i: {} for i in range(10)
		}
		# 0: {}, 1: {}, 2: {}, 3: {}, 4: {}, 5: {}, 6: {}, 7: {}, 8: {}, 9: {}

		self.user_actions = []

	@commands.Cog.listener()
	async def on_ready(self):

		printv(fg.g(f"\n{bot.user.name} Main Activated")+f"\n{time.ctime()}")
		printv(2, "user ID:", bot.user.id)
		printv(2, f"Discord.py Version: {fg.c(discord.__version__)}\n")

		# reset when activated, prevents faulty overnight join times
		class ctx:
			async def send(*args, **kwargs): pass
			class message:
				class author:
					id = get.top_level_users[0]

		await self.update(ctx)


	@commands.command(pass_context=True)
	async def a(self, ctx):
		await ctx.send("a")


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

		# print(before, after)

		if type(after) != str:
			if before.channel == after.channel or (member.id not in self.user_joins and after.channel == None):
				# name of the channel unchanged: not a disconnect or move
				# disconnected while no record of inital connection
				return

		if member.id not in self.user_actions: self.user_actions.append(member.id)

		# add their join time
		if member.id not in self.user_joins:
			self.user_joins[member.id]: int = int(time.time())
			return

		# add update time
		# no not delete here
		if member.id not in self.user_updates:
			self.user_updates[str(member.id)[-2:]][member.id]: int = 0

		# change update time
		self.user_updates[str(member.id)[-2:]][member.id] += int(time.time()) - self.user_joins[member.id]

		# removes from needing updates
		if type(after) != str:
			if after.channel == None:
				del self.user_joins[member.id]
				return

		# if it was not a leave: restart the count
		# starts the count if it was a first time join
		self.user_joins[member.id] = int(time.time())

		return


	@app_commands.command(name="total", description="Shows total time in seconds")
	async def total(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
		""" Return's the user's time in seconds """

		lookup = interaction.user if user is None else user

		if lookup.id in self.user_actions:
			async with self.lock:
				await self.writeInData()

		# opens the corresponding file\
		with bot.conn.cursor() as cur:
			cur.execute("SELECT json_contents FROM levels WHERE right_two = %s", str(lookup.id)[-2:])
			user_times = cur.fetchone()[0]  # wow it already converted from json to py objects!
			
		if str(lookup.id) not in user_times:
			# record does not exist
			return await ctx.send(f"<@!{lookup.id}> has no time saved yet.")

		# gets live info and the user times
		current_user_time = \
			user_times[str(lookup.id)] + int(time.time()) - self.user_joins[lookup.id] \
		if ctx.message.author.id in self.user_joins else \
			ser_times[str(lookup.id)]

		return await ctx.send(f"{lookup.name} has spent {current_user_time} seconds in voice channels")

	@app_commands.command(name="time", description="Gets the time spent in voice channel of a specified user")
	async def time(self, interaction: discord.Interaction, user: Optional[discord.User]):
		""" returns human readable text """

		lookup = interaction.user if user is None else user

		if lookup_id in self.user_actions:
			async with self.lock:
				await self.writeInData()


		# opens the corresponding file
		with bot.conn.cursor() as cur:
			cur.execute("SELECT json_contents FROM levels WHERE right_two = %s", str(lookup.id)[-2:])
			user_times = cur.fetchone()[0]  # wow it already converted from json to py objects!

		if str(lookup.id) not in user_times:
			# record does not exist
			return await ctx.send(f"<@!{lookup.id}> has no time saved yet.")

		# gets live info and the user times
		# current_user_times
		total_seconds = user_times[str(lookup.id)]
		cut = datetime.timedelta(seconds=\
				total_seconds + int(time.time()) - self.user_joins[lookup.id] \
			if lookup.id in self.user_joins else \
				total_seconds
		)
		hours, minutes, seconds = str(cut).split()[-1].split(":")

		return await ctx.send(f"{lookup.name} has spent {cut.days} days, {hours} hours, {minutes.lstrip('0')} minutes and {seconds.lstrip('0')} seconds on call: level {get_level(total_seconds)}")


	@commands.command(pass_context=True, name='top', aliases=['leaderboard', 'ranks'])
	async def top(self, ctx):
		""" leaderboard of the server's times """

		sorted_d = {}

		all_check = ctx.author.id in get.top_level_users and "all" in ctx.message.content
		if all_check:
			total_members = len([member for server in bot.guilds for member in server.members])

		# leaderboard in DMs ( joke )
		# if not ctx.guild:
		if False:
			if ctx.author.id in top_level_users:
				for i in range(len(fulld)):
					g_mem_position = n_def(namestr, member=int(nameid[i]))

					if namesecs[i] != '0' and g_mem_position is not None:
						guild_mem_valid.append((nameid[i], g_mem_position))
						guild_members_id.append(nameid[i])

			else:
				if namesecs[n_def(namestr, ctx.author.id)] != "0":
					guild_mem_valid.append((ctx.author.id, n_def(namestr, ctx.author.id)))
					guild_members_id.append(ctx.author.id)

				guild_mem_valid.append((bot.user.id, n_def(namestr, bot.user.id)))
				guild_members_id.append(bot.user.id)


		page = (int(ctx.message.content.split()[1]) if ctx.message.content.split()[1].isdigit() else 1) if len(ctx.message.content.split()) != 1 else 1
		total_pages = (total_members if all_check else len(ctx.guild.members))// 20
		if page > total_pages:
			return await ctx.send(f"Nothing on page {page}. Total {total_pages} pages")

		# Typing in the channel
		async with ctx.typing():
			with open("data - All.json", "r") as file_obj:
				large_dict = json.load(file_obj).items()
				dict_nicknames = {i.id: i.display_name for i in ctx.guild.members}

				for k, v in sorted(large_dict, key=lambda item: item[1], reverse=True):

					if int(k) in [i.id for i in ctx.guild.members]:
						sorted_d[int(k)] = v

				if all_check:
					sorted_d = {i: j for i, j in sorted(large_dict, key=lambda item: item[1], reverse=True)}
					dict_nicknames = {}
					for server in bot.guilds:
						dict_nicknames.update({str(member.id): member.name for member in server.members})

				formatted = """Leaderboard of global scores from users of {}\n>>> ```md\n#Rank  Hours   Level    Name\n""".format("all servers" if all_check else "this server")
				
				# print(list(sorted_d.items())[(page-1)*20:page*20])
				for member_id, member_seconds in list(sorted_d.items())[(page-1)*20:page*20]: # {((4 - len(str(cnt)))) * " "} # {(7 - len(str(round(member_seconds/60/60, 2))))*" "} # {" "*(4 -len(str(get_level(member_seconds))))}
					try:
						nickname = dict_nicknames[member_id]
					except KeyError:
						nickname = member_id
					formatted += f""" {str(cnt := list(sorted_d).index(member_id) + 1)+".":<5}{round(member_seconds/60/60,2):<7} [ {get_level(member_seconds):<4} ]( {nickname} )\n"""

		await ctx.send(formatted+"```")


	@commands.command(pass_context=True)
	async def update(self, ctx, token=False):
		""" manually run through all channels and update into data.json """

		if ctx.message.author.id not in get.top_level_users:
			return

		copy = self.user_updates.copy()

		async with self.lock:
			await self.writeInData() # Update everyone who is currently in

		class member:
			def __init__(self, i):
				self.id = i

		member = member(0)

		for server in bot.guilds: # list of guilds
			for details in server.channels: # list of server channels
				if str(details.type) == "voice":
					if details.voice_states:
						for i in details.voice_states: # dict { id : info}
							member.id = i
							await self.on_voice_state_update(member, None, "joined")

		async with self.lock:
			await self.writeInData()
		
		printv(2, "\nCalled an update:\n\tUser actions: ", self.user_actions, "\n\tUser joins: ", self.user_joins, "\n\tUser updates: ", copy)

		return await ctx.send("Updated")

	@tasks.loop(minutes=5.0)
	async def updater(self):
		async with self.lock:
			await self.writeInData()


# cog setup
async def setup(bot):
	await bot.add_cog(Levels(bot))
