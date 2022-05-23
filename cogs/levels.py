if __name__ == "__main__":
	exit()
	# exits if not imported

from __main__ import *


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

def check_JSON(file: object) -> bool:
	try:
		json.load(file)
	except ValueError:
		return False
	else:
		return True


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
			i: {} for i in range(10)
		}
		# 0: {}, 1: {}, 2: {}, 3: {}, 4: {}, 5: {}, 6: {}, 7: {}, 8: {}, 9: {}


	async def writeInData(self) -> None:
		""" this function writes the data into the long term data file """

		class user: ... # looks better lol

		for last_int in self.user_updates:

			# if empty
			if not self.user_updates[last_int]: continue

			# opens file
			with open(f"data - Copy ({last_int}).json", "r+") as file_obj:
				# reads
				dict_data: dict = json.load(file_obj)

				# loops through user's IDs and times
				for user.id, user.time in self.user_updates[last_int].items():

					if str(user.id) not in dict_data:
						dict_data[str(user.id)] = 0

					# adds time
					dict_data[str(user.id)] += user.time

				# writes from beginning
				file_obj.seek(0)
				json.dump(dict_data, file_obj, indent=2)

		# file with ALL data
		# 
		# if False:
		
		# checking if valid JSON
		rewrite: bool = False
		with open("data - All.json", "r") as raw:
			if not check_JSON(raw):
				rewrite = True
		if rewrite:
			print("REWRITING : INVALID JSON")
			with open("data - All.json", "w") as raw:
				raw.seek(0)
				raw.write(r"{}")
		
		with open("data - All.json", "r") as file_obj:

			# very large data object
			large_dict: dict = json.load(file_obj)

			# flattening, removing by-suffix-int segregation
			for dict_timedata in self.user_updates.values():
				for user.id, user.time in dict_timedata.items():
					try:
						large_dict[str(user.id)] += user.time
					except KeyError:
						large_dict[str(user.id)] = user.time

		with open("data - All.json", "w") as file_obj:
			file_obj.seek(0)
			json.dump(large_dict, file_obj, indent=2)

		self.user_updates = {
			i: {} for i in range(10)
		}
		# 0: {}, 1: {}, 2: {}, 3: {}, 4: {}, 5: {}, 6: {}, 7: {}, 8: {}, 9: {}

		self.user_actions = []

	@commands.Cog.listener()
	async def on_ready(self):

		await client.change_presence(activity=discord.Activity(name="Mega" + 'lov' + 'ania',
		type=discord.ActivityType.listening))

		printv(fg.g(f"\n{client.user.name} Main Activated")+f"\n{time.ctime()}")
		printv(2, "user ID:", client.user.id)
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
			self.user_updates[int(str(member.id)[-1])][member.id]: int = 0

		# change update time
		self.user_updates[int(str(member.id)[-1])][member.id] += int(time.time()) - self.user_joins[member.id]

		# removes from needing updates
		if type(after) != str:
			if after.channel == None:
				del self.user_joins[member.id]
				return

		# if it was not a leave: restart the count
		# starts the count if it was a first time join
		self.user_joins[member.id] = int(time.time())

		return


	@commands.command(pass_context=True, name="total", aliases=["to", "seconds"])
	async def total(self, ctx):
		""" Return's the user's time in seconds """

		try:
			lookup_id = int(ctx.message.split()[-1])
		except ValueError:
			lookup_id = ctx.message.author.id if len(ctx.message.mentions) == 0 else ctx.message.mentions[0].id

		if lookup_id in self.user_actions:
			async with self.lock:
				await self.writeInData()

		# opens the corresponding file
		with open(f"data - Copy ({str(lookup_id)[-1]}).json", "r") as file_obj:
			
			all_user_times = json.load(file_obj)
			if str(lookup_id) not in all_user_times:
				# record does not exist
				return await ctx.send(f"<@!{lookup_id}> has no time saved yet.")

			# gets live info and the user times
			current_user_time = \
				all_user_times[str(lookup_id)] + int(time.time()) - self.user_joins[lookup_id] \
			if ctx.message.author.id in self.user_joins else \
				all_user_times[str(lookup_id)]

			await ctx.send(f"{ctx.message.author.name if len(ctx.message.mentions) == 0 else ctx.message.mentions[0].name} has spent {current_user_time} seconds in voice channels")

		return

	@commands.command(pass_context=True, aliases=['t', 'level', 'lvl', 'l', 'info', 'i'])
	async def time(self, ctx):
		""" returns human readable text """

		lookup_id = ctx.message.author.id if len(ctx.message.mentions) == 0 else ctx.message.mentions[0].id

		if lookup_id in self.user_actions:
			async with self.lock:
				await self.writeInData()


		# opens the corresponding file
		with open(f"data - Copy ({str(lookup_id)[-1]}).json", "r") as file_obj:
			
			all_user_times = json.load(file_obj)
			if str(lookup_id) not in all_user_times:
				# record does not exist
				await ctx.send(f"<@!{lookup_id}> has no time saved yet.")
				return

			# gets live info and the user times
			# current_user_times
			total_seconds = all_user_times[str(lookup_id)]
			cut = datetime.timedelta(seconds=\
					total_seconds + int(time.time()) - self.user_joins[lookup_id] \
				if lookup_id in self.user_joins else \
					total_seconds
			)
			hours, minutes, seconds = str(cut).split()[-1].split(":")

			await ctx.send(f"{ctx.message.author.name if len(ctx.message.mentions) == 0 else ctx.message.mentions[0].name} has spent {cut.days} days, {hours} hours, {minutes.lstrip('0')} minutes and {seconds.lstrip('0')} seconds on call: level {get_level(total_seconds)}")


	@commands.command(pass_context=True, name='top', aliases=['leaderboard', 'ranks'])
	async def top(self, ctx):
		""" leaderboard of the server's times """

		sorted_d = {}

		all_check = ctx.author.id in get.top_level_users and "all" in ctx.message.content
		if all_check:
			total_members = len([member for server in client.guilds for member in server.members])

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

				guild_mem_valid.append((client.user.id, n_def(namestr, client.user.id)))
				guild_members_id.append(client.user.id)


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
					for server in client.guilds:
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

		for server in client.guilds: # list of guilds
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
