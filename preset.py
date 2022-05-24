# everything here is over engineered, and completely unnecessary to the normal functioning of the system
# TODO: delete everything here

if __name__ == "__main__":
	exit(1)
	# exits if was not imported

from __main__ import *

""" --------------------------------------------------------------------------
	#############################
	### colours.py moved here ###
	#############################
"""
###

### --------------------------------------------------------------------------

import os

### --------------------------------------------------------------------------

global letters
letters = ["k", "r", "g", "y", "b", "m", "c", "w", "K", "R", "G", "Y", "B", "M", "C", "W"]
class fg:
	"""
		Console foreground colouriser
		Usage:
			fg.color("string")
		k = black
		r = red
		g = green
		y = yellow
		b = blue
		m = magenta
		c = cyan
		w = white

			fg.d["colour"]("string")


		capital = bold (not working)
	"""
	d = {}
	for num, letter in enumerate(letters[:8]):
		exec(letter+"= '\033["+str(num+30)+"m{}\033[0m'.format")
		d[letter] = "\033[{}m{}\033[0m".format(num+30, "{}").format
	for num, letter in enumerate(letters[8:]):
		exec(letter+"= '\033["+str(num+30)+"m{}\033[0m'.format")
		d[letter] = "\033[{}m;1m{}\033[0m".format(num+38, "{}").format

class bg:
	"""
	Console background colouriser
		Usage:
			bg.color("string")
		k = black
		r = red
		g = green
		y = yellow
		b = blue
		m = magenta
		c = cyan
		w = white

			bg.d["colour"]("string")


		capital = bold (not working)
	"""
	d = {}
	for num, letter in enumerate(letters):
		exec(letter+"= '\033["+str(num+40)+"m{}\033[0m'.format")
		d[letter] = "\033[{}m{}\033[0m".format(num+40, "{}").format

"""
	Console text formatter
		Usage:
			fm[int]("string")
		0 = reset
		1 = bold
		2 = darken
		3 = italic
		4 = underlined
		5 = blinking
		6 = un-inverse colour
		7 = inverse colour
		8 = hide
		9 = crossthrough
"""
fm = {
	**{i : "\033[{}m{{}}\033[0m".format(i).format for i in range(10)},
	"c":"\033[0m{}\033[0m".format,
	"u":"\033[4m{}\033[0m".format,
	"i":"\033[8m{}\033[0m".format
}

def printr(*args):
	print(*args)
	return [*args]

# format an error message
def ferror(*text: str):
	# bold, background red, foreground black
	return printr(fm[1](bg.R(">     :")+" "+str(*text)))


###
# End of colours.py
### --------------------------------------------------------------------------
##############################################################################

# importing
import sys, socket

# globalises variables
# global catchless, debugs, verbose, input_times
verbose = 1 # !!! 0 = silent, 1 = default, 2 = verbose, 3 = debug
catchless = False
debugs = []
from_console = len(sys.argv) != 1

# non global variables
manual_dc = False

### --------------------------------------------------------------------------

# preprocess verbosity
silenced = 1
# todo matching algorithm

# print(any([i in ["-s", "-silent", "-silence"] for i in sys.argv]))
if any([i in ["-s", "-silent", "-silence"] for i in sys.argv]):
	# for arg in sys.argv[sys.argv.index(arg) + 1]: # !!! @todo OPTIMISE - get rightmost "-silent" arg and start from there instead
	# for arg in sys.argv[::-1][:sys.argv[::-1].index(arg)][::-1]:
	for arg in sys.argv:
		if arg in ["-q", "-quiet"]:
			silenced -= 1
		elif arg in ["-v", "-verbose"]:
			silenced += 1
		elif arg in ["-s", "-silent", "-silence"]:
			silenced = 0

silenced = False if silenced else True

# preset arguments header
if (
	sys.argv.count("-q") + sys.argv.count("-quiet") <
	sys.argv.count("-v") + sys.argv.count("-verbose") + 1
) and len(sys.argv) != 1 and not silenced: print(fg.g("\npreset arguments:\n"))


