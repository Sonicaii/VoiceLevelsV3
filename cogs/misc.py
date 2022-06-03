import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import snowflake_time
from typing import Union, Optional
from re import findall

class Misc(commands.Cog):

	def __init__(self, bot):
		self.bot = bot
		self.deliver = bot.deliver

	@commands.Cog.listener()
	async def on_ready(self):
		self.bot.cogpr("Misc", self.bot)

	async def cog_unload(self):
		pass

	@commands.hybrid_command(name="members", description="Gets the number of members in the server")
	async def members(self, ctx: commands.Context):
		await self.deliver(ctx)(f"Number of members in this server: {ctx.guild.member_count}")

	@commands.hybrid_command(name="latency", description="current latency of bot")
	async def latency(self, ctx: commands.Context):
		await self.deliver(ctx)(f"Current latency is {round(self.bot.latency * 1000)}ms")

	@commands.hybrid_command(name="ping", description="current latency of bot")
	async def ping(self, ctx: commands.Context):
		if ctx.interaction:
			# return await ctx.interaction.response.pong()  # What does this even do
		await self.deliver(ctx)(f"Current latency is {round(self.bot.latency * 1000)}ms")

	async def _process_id(self, interaction: discord.Interaction, thing: Union[discord.Object, int, str], fmt) -> None:
		try:
			msg = fmt.format(snowflake_time=discord.utils.format_dt(
				snowflake_time(
					int(thing.id) \
				if hasattr(thing, "id") else \
					int(
						findall(r"(?<=[<@#!:a-z])(\d+)", thing)[0] \
						if type(thing) is str and not thing.isdigit() else thing
					)
				),
				style="F"
			))
		except (ValueError, IndexError):
			msg = f"Invalid input: {thing}"
		return await self.deliver(interaction)(msg)

	@app_commands.command(name="id", description="Discord ID to time")
	@app_commands.describe(
		discord_id="The number from \"Copy ID\" in the discord context menu (right click) after enabling Settings>App Settings>Developer Mode"
	)
	@app_commands.rename(
		discord_id="discord-id"
	)
	async def id(self, interaction: discord.Interaction, discord_id: str):
		print(discord_id)

		await self._process_id(interaction, discord_id, f"`{discord_id}` is equivalent to {{snowflake_time}}")

	@app_commands.command(name="user", description="Get when user account was made")
	async def user(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
		if not user: user = interaction.user
		await self._process_id(interaction, user, f"Account creation of {user.name} with the ID of `{user.id}`\ntranslates to {{snowflake_time}}")

	@app_commands.command(name="channel", description="Get when channel was made")
	async def channel(self, interaction: discord.Interaction, channel: Optional[Union[app_commands.AppCommandChannel, discord.Thread]] = None):
		if not channel: channel = interaction.channel
		await self._process_id(interaction, channel, f"{channel.name} with the ID of `{channel.id}`\nwas created at {{snowflake_time}}")

	@commands.hybrid_command(name="lookup", with_app_command=True)
	async def lookup(self, ctx: commands.Context, thing: Optional[str] = None):
		if thing is None: thing = ctx.author.id
		await self._process_id(ctx, thing, f"{thing} translates to {{snowflake_time}}")

	@commands.hybrid_command(name="prefix", with_app_command=True)
	@commands.has_permissions(manage_guild=True)
	async def prefix(self, ctx, prefix: Optional[str]):
		with self.bot.conn.cursor() as cur:
			if prefix:
				if len(prefix) > 16:
					return await deliver(ctx)("Prefix is too long, maximum 16 characters.", ephemeral=True)
				async with ctx.channel.typing():
					cur.execute("""
						INSERT INTO prefixes (id, prefix)
						VALUES (%s, %s)
						ON CONFLICT (id) DO UPDATE
							SET prefix = EXCLUDED.prefix
						""", (str(ctx.guild.id), prefix))
					await self.deliver(ctx)(f"New prefix set to: {prefix}")
			else:
				cur.execute("DELETE FROM prefixes WHERE id ~ %s", (str(ctx.guild.id),))
				await self.deliver(ctx)("Reset prefix to `,,`")
		self.bot.conn.commit()
		self.bot._prefix_cache_pop(ctx.guild.id)

	@commands.command(pass_context=True, name="stop")
	@commands.is_owner()
	async def stop(self, ctx):
		await ctx.channel.send("Killed process (might auto-reload, run another stop after)")
		exit()

	@app_commands.command(name="stop", description="STOP")
	async def stop(self, interaction: discord.Interaction):
		await interaction.response.send_message("Killed process (might auto-reload, run another stop after)", ephemeral=True)
		exit()

	@commands.command(pass_context=True, name="cache_size")
	async def cache_size(self, ctx: commands.Context):
		if ctx.author.id not in self.bot.sudo:
			return
		await self.deliver(ctx)(f"Cache size is: {self.bot._prefix_cache_size()}")

async def setup(bot):
	await bot.add_cog(Misc(bot))
