import sys

# only runs if this file is excecuted originally.
if __name__ != "__main__":
	sys.exit(1) # exits with error code 1: failure

# second pass imports
import time; s = time.time()
import datetime, socket, asyncio, random, json, os, subprocess, math
from threading import Thread
from aiohttp.client_exceptions import ClientConnectionError
from asyncio.exceptions import TimeoutError

# preset functions and variables
# from colours import * # unused, @see preset.py
from preset import (
	preset as pre,
	pTypes,
	verbose,
	printv,
	fm,
	fg,
	bg,
	input_times,
	is_connected,
	catchless,
	debugs,
	ferror,
)

# thrid pass imports
if is_connected: # note: discord is a phat import.
	import discord 
	from discord.ext.commands import bot
	from discord.ext import tasks, commands

# Variables
user_joins = {}
# { user id: unix time of join}
user_updates = {
	i: {} for i in range(10)
}
# {
# 	0: {
# 			user id (ends in 0): seconds to add,
# 			another user id (ends in 0): seconds to add,
# 			...
# 		},
# 	1: {
# 			user id (ends in 1): seconds to add,
# 			...
# 		}
# 	...
# }

# Subtract the user input delays if there were any (through test with sys.argv)
# Subtract server ping times
# Format vars
all_size = 0
current_vars = pre.rb(globals(), True).items()
indents = {len(str(i)): len(str(type(j))) for i, j in current_vars}
indents = [max(indents.keys())+2, max(indents.values())+1]
indents.append(str(sum(indents)))

printv(1, "Total import time:", fm[4](str(time.time() - s - input_times)), " seconds"); del input_times, s
printv(2, "(The time delay above is subtracted by the internet test ping times and user input times)")
printv(1, bg.g("   ")+" "+fg.g("Connected")+" to internet and imported discord.py" if is_connected else bg.r("   ")+" "+fg.r("Disconnected")+" from internet")

printv(2,
	"\nPreset variables:\n\n" +
	"\n".join(
[	# Type colour block indicator
	pTypes().btypegen(v, " ", "w") + " " +
		"%{}s %-{}s %s%s\n".format(
			# Indents
			indents[0],
			indents[1] if verbose > 2 else 0,
			("\n"+indents[2]) if verbose > 2 else 0,
		) % (
			# Values
		current :=
			k,
			type(v) if verbose > 2 else pTypes().ftypegen(v, " : "),
			str(all_size := (_:=sys.getsizeof(v))+all_size)[:0] + pre.sizeof_fmt(_),
			(pTypes().ftypegen(v, "\n-> ")+str(v)) if verbose > 2 else "",
		# Loop
	) for k, v in current_vars
]),
	fm[7]("\nNumber of variables:"), str(len(current_vars)),
	fm[7]("\nMemory size:"), pre.sizeof_fmt(all_size), "\n"
)
del current_vars, all_size

"""
	console output structure:

	preset args:
	sys.argv comments
	\n

	total import time
	internet connection?
	\n

	list of preset vars from runtimeVars
	\n

	bot intro / startup comments
"""

if not is_connected:
	sys.exit(1)

### --------------------------------------------------------------------------

class get:
	""" class to organise small functions that return specifics """

	class func: pass

	def token() -> str:
		""" Gets token from token.txt for run() """
		return open("token.txt", "r", encoding="utf8").read().strip()


	def prefix(_bot, message):
		""" sets the bot's prefix """

		prefixes = [
			'..', '<@695805789050241034>', '<@!695805789050241034>'
		] if message.guild else [
			'..', '<@695805789050241034>', '<@!695805789050241034>', '']
		# no prefix needed if not in dm

		return commands.when_mentioned_or(*prefixes)(_bot, message)

	def prefix_filter(message):
		# print(message.content.split())
		return

	remove_commands = ["help"] # default commands to remove

	c = "cogs.{}".format
	init_extensions = list(map(lambda x: "cogs."+x, [
		"levels",
		"misc",
		"help",
		"snipe",
	]))

	cogfiles = [str(i)[:-3] if i != "__pycache__" else "" for i in os.listdir("cogs")]

	top_level_users = set()


# the discord bot client
client = commands.Bot(command_prefix=get.prefix, case_insensitive=True, intents=discord.Intents().all(),
description='''User levels based on time spent in voice channels.''')

get.top_level_users.add(client.owner_id)

## initialising
printv(1, "\ninitialising bot")

# removes commands
if get.remove_commands: printv(2, "\nRemoving commands: ")
for cmd in get.remove_commands:
	client.remove_command(cmd)
	printv(2, "\tRemoved command:", cmd)

# loads extention cogs
if get.init_extensions: printv(2, "\nLoading cogs:")
for ext in get.init_extensions:
	client.load_extension(ext)
	printv(2, "\tLoaded", ext, "cog")



@client.command(name="kill", pass_context=True)
async def kill(ctx):
	""" force stop """
	if ctx.author.id in get.top_level_users:
		await ctx.send("deactivated")
		printv(1, ferror(str("  ") + " Requested stop at", time.ctime()))
		await client.logout()


@client.command(name="reload", aliases=["r"])
async def reload(ctx):
	""" reloads a cog """
	if ctx.author.id in get.top_level_users:
		if len(ctx.message.content.split()) == 2:
			cog = ctx.message.content.split()[1]
			msg = "Reloading cogs."+cog

			if ctx.message.content.split()[1] not in get.cogfiles:
				return await ctx.send("Cog not found")
			try:
				client.reload_extension(name="cogs."+cog)
				printv(pre.cogpr(cog, client, "y")) # output in console
				return await ctx.send(msg)
			except Exception as e:
				return await ctx.send(e)


@client.command(name="load", aliases=["ld"])
async def load(ctx):
	""" loads a cog """

	if ctx.author.id in get.top_level_users:
		if len(ctx.message.content.split()) == 2:
			if ctx.message.content.split()[1] not in get.cogfiles:
				return await ctx.send("Cog not found")
			if catchless:
				client.load_extension(name=f"cogs.{ctx.message.content.split()[1]}")
				await ctx.send(f"Loading cogs.{ctx.message.content.split()[1]}")
			else:
				try:
					client.load_extension("cogs."+ctx.message.content.split()[1])
					get.cogfiles.append(ctx.message.content.split()[1])
					return await ctx.send(f"Loading cogs.{ctx.message.content.split()[1]}")
				except Exception as e:
					return await ctx.send(e)
		else:
			return await ctx.send(f"Available cogs: {', '.join(get.cogfiles)[:-2]}")


get.func.reload = reload
get.func.load = load

# activate bot
printv(2, (
(fg.g("\n\n--! ")+bg.w(" ")+ fm["u"]("  ACTIVATING BOT  ")+bg.w(" ")+fg.g(" !--\n")))
) if verbose >= 2 else printv(1, fg.g("\n --! ACTIVATING BOT !-- \n"))

def main():
	
	# Start bot
	client.run(get.token())

	main()
