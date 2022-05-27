import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import snowflake_time
from typing import Union, Optional

class Misc(commands.Cog):

	def __init__(self, bot):
		self.bot = bot

	@commands.Cog.listener()
	async def on_ready(self):
		self.bot.cogpr("Misc", self.bot)

	async def cog_unload(self):
		pass

	@commands.hybrid_command(name="members", description="Gets the number of members in the server")
	async def members(self, ctx: commands.Context):
		await ctx.send(f"Number of members in this server: {ctx.guild.member_count}")

	@commands.hybrid_command(name="latency", description="current latency of bot")
	async def latency(self, ctx: commands.Context):
		await ctx.send(f"Current latency is {round(self.bot.latency * 1000)}ms")

	@commands.hybrid_command(name="ping", description="current latency of bot")
	async def ping(self, ctx: commands.Context):
		# await interaction.pong()  # can't use in this context
		await ctx.send(f"Current latency is {round(self.bot.latency * 1000)}ms")

	async def _process_id(self, interaction: discord.Interaction, thing: Union[discord.Object, int], fmt) -> None:
		try:
			return await interaction.response.send_message(fmt.format(snowflake_time=\
				discord.utils.format_dt(
						snowflake_time(
						int(thing.lstrip("<@").lstrip("!").rstrip(">") if type(thing) == str else thing) \
						if type(thing) == int else \
						thing.id
					)
				)))
		except ValueError:
			return await interaction.response.send_message(f"Invalid input {thing}")

	@app_commands.command(name="id", description="Discord ID to time")
	@app_commands.describe(
		discord_id="The number from \"Copy ID\" in the discord context menu (right click) after enabling Settings>App Settings>Developer Mode"
	)
	@app_commands.rename(
		discord_id="discord-id"
	)
	async def id(self, interaction: discord.Interaction, discord_id: str):
		await self._process_id(interaction, discord.Object(id=discord_id), f"`{discord_id}` is equivalent to {{snowflake_time}}")

	@app_commands.command(name="user", description="Get when user account was made")
	async def user(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
		if not user: user = interaction.user
		await self._process_id(interaction, user, f"Account creation of {user.name} with the ID of `{user.id}`\ntranslates to {{snowflake_time}}")

	@app_commands.command(name="channel", description="Get when channel was made")
	async def channel(self, interaction: discord.Interaction, channel: Optional[Union[app_commands.AppCommandChannel, discord.Thread]] = None):
		if not channel: channel = interaction.channel
		await self._process_id(interaction, channel, f"{channel.name} with the ID of `{channel.id}`\nwas created at {{snowflake_time}}")

	@commands.hybrid_command(name="prefix", with_app_command=True)
	@commands.has_permissions(manage_guild=True)
	async def prefix(self, ctx, prefix: Optional[str]):
		if prefix:
			if len(prefix) > 16:
				return await ctx.send("Prefix is too long, maximum 16 characters.", ephemeral=True)
			async with ctx.channel.typing():
				with self.bot.conn.cursor() as cur:
					cur.execute("""
						INSERT INTO prefixes (id, prefix)
						VALUES (%s, %s)
						ON CONFLICT (id) DO UPDATE
							SET prefix = EXCLUDED.prefix
						""", (str(ctx.guild.id), prefix))
				await ctx.send(f"New prefix set to: {prefix}")
		else:
			await ctx.send("Reset prefix to `,,`")

	@commands.command(pass_context=True, name="stop")
	@commands.is_owner()
	async def stop(self, ctx):
		await ctx.channel.send("Killed process (might auto-reload, run another stop after)")
		exit()

	@app_commands.command(name="stop", description="STOP")
	async def stop(self, interaction: discord.Interaction):
		await interaction.response.send_message("Killed process (might auto-reload, run another stop after)", ephemeral=True)
		exit()

async def setup(bot):
	await bot.add_cog(Misc(bot))