class ArgManage():

	def __init__(self):
		self.argProc(sys.argv[1:]) # firstpass arg process with system commands

	def argUpdate(self, arg: str) -> (str, str, bool):
		"""
			@todo [ optimise ] switch/case or if/else
			
			Returns:
				information of the passed argument

				tuple(
					str (low verbosity),
					str (high verbosity),
					bool (spec)
				)

		"""

		global catchless, verbose

		if arg in ["v", "verbose"]:
			verbose += 1 if verbose < 3 else 0 # adds 1 level to verbosity if under 2
			return "Verbose +", f"Verbosity increased to {verbose}", False
		elif arg in ["q", "quiet"]:
			verbose -= 1 if verbose > 0 else 0 # lowers 1 level of verbosity if over 0
			return "Verbose -", f"Verbosity decreased to {verbose}", False
		elif arg in ["s", "silent", "silence"]:
			verbose = 0
			return "", "", False
		elif arg == "spec":
			return "Entered special debug outputs:", "Entered special debug outputs:", True
		elif arg in ["o", "offline"]:
			global manual_dc
			manual_dc = True
			return "Offline mode", "Offline mode on", False
		elif arg in ["c", "catch", "catchless"]:
			catchless = not catchless
			return "Toggled catches", f"Toggled catches: {catchless}", False
		elif arg == "clear":
			# os.system("cls")
			# return "","",False 
			return "Cleared text", "Cleared text", False

		return f"Invalid argument: {arg}", f"Invalid argument: {arg}", False

	def argProc(self, arg_list: list) -> None:
		# processing verbose
		spec = False # spec = False: process normal sysargs -cmd, spec = True: get value of next sys.arg
		for arg in enumerate(arg_list): # the argv[1:] separates the cmd directory string
			# @todo iter() object for manipulation

			current_iter, arg = arg # seperate (iter, values)

			if not arg: continue # skip empty commands

			if spec:

				# converts shorthand numbers to words
				enum = {
					"levels": 1 
				}

				# not readable for noobs...
				# debugs.append(enum[arg] if arg in enum.keys() else arg if arg in enum.values() else "")
				if arg in enum.keys(): # [ tested ] arg.isnumenric() - IndexError if not match in enum[arg]
					debugs.append(enum[arg])
				elif arg in [str(i) for i in enum.values()]:
					debugs.append(arg)
				else:
					if not silenced: print(" "*5+"--! Invalid debug type passed:", arg)
					self.argUpdate(arg[1:])

					spec = False
					continue

				if not silenced: print(" "*5+debugs[-1])

				spec = False

				# appends strings of IDs of debug locations
				continue


			if arg[0] in ["-", "/"]: # @todo [ optimise ] matching of "-" and "/"

				arg = spec if type(spec) == str else arg[1:]
				spec = False # setting up specific debug printing options

				tup_messages = self.argUpdate(arg)
				if verbose and not silenced: print((_ := "cmd #"+str(current_iter+1)) + " "*(10 - len(_)) + tup_messages[1] if verbose > 2 else " "*10+tup_messages[0])

				if tup_messages[2]: spec = True
			else:
				if verbose and not silenced: print(f"Invalid argument: {arg}" if verbose > 2 else f"Invalid argument: {arg}")

		if spec and verbose and not silenced: print(" "*5+"Did not enter valid special debug value, disregarded")

		return

args = ArgManage()
input_times = []


### --------------------------------------------------------------------------


class pTypes():
	"""
	Class:
		Preset special types
	"""
	def __init__(self):
		#setup
		def func(): yield ""
		class C(): 
			def m(self): ...

		self.function = type(func)
		self.generator = type(func())
		self.module = type(sys)
		self.method = type(C().m)

		del func, C

		# types dictionary
		types = {
			"bool": bool,
			"bytes": bytes,
			"bytearray": bytearray,
			"complex": complex,
			"dict": dict,
			"Ellipsis": ...,
			"float": float,
			"frozenset": frozenset,
			"function": self.function,
			"generator": self.generator,
			"int": int,
			"memoryview": memoryview,
			"method": self.method,
			"module": self.module,
			"None": type(None),
			"object": object,
			"range": type(range(0)),
			"set": set,
			"string": str,
			"tuple": tuple,
			"type": type(type),
		}

		typecol = {
			str: "g",
			int: "b",
			float: "b",
			bool: "y",
			self.function: "m",
			list: "c",
			tuple: "c",
			set: "c",
			dict: "c"
		}
		self.types = types
		self.typecol = typecol

	def btypegen(self, var, text: str, else_effect = False) -> str:
		# Colours the background to match the type of the variable
		return bg.d[self.typecol[type(var)]](str(text)) if type(var) in [str, bool, float, int, tuple, set, list, dict, self.function] else bg.d[else_effect](str(text)) if else_effect else str(text)

	def ftypegen(self, var, text: str, else_effect = False) -> str:
		# Colours the foreground to match the type of the variable
		return fg.d[self.typecol[type(var)]](str(text)) if type(var) in [str, bool, float, int, tuple, set, list, dict, self.function] else fg.d[else_effect](str(text)) if else_effect else str(text)



