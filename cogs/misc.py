import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Greedy
from discord.utils import snowflake_time
from datetime import datetime, timedelta
from os import SEEK_END
from typing import Literal, Optional, Union
from re import findall, sub


def reverse_readline(filename, buf_size=8192):
	"""A generator that returns the lines of a file in reverse order"""
	# https://stackoverflow.com/questions/2301789/how-to-read-a-file-in-reverse-order
	with open(filename) as fh:
		segment = None
		offset = 0
		fh.seek(0, SEEK_END)
		file_size = remaining_size = fh.tell()
		while remaining_size > 0:
			offset = min(file_size, offset + buf_size)
			fh.seek(file_size - offset)
			buffer = fh.read(min(remaining_size, buf_size))
			remaining_size -= buf_size
			lines = buffer.split('\n')
			# The first line of the buffer is probably not a complete line so
			# we'll save it and append it to the last line of the next buffer
			# we read
			if segment is not None:
				# If the previous chunk starts right from the beginning of line
				# do not concat the segment to the last line of new chunk.
				# Instead, yield the segment first
				if buffer[-1] != '\n':
					lines[-1] += segment
				else:
					yield segment
			segment = lines[0]
			for index in range(len(lines) - 1, 0, -1):
				if lines[index]:
					yield lines[index]
		# Don't yield None if the file was empty
		if segment is not None:
			yield segment


class Misc(commands.Cog):

	def __init__(self, bot):
		self.bot = bot
		self.deliver = bot.deliver

	@commands.command(pass_context=True, name="uptime", description="Get uptime of bot")
	async def uptime(self, ctx: commands.Context):
		if ctx.author.id in self.bot.sudo:
			await self.deliver(ctx)(f"Time since last restart: {timedelta(seconds=(datetime.now()-self.bot.start_time).seconds)}\nOn <t:{int(datetime.timestamp(self.bot.start_time))}:D>")

	@commands.hybrid_command(name="members", description="Gets the number of members in the server")
	async def members(self, ctx: commands.Context):
		await self.deliver(ctx)(f"Number of members in this server: {ctx.guild.member_count}")

	@commands.hybrid_command(name="latency", description="current latency of bot")
	async def latency(self, ctx: commands.Context):
		await self.deliver(ctx)(f"Current latency is {round(self.bot.latency * 1000)}ms")

	@commands.hybrid_command(name="ping", description="current latency of bot")
	async def ping(self, ctx: commands.Context):
		# if ctx.interaction:
			# return await ctx.interaction.response.pong()  # What does this even do
		await self.deliver(ctx)(f"Current latency is {round(self.bot.latency * 1000)}ms")

	async def _process_id(self, interaction: discord.Interaction, thing: Union[discord.Object, int, str], fmt) -> None:
		try:
			msg = fmt.format(snowflake_time=discord.utils.format_dt(
				snowflake_time(
					int(thing.id)
				if hasattr(thing, "id") else
					int(
						findall(r"(?<=[<@#!:a-z])(\d+)", thing)[0]
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
		_ = "`" if discord_id.isdigit() else ""
		await self._process_id(interaction, discord_id, f"{_}{discord_id}{_} is equivalent to {{snowflake_time}}")

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

	@commands.command(name="prefix")
	@commands.has_permissions(manage_guild=True)
	async def cmd_prefix(self, ctx):
		for pre in await self.bot.get_prefix(ctx.message):  # 1-liner possible here
			if ctx.message.content.startswith(pre):
				break
		await self.prefix(ctx, ctx.message.content[len(pre)+6:].lstrip())

	@app_commands.command(name="prefix")
	@commands.has_permissions(manage_guild=True)
	async def app_cmd_prefix(self, ctx, prefix: Optional[str]):
		await self.prefix(ctx, prefix)

	async def prefix(self, ctx, prefix):
		if not ctx.guild:
			self.deliver(ctx)("Setting prefixes outside servers unsupported")
		with self.bot.conn.cursor() as cur:
			msg = "Reset prefix to: \"%s\""
			if prefix:
				if prefix.endswith(" \\"):
					prefix = prefix[:-1]
				if len(prefix) > 16:
					return await self.deliver(ctx)("Prefix is too long, maximum 16 characters.", ephemeral=True)
				async with ctx.channel.typing():
					cur.execute("""
						INSERT INTO prefixes (id, prefix)
						VALUES (%s, %s)
						ON CONFLICT (id) DO UPDATE
							SET prefix = EXCLUDED.prefix
						""", (str(ctx.guild.id), prefix))
					await self.deliver(ctx)(msg % self.bot.discord_escape(prefix))
			else:
				cur.execute("DELETE FROM prefixes WHERE id ~ %s", (str(ctx.guild.id),))
				await self.deliver(ctx)(msg % self.bot.default_prefix)
		self.bot.conn.commit()
		self.bot.prefix_cache_pop(ctx.guild.id)

	@commands.command(pass_context=True, name="stop")
	@commands.is_owner()
	async def stop(self, ctx):
		await ctx.channel.send("Killed process (might auto-reload, run another stop after)")
		exit()

	@commands.command(pass_context=True, name="tail")
	async def tail(self, ctx, lines: Optional[int] = 10):
		if ctx.author.id not in self.bot.sudo:
			return
		gen = reverse_readline("discord.log")
		txt = ""
		line = 0
		try:
			while len((n:=sub(r"\[[\w\s]*\] discord(\.(\w\w*\.?)*)?:", "", next(gen))) + txt) + 1< 1989 and line <= lines:
				txt = "\n" + n + txt
				line += 1
		except StopIteration:
			pass

		await self.deliver(ctx)("```ansi\n"+sub(r"(\033\[(\d*;?)*m)?(```)?", "", txt[max(txt.find("\n"), 11):])+"```")

	@commands.command(name="stop", description="STOP")
	async def stop(self, interaction: discord.Interaction):
		try:
			await self.deliver(interaction)("Killed process (might auto-reload, run another stop after)", ephemeral=True)
		finally:
			exit()

	@commands.command(pass_context=True, name="cache_size")
	async def cache_size(self, ctx: commands.Context):
		if ctx.author.id not in self.bot.sudo:
			return
		await self.deliver(ctx)(f"Cache size is: {self.bot.prefix_cache_size()}")


async def setup(bot):
	await bot.add_cog(Misc(bot))
