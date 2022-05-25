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
		printv(cogpr("Misc", bot))

	async def cog_unload(self):
		pass

	# @commands.command(pass_context=True, name="echo", aliases=["e"])
	# async def echo(self, ctx):
	# 	await ctx.send("echo")

	@app_commands.command(name="members", description="Gets the number of members in the server")
	async def members(self, interaction: discord.Interaction):
		await interaction.response.send_message(f"Number of members in this server: {interaction.guild.member_count}")

	# alias: latency
	@app_commands.command(name="ping", description="current latency of bot")
	async def ping(self, interaction: discord.Interaction):
		await interaction.response.send_message(f"Current latency is {round(bot.latency * 1000)}ms")

	@app_commands.command(name="when", description="Translates any Discord element's ID to the time when it was created")
	async def when(self, interaction: discord.Interaction, id: Greedy[Object]):
		return await interaction.response.send_message(id)
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