class Preset:
	"""
	@todo docstring
	"""

	def __init__(self):
		self.ATL = pTypes()

	def myVar(self, val) -> dict:
		# sets the class scope dict_myVars value and returns it
		self.dict_myVars = val
		return val

	def cogpr(self, name: str, client: object, colour: str="c") -> str:
		return fg.d[colour](f"\n{client.user.name} ")+name+fg.d[colour](" Activated")+f"\n{time.ctime()}"


	def printd(self, level, *args, **kwargs) -> None:
		self.printv(1, *args)
		return
		print("new printd:------------------------------\n"
			"args:" + "".join(["\n"+str(i+1) + " " + str(args[i]) for i in range(len(args))]),
			"\nkwargs:\n"+ "\n".join([f"{k} -> {v}" for k, v in kwargs.items()])
		)
		return

	def printv(self, level, *args) -> bool:
		"""
			print function used for this project: print(@verbosity>?)
			returns: True if successful print
		"""

		if type(level) == int:
			# prints if describled verbose level is acceptable
			if level <= verbose and level != 0:

				out = args if verbose != 3 else (
					(_ := datetime.datetime.now().strftime("%d/%m, %X").strip()),
					(" "*(20-len(_))), " ".join(str(i) for i in args)
				)

				print(*out)
				return True
		elif verbose: # prints all if not silent mode
				print(str(level), str(*args))
				return True
		return False

	def newVerbose(level: int) -> None:
		# Depricated: use argUpdate()
		if 0 <= level < 3:
			global verbose
			verbose = level
		return
	
	def getCurrentVars(self, names: set = dir(), dict_loc_glob: dict = globals()) -> dict: # stoopid
		# returns all current global variable names and values
		# Params:
		#	pass in dir() and globals()

		dict_current_vars = {}
		for i in set(names) - set(dir(__builtins__)): # Remove builtins
			if i in [*dict_loc_glob]: # usually True
				if type(dict_loc_glob[i]) not in [self.ATL.generator, self.ATL.module]:
					if i not in ["__builtins__", "__loader__", "__file__", "__cached__", "__package__", "__spec__", "__name__", "__annotations__"]:
						dict_current_vars[i] = dict_loc_glob[i]

				# print(("variable: ", i,"->",dict_current_vars[i]) if i in dict_current_vars else ("not in dict_current_vars:",i))
			else:
				pass
				print(fg.r(i), "not in local global vars")
		dict_sorted_vars = {}
		for k, v in sorted(dict_current_vars.items()):
			dict_sorted_vars[k] = v

		return dict_sorted_vars

	def rb(self, *args: dict, sort: bool=False) -> dict: # stoopid, but better...
		# remove builtins from dict
		# feed me locals or globals, or both? or even more???

		# fix
		if type(sort) != dict:
			args = list(args)
			del args[-1]
		else:
			sort = False

		final = {}
		for dictv in args:
			if type(dictv) == dict:
				for var in set(dictv) - set(dir(__builtins__) + ["__builtins__", "__loader__", "__file__", "__cached__", "__package__", "__spec__", "__name__", "__annotations__"]):
					final[var] = dictv[var]
			else:
				raise TypeError(f"""Wrong type passed, recieved: {dictv} {pTypes().ftypegen(dictv, "->")} {type(dictv)}""")
				
		return {k: final[k] for k in sorted(final)} if sort else final # {var: val for var, val in vars.items()}

	def sizeof_fmt(self, num, suffix: str="B"):
		""" by Fred Cirera,  https://stackoverflow.com/a/1094933/1870254, modified"""
		for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
			if abs(num) < 1024.0:
				return "%3.1f %s%s" % (num, unit, suffix)
			num /= 1024.0
		return "%.1f %s%s" % (num, "Yi", suffix)

# finishes globalising variables after class definitions
preset = pre = Preset()
types = pTypes().types

## ----------------
# declaring variables that take time to declare
input_times.append(time.time())
# import subprocess
# is_connected = ("Reply from 1.1.1.1" in subprocess.run(["ping","1.1.1.1","-w","1","-n","1","-l","0"], shell=True, capture_output=True).stdout.decode()) if not manual_dc else False
is_connected = "DYNO" in os.environ # For Heroku
# only checks if connected, doesn't check if connection does not work.
input_times[-1] = time.time() - input_times[-1]
## ----------------

# redefine in file scope
printv = pre.printv

# deletes

del silenced

# finalising all delay times
input_times = sum(input_times)
