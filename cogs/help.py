from typing import Any

if __name__ == "__main__":
	exit()
	# exits if not imported

from __main__ import *

class Help(commands.Cog, name='Help'):

	def __init__(self, bot):
		self.bot = bot

	@commands.Cog.listener()
	async def on_ready(self):
		printv(cogpr("Help", client))

	@commands.group(name="help", invoke_without_command=True)
	async def help_command(self, ctx, *cog):

		if not cog:
			embed = discord.Embed(description="_ _\n_ _", colour=0xffffff)

			desc: list = ["" for i in range(4)]

			modules: list = [('``top     ``', '''This command lists the server's members by voice level rank.
*``Alternate prefixes: leaderboard, ranks``*'''),
					   ('``total   ``', '''This command gives your total time in seconds, minutes, hours and days.
if you mention someone, then you get their stats.
*``Alternate prefixes: to, seconds``*'''),
					   ('``level   ``', '''This command gives your or the mentioned person their actual calculated time.
*``Alternate prefixes: t, time, lvl, l, info and i``*'''),
					   ('``snipe   ``', '''This command gives you the most recent message that was deleted.
Putting a number after "snipe" will get you the message that was deleted at the specified distance away.
*``e.g. snipe 3 will get the message 3 deleted messages ago.``*''')
					   ]



			misc: list = [('``echo    ``', 'echo...'),
					('``members ``', '''This command gives you the amount of members of this server.
*``Alternate prefixes: m``*'''),
					('``ping    ``', '''This command gives you the latency of this bot.
*``Alternate prefixes: latency``*'''),
					('``lookup  ``', '''This command translate Discord snowflake IDs (any Discord ID)
to their date of creation. Discord IDs are linked to their creation time.
*``Alternate prefixes: lk``*'''),
					('``memes   ``', '''do "help memes" for more details.'
"memes" toggles meme replies server-wide''')
					]

			if not ctx.guild:
				await ctx.send(f'{ctx.author.mention}, **IMPORTANT**\n**RUN "STOP" TO KILL BOT IN CASE OF EMERGENCY**')
				adm = [('status', '''This command changes the bot's status.
The second word in this command dictates the status being used.
Available status messages: playing, listening, watching.
*Anything else will cause a light error that resets the status message.*
*"listening" makes it show "listening to ___".*
e.g. "status listening Megalovania" will change the status to "Listening to Megalovania".\n\n'''),
					   ('any channel id', 'Pasting any channel ID that that bot has access to gives you access to '
										  f'''what the bot says.
e.g. "{ctx.author.dm_channel.id}" will select your own DM channel.
If the bot can't select that channel for some reason, it will give you the error message.''')]
				amd_2 = [('/', 'This command lets you send a message to the channel that you have selected with the '
							   '''previous command.
e.g. "s owo ** *notices bulge* **" will send "owo ** *notices bulge* **" wherever you told it to send it.
If the bot can't send in that channel for some reason, it will give you the error message.'''),
						 ('link', '''This command lets you link the selected channel\'s messages with your DM so you can
	see the messages without switching between channels. *wip i guess?*'''),
						 ('j', 'This command lets you join the voice channel that you have selected with the selection '
							 f'''command
If the bot can't join that voice channel for some reason, it will give you the error message.
**WIP**''')]
				embed.add_field(name='**IMPORTANT**', value='**RUN "STOP" TO KILL BOT IN CASE OF EMERGENCY**',
								inline=False)
				for x, y in adm:
					desc[2] += f'**{x}** - {y}'
				for x, y in amd_2:
					desc[3] += f'**{x}** - {y}\n\n'

			for x, y in modules:
				desc[0] += f'**{x}** - {y}\n\n'
			for x, y in misc:
				desc[1] += f'**{x}** - {y}\n\n'

			embed.add_field(name='Commands', value=desc[0])
			embed.add_field(name='''_ _
Miscellaneous''', value=desc[1], inline=False)

			if not ctx.guild and ctx.author.id in get.top_level_users:
				embed.add_field(name='''_ _
Commands just for you~''', value=desc[2])
				embed.add_field(name='''_ _''', value=desc[3], inline=False)

			embed.set_author(name="Help Panel")
			# embed.set_author(name='test', url=Embed.Empty, icon_url=Embed.Empty)

			await ctx.send(embed=embed)

async def setup(bot):
	await bot.add_cog(Help(bot))
