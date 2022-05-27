import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from io import BytesIO
from aiohttp import ClientSession
from urllib.parse import urlparse


global debug
debug = False

snipe_target = {}

class View(discord.ui.View):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	@discord.ui.button(
		emoji="\U0001f5d1️",
		style=discord.ButtonStyle.danger
	)
	async def callback(self, interaction: discord.Interaction, select: discord.ui.button):
		# await interaction.response.send_message(
		# 	# f"`Original msg ID:     {og_msg.id}\n" +
		# 	f"`User:                {interaction.user.name} {interaction.user.id}`\n" +
		# 	f"`this msg ID:  {interaction.message.id}`\n" +
		# 	f"`this channel: {interaction.channel}`\n"+
		# 	f"`Data?: {interaction.data}`"
		# 	, ephemeral=True)
		for msg in snipe_target[interaction.channel.id]:
			# locating the message, could rewrite using ordered dict instead
			if msg.id == self.msg.id:
				# the person who clicked the bin button was the original sniper
				if interaction.user.id == self.sniper_id:
					await interaction.response.send_message(f"<@{interaction.user.id}> denied their own hit.")
				else:
					msg.add(self.sniper_id)
					await interaction.response.send_message(f"<@{interaction.user.id}> denied hit and destroyed <@{self.sniper_id}>'s ammunition.")
				await interaction.message.delete()
				await asyncio.sleep(5)

				return await interaction.delete_original_message()

		# This should never send
		await interaction.response.send_message(
			"Something went wrong.\n"
			"Could obtain information on where the bin was attached to\n"
			"This should not have happened, please contact the bot's developer and tell them what you did to get this message",
			ephemeral=True
			)


class msg():
	""" contains message attributes """
	def __init__(self, **kwargs):
		for k, v in kwargs.items():
			self.__setattr__(k, v)

		# set of ids of people who cannot snipe this msg
		self.denied = set()

	def add(self, deny_id: int):
		self.denied.add(deny_id)

	def is_denied(self, id: int) -> bool:
		return id in self.denied


class Snipe(commands.Cog):

	def __init__(self, bot, msg):
		self.bot = bot
		self.msg = msg
		self.del_id = {}

	@commands.Cog.listener()
	async def on_ready(self):
		self.bot.cogpr("Snipe", bot)

	@commands.Cog.listener()
	async def on_message_delete(self, message):
		if message.author == bot.user:
			# Don't log itself
			return

		# split deleted message into 1000 char chunks to avoid 2k char limit
		string = message.content
		for content in (string[0+i:1000+i] for i in range(0, len(string)+1, 1000)):
			message.content = content
			self.o_m_d(message)


	def o_m_d(self, message):

		m_c_id = message.channel.id
		temp_key = message.id

		msg = self.msg(
			author=type("author",(object,), dict( # filter out unused author attributes
				name=message.author.name,
				nick=message.author.nick,
				id=message.author.id
				)
			),
			content=message.content,
			id=message.id,
			# embed=message.embeds[0] if message.embeds else False,
			attachments=[i.url for i in message.attachments]
		)

		if m_c_id in snipe_target:
			temp_append = snipe_target[m_c_id]

			if len(temp_append) > 35:  # arbitrary value of 35: 3500m furthest sniper kill distance
				del temp_append[0]

			temp_append.append(msg)
			snipe_target[m_c_id] = temp_append
		else:
			# Beginning of list\
			snipe_target[m_c_id] = [msg]


	@app_commands.command(name="snipe", description="Snipes messages")
	async def snipe(self, interaction: discord.Interaction, distance: Optional[int]):

		m_c_id = interaction.channel.id

		if distance is not None:
			dist = distance
		else:
			dist = ""

		if dist and snipe_target.get(m_c_id) is not None:
			if dist <= len(snipe_target[m_c_id]):
				snipe_range = -dist
			else:
				snipe_range = -1
		else:
			snipe_range = -1

		if snipe_target.get(m_c_id) is None:
			return await interaction.response.send_message("Couldn't find target to snipe in this channel.", ephemeral=True)
			# Nothing in list currently
		else:
			if snipe_target[m_c_id][snipe_range].is_denied(interaction.user.id):
				return await interaction.response.send_message("You are unable to snipe this message", ephemeral=True)

			if dist:
				if dist > len(snipe_target[m_c_id]):
					return await interaction.response.send_message("Couldn't find target to snipe. No targets that far out.", ephemeral=True)
				else:
					msg = snipe_target[m_c_id][-dist]
					range_msg = f"from {dist}00m"
					if dist > 35:
						range_msg += " which is further than the world's longest confirmed sniper kill"

			else:
				msg = snipe_target[m_c_id][-1]
				range_msg = "the closest target"

			send = f"""<@{interaction.user.id}> hit {msg.author.name}, {range_msg}, who said\n{msg.content}\n"""
			file = None
			if len(msg.attachments) == 1:
				async with ClientSession() as session:
					async with session.get(msg.attachments[0]) as resp:
						if resp.status != 200:
							send += msg.attachments[0]
							await interaction.response.send_message('Could not download attachment file', ephemeral=True)
						file = BytesIO(await resp.read())
			else:
				for url in msg.attachments:
					send += url + "\n"

			view=View()
			view.msg = msg
			view.sniper_id = interaction.user.id
			new_msg = await interaction.response.send_message(
				send,
				# embed=discord.Embed().from_dict(msg.embed) if msg.embed else None,
				file=discord.File(file, os.path.basename(urlparse(msg.attachments[0]).path)) if file else discord.utils.MISSING,
				view=view
			)


async def setup(bot):
	await bot.add_cog(Snipe(bot, msg))
