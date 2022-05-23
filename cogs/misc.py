# recycled
if __name__ == "__main__":
	exit()
	# exits if not imported

# import asyncio
from __main__ import *
from discord.utils import snowflake_time

global reSync

class reSync(dict):
	""" I/O External commands hanlder """

	def __init__(self):
		self.updatelist = {}
		self.update_error = False

		self.returnmsg = {
			"update": False,
			"return": ""
		}

	def init(self, module_name: str) -> bool:
		""" Initialise Sync for module """

		if self.__contains__(module_name):
			raise NameError

		self.__setitem__(module_name, {})
		return True


	def _re(self, name: str="shared.json") -> dict:
		with open(name, "w") as r_shared:
			r_shared.seek(0)
			json.dump(self.returnmsg, r_shared)
			return self.returnmsg


	def __call__(self, recurse: int=0):
		""" Sync """
		name = "shared.json"
		new = {}
		returnmsg_old = self.returnmsg

		try:
			with open(name, "r") as r_shared:
				try:
					new = json.load(r_shared)
				except ValueError:
					new = self._re()

		except FileNotFoundError:
			# No file exists yet
			if recurse > 2: # This was called multiple times
				printv(1, "unable to create file")

				self.__call__ = lambda self, *args, **kwargs: None

			printv(1, name, "not found, creating one")
			self._re()
			
			return self.__call__(recurse+1)
		except json.decoder.JSONDecodeError:
			printv(1, name, "had invalid JSON, rewriting")
			self._re()

		loop = asyncio.get_event_loop()
		class ctx:
				async def send(*a, **k): None
				class author:
					id = client.AppInfo.owner.id
				class message: ...

		if "reload" in new.keys():
			ctx.message.content = "..r " + new["reload"]
			loop.create_task(get.func.reload(ctx))
			self.returnmsg["return"] += "\nreloaded cog " + new["reload"]
			del new["reload"]

		elif "load" in new.keys():
			ctx.message.content = "..ld " + new["load"]
			loop.create_task(get.func.load(ctx))
			self.returnmsg["return"] += "\nloaded cog " + new["load"]
			del new["reload"]

		del loop
		if returnmsg_old == self.returnmsg:
			with open(name, "w") as f:
				# json.dump({**pre.rb(globals()), **{"update": False}}, f)
				json.dump({**self.returnmsg, **{"update": False}}, f)
				self.returnmsg["return"] = ""
					

reSync = reSync()


class Misc(commands.Cog):
	global stop

	def __init__(self, bot):
		self.bot = bot

	@commands.Cog.listener()
	async def on_ready(self):
		printv(pre.cogpr("Misc", client))
		# print(dir(synccmd))
		synccmd.sync_start()
		try:
			await self.refresh_globals.start()
		except RuntimeError:
			pass

	async def cog_unload(self):
		await self.refresh_globals.cancel()


	@commands.command(pass_context=True, name="echo", aliases=["e"])
	async def echo(self, ctx):
		await ctx.send("echo")

	@commands.command(pass_context=True, aliases=["m"])
	async def members(self, ctx):
		await ctx.send(f"Number of members in this server: {ctx.guild.member_count}")

	@commands.command(pass_context=True, name="ping", aliases=["latency"])
	async def ping(self, ctx):
		await ctx.send(f"Current latency is {round(client.latency * 1000)}ms")

	@commands.command(pass_context=True, name="lookup", aliases=["lk", "snowflake", "when"])
	async def lookup(self, ctx):
		name = ""
		if len(ctx.message.mentions) != 0:
			id_ = ctx.message.mentions[0].id
			msg = f"{ctx.message.mentions[0].name}'s ID,"
		else:
			id_ = ctx.message.content.split()[1] \
			.lstrip("<@") \
			.lstrip("!") \
			.rstrip(">")
			msg = ""

		try:
			utc = snowflake_time(int(id_))
		except ValueError:
			return await ctx.send(f"Invalid input")
		else:
			return await ctx.send(f"{msg} ``{id_}`` translates to ``{utc}`` UTC")

	@tasks.loop(seconds=5)
	async def refresh_globals(self):
		""" ??? """

		return # reSync()

		new = json.load(open("shared.json"))
		if type(new) == dict:
			if "update" not in new:
				new["update"] = False
			if not new["update"]:
				json.dump({**pre.rb(globals()), **{"update": False}}, open("shared.json", "w"))
				return
			if "reload" in new.keys():
				class ctx:
					class author:
						id = get.top_level_users[0]
					class message:
						content = "..r " + new["reload"]
				await reload(ctx)
				

		del new["update"]

		for var, val in new.items():
			exec("global var; var = val")

		new["update"] = False

	@commands.Cog.listener()
	async def on_message(self, ctx):
		if ctx.author.id in get.top_level_users and "..stop" in ctx.content.lower():
			ctx.channel.send("Killed process")
			exit()


def setup(bot):
	bot.add_cog(Misc(bot))
