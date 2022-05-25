# recycled

# import asyncio
# bad practice but ... fix later
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

	@app_commands.command(name="members", description="Gets the number of members in the server")
	async def members(self, interaction: discord.Interaction):
		await interaction.response.send_message(f"Number of members in this server: {interaction.guild.member_count}")

	# alias: latency
	@app_commands.command(name="ping", description="current latency of bot")
	async def ping(self, interaction: discord.Interaction):
		await interaction.response.send_message(f"Current latency is {round(bot.latency * 1000)}ms")

	async def _process_id(self, interaction: discord.Interaction, thing: Union[discord.Object, int], fmt) -> None:
		try:
			return await interaction.response.send_message(fmt.format(snowflake_time=\
				snowflake_time(
					int(thing.lstrip("<@").lstrip("!").rstrip(">") if type(thing) == str else thing) \
					if type(thing) == int else \
					thing.id
				)))
		except ValueError:
			return await interaction.response.send_message(f"Invalid input {thing}")

	@app_commands.command(name="id", description="Discord ID to time")
	async def id(self, interaction: discord.Interaction, discord_id: int):
		await _process_id(interaction, discord_id, f"`{discord_id}` is equivalent to `{{snowflake_time}}` UTC")

	@app_commands.command(name="user", description="Get when user account was made")
	async def user(self, interaction: discord.Interaction, user: discord.User):
		await _process_id(interaction, user, f"Account creation of {user.name} with the ID of `{user.id}`\ntranslates to `{{snowflake_time}}` UTC")

	# @app_commands.command(name="channel", description="Get when channel was made")
	# async def channel(self, interaction: discord.Interaction, Channel: Choice[discord.TextChannel]):
	# 	await _process_id(interaction, user, f"{Channel.name} with the ID of `{Channel.id}`\nwas created at `{{snowflake_time}}` UTC")

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
