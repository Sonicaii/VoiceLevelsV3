from typing import Any, Optional, Literal
import discord
from discord import app_commands
from discord.ext import commands

class Help(commands.Cog, name='Help'):

	def __init__(self, bot):
		self.bot = bot

	@commands.Cog.listener()
	async def on_ready(self):
		self.bot.cogpr("Help", self.bot)

	@app_commands.command(name="help", description="Get help about Voice Level's functions!")
	async def help(self, interaction: discord.Interaction,
		subcommand: Optional[Literal["levels", "snipe",]]
	):
		msg = ""
		embed = discord.Embed(description="_ _\n_ _", colour=0xf0fff0)

		desc: list = ["" for i in range(4)]

		modules: list = [('``top     ``', '''This command lists the server's members by voice level rank.
*``Aliases: leaderboard, all``*'''),
				   ('``total   ``', '''This command gives your total time in seconds, minutes, hours and days.
*``Aliases: seconds``*'''),
				   ('``level   ``', '''This command gives your or the mentioned person their actual calculated time.
*``Aliases: time, info``*'''),
				   ('``snipe   ``', '''This command gives you the most recent message that was deleted.
Putting a number after "snipe" will get you the message that was deleted at the specified distance away.
*``e.g. snipe 3 will get the message 3 deleted messages ago.``*''')
				   ]

		misc: list = [('``echo    ``', 'echo...'),
				('``members ``', 'This command gives you the amount of members of this server.'),
				('``ping    ``', 'This command gives you the latency of this bot.\n*``Aliases: latency``*'),
				('``lookup  ``', '''This command translate Discord snowflake IDs (any Discord ID)
to their date of creation. Discord IDs are linked to their creation time.
*``Aliases: lk``*'''),
				('``memes   ``', '''do "help memes" for more details.'
"memes" toggles meme replies server-wide''')
				]

		if interaction.user.id in self.bot.sudo and not interaction.guild:
			msg = f'**IMPORTANT**\n**RUN "STOP" TO KILL BOT IN CASE OF EMERGENCY**'
			embed.add_field(name='**IMPORTANT**', value='**RUN "STOP" TO KILL BOT IN CASE OF EMERGENCY**',inline=False)

		for x, y in modules:
			desc[0] += f'**{x}** - {y}\n\n'
		for x, y in misc:
			desc[1] += f'**{x}** - {y}\n\n'

		embed.add_field(name='Commands', value=desc[0])
		embed.add_field(name='_ _\nMiscellaneous', value=desc[1], inline=False)
		embed.set_author(name="Help Panel")

		await interaction.response.send_message(msg, embed=embed)

async def setup(bot):
	await bot.add_cog(Help(bot))
