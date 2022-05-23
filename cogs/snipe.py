# recycled
if __name__ == "__main__":
	exit()
	# exits if not imported


from __main__ import *
from io import BytesIO
from aiohttp import ClientSession
from urllib.parse import urlparse

global debug
debug = True if "snipe" in debugs else False

del_ammo_out, used_comb = [], []
snipe_target = {}

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

class org_msg:
	"""
		message organiser

	how to snipe:
	1. target sends message
	2. on_msg_del:
		- create entry in channel_dict if it doesn't exist yet
		- collect msg 
			.id: int.
			.content: str
			.author.id: int
			.embeds: list[]: object # doesn't work
			.attachments[list].url: str
		- add to stack
	3. 

	"""

	def __init__(self):
		self.channel_dict = {}

	def new_channel_history(self, channel_id: int):
		self.channel_dict[channel_id] = {}

	def id_set(self, channel_id: int, bot_msg_id: int, reference_to: int):
		if channel_id not in self.channel_dict:
			self.new_channel_history(channel_id)

		self.channel_dict[channel_id][bot_msg_id] = reference_to

	def get(self, channel_id: int, bot_msg_id: int):
		""" Returns reference """

		self.clean(channel_id)
		return self.channel_dict[channel_id][bot_msg_id]

	def clean(self, channel_id: int):
		""" deletes first item """

		try: # Nothing in channel_dict[channel_id]
			if len(self.channel_dict[channel_id]) > 40:
				first_item_index = next(iter(self.channel_dict[channel_id]))
				del self.channel_dict[channel_id][first_item_index]
		except KeyError:
			pass

org_msg = org_msg()


class SnipeCog(commands.Cog):

	def __init__(self, bot, msg):
		self.bot = bot
		self.msg = msg
		self.del_id = {}

	@commands.Cog.listener()
	async def on_ready(self):
		printv(pre.cogpr("Snipe", client))


	@commands.Cog.listener()
	async def on_reaction_add(self, reaction, user):
		# user is who sniped, i_temp is the key to link to original message's target
		if user == client.user or user.bot:  # self check, bot check
			return

		r_id = reaction.message.id
		r_m_ch = reaction.message.channel

		if self.del_id.get(r_id) is not None:
			async with reaction.message.channel.typing():
				for i1 in range(len(self.del_id)):
					if self.del_id[r_id][i1] == r_id:
						who_sniped = reaction.message.mentions[0].id
						del self.del_id[r_id][i1]
						break
				cnt = 0

				org_message_id = org_msg.get(reaction.message.channel.id, r_id)


				for msg in snipe_target[r_m_ch.id]:
					if int(msg.id) == int(org_message_id):
						if who_sniped != user.id:
							snipe_target[r_m_ch.id][cnt].denied.add(who_sniped)
						break
					cnt += 1

				if who_sniped != user.id:
					await r_m_ch.send(
						f"<@{user.id}> denied hit and destroyed the sniper's ammunition.",
						delete_after=5
					)
				else:
					await r_m_ch.send(
						f"<@{user.id}> denied their own hit.",
						delete_after=5
					)
				return await reaction.message.delete()

	@commands.Cog.listener()
	async def on_message_delete(self, message):
		if message.author == client.user:
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
		# if debug:
		# 	print(snipe_target)

		if m_c_id in snipe_target:
			temp_append = snipe_target[m_c_id]

			if len(temp_append) > 40:
				org_msg.clean(m_c_id) #[temp_append[0][3]]
				del temp_append[0]

			# temp_append.append([message.author.name, message.content, {}, temp_key])
			temp_append.append(msg)

			snipe_target[m_c_id] = temp_append
			# snipe_target[m_c_id] = [(message.author.name, message.content)] - for only 1 delete range
		else:
			# Beginning of list
			# V1: snipe_target[m_c_id] = [[message.author.name, message.content, {}, temp_key]]
			snipe_target[m_c_id] = [msg]


	@commands.Cog.listener()
	async def on_message(self, message):
		global org_msg

		pre = get.prefix_filter(message)
		pre = ".."

		if message.author != client.user:  # self check
			return

		if len(message.content) > 10 and len(message.mentions) != 0:
			if message.content[len(str(message.mentions[0].id)) + 4:len(str(message.mentions[0].id)) + 7] == 'hit':
				try:
					await message.add_reaction('\U0001f5d1️')
				except Exception as e:
					await message.channel.send("Unable to set up the snipe bin.", delete_after=5)
					print(ferror(e))
					await message.delete()

				if message.mentions[0].id in self.del_id:
					l_temp = self.del_id[message.mentions[0].id]
					l_temp.append(message.id)
				else:
					l_temp = [message.id]
				self.del_id[message.id] = l_temp

	# @commands.guild_only()
	@commands.command(
		pass_context=True, name='snipe', aliases=['no'+'scope', 'quick' + 'scope']) # '360 no'+'scope']) Does not work
	async def snipe(self, ctx):
		pre = ".."
		# if not ctx.message.content.lower()[:len('..snipe')] == '..snipe':
		#     return

		m_c_id = ctx.channel.id

		if len(ctx.message.content.split()[1:]) == 1 and ctx.message.content.split()[1].isnumeric():
			dist = int(ctx.message.content.split()[1])
		else:
			dist = ""

		if dist and snipe_target.get(m_c_id) is not None:
			if debug:
				print('if correct range:', dist <= len(snipe_target[m_c_id]))
			if dist <= len(snipe_target[m_c_id]):
				snipe_range = -dist
			else:
				snipe_range = -1
		else:
			snipe_range = -1

		if snipe_target.get(m_c_id) is None:
			return await ctx.send("Couldn't find target to snipe in this channel.")
			# Nothing in list currently
		else:
			if snipe_target[m_c_id][snipe_range].is_denied(ctx.author.id):
				return await ctx.send("You are unable to snipe this message")

			if dist:
				if dist > len(snipe_target[m_c_id]):
					return await ctx.send("Couldn't find target to snipe. No targets that far out.")
				else:
					msg = snipe_target[m_c_id][-dist]
					range_msg = f"from {dist}00m"

			else:
				msg = snipe_target[m_c_id][-1]
				range_msg = "the closest target"

			send = f"""<@{ctx.author.id}> hit {msg.author.name}, {range_msg}, who said\n{msg.content}\n"""
			file = None
			if len(msg.attachments) == 1:
				async with ClientSession() as session:
					async with session.get(msg.attachments[0]) as resp:
						if resp.status != 200:
							send += msg.attachments[0]
							await ctx.send('Could not download attachment file', delete_after=5)
						file = BytesIO(await resp.read())
			else:
				for url in msg.attachments:
					send += url + "\n"

			global org_msg
			new_msg = await ctx.send(
				send,
				# embed=discord.Embed().from_dict(msg.embed) if msg.embed else None,
				file=discord.File(file, os.path.basename(urlparse(msg.attachments[0]).path)) if file else None
			)
			# nmc_id = new_msg.channel.id
			org_msg.id_set(new_msg.channel.id, new_msg.id, msg.id)
			
			return new_msg

def setup(b):
	b.add_cog(SnipeCog(b, msg))
