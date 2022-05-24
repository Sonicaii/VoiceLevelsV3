# recycled

# import asyncio
from __main__ import *
from discord.utils import snowflake_time

class Misc(commands.Cog):
	global stop

	def __init__(self, bot):
		self.bot = bot

	@commands.Cog.listener()
	async def on_ready(self):
		printv(cogpr("Misc", client))

	async def cog_unload(self):
		pass

	# @commands.command(pass_context=True, name="echo", aliases=["e"])
	# async def echo(self, ctx):
	# 	await ctx.send("echo")

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

	@commands.command(pass_context=True, name="stop")
	@commands.is_owner()
	async def stop(self, ctx):
		ctx.channel.send("Killed process")
		exit()

	@app_commands.command(name="command-1")
	async def my_command(self, interaction: discord.Interaction) -> None:
		""" /command-1 """
		await interaction.response.send_message("Hello from command 1!", ephemeral=True)


async def setup(bot):
	await bot.add_cog(Misc(bot))
