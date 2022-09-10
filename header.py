""" Voice Levels header"""
import logging
import logging.handlers
import os
from typing import Union
from collections import OrderedDict
from sys import stdout
from dotenv import load_dotenv

try:
    from psycopg2cffi import compat
    compat.register()
except ImportError:
    pass
finally:
    import psycopg2
    from psycopg2.extensions import connection

import new_db

# from cachetools import cached, cachedmethod, LRUCache, TTLCache, keys

if not os.path.isfile("./.env"):
    with open("./.env", "w", encoding="utf-8") as file:
        file.write("""# Voice Levels .env
# Uncomment (remove hashtag infront of) DATABASE_URL below and paste your own postgresql url (uses ssl connection)
# If you are on Heroku, they set DATABASE_URL for you. No need to Uncomment

# DATABASE_URL=
# BOT_PREFIX=,,
BOT_TOKEN=

# Arbitrary value of 35: 3500m furthest sniper kill distance
BOT_SNIPE_MAX=35
# The interval of each automatic save to database in minutes
BOT_SAVE_TIME=30

# Allows everyone to use the `all` command fully (yes/no)
BOT_GLOBAL_ALL_LEADERBOARD_ACCESS=no

# Print output as well: yes/no
# This must be yes for a Heroku deployment if you want to view logs
BOT_PRINT=yes

# debug, info, warning, error, critical
BOT_LOG_LEVEL=info
DISCORD_LOG_LEVEL=info
# Max size of log files, in Mib
BOT_LOG_FILESIZE=4
# Max log backup files amount
BOT_LOG_BACKUP_COUNT=2

# Follow log in bash using `tail discord.log -f -n lines`
# Follow log in powershell `Get-Content discord.log -Wait -Tail lines`
""")
    print(
        # "If you are using Heroku or railway.app, please set your environment variables\n"
        # "You need BOT_TOKEN and DATABASE_URL / DATABASE_URL_O (for override)\n"
        "If you are using Heroku or railway.app, disregard the following\n"
        ".env was not found, "
        "making .env file now, "
        "please insert the bot token and other information\n"
    )

load_dotenv()

# Stream gets "constipated", this helps unclog logging
# if not os.path.isfile("discord.log"):
#   with open("discord.log", "w"):
#       pass

# if os.path.getsize("discord.log") > 1.8 * 1024 * 1024:
#   os.rename("discord.log", "discord.log.1")
#   for i in range(5, 1, -1):
#       if not os.path.isfile(f"discord.log.{i}"):
#           break
#       os.rename(f"discord.log.{i}", f"discord.log.{i+1}")

#   with open("discord.log", "w"):
#       pass

logging_level = logging.getLevelName(os.getenv("DISCORD_LOG_LEVEL", "INFO").upper())

log = logging.getLogger("vl")

log.setLevel(logging.getLevelName(os.getenv("BOT_LOG_LEVEL", "INFO").upper()))

logging.getLogger("discord.http").setLevel(logging_level)
logging.getLogger("discord").setLevel(logging_level)

handler = logging.handlers.RotatingFileHandler(
    filename="./discord.log",
    encoding="utf-8",
    maxBytes=int(float(os.getenv("BOT_LOG_FILESIZE", "4")) * 1024 * 1024),
    backupCount=2,
)
formatter = logging.Formatter(
    "{asctime} [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{"
)
handler.setFormatter(formatter)
log.addHandler(handler)

if os.getenv("BOT_PRINT", "").lower() == "yes":
    printer = logging.StreamHandler(stdout)
    printer.setFormatter(formatter)
    log.addHandler(printer)

# Activate colour output in terminal in command prompt
if os.name == "nt":
    os.system("color")


class ColourFormat(dict):
    """Class that sets up formatting"""

    _letters = "krgybmcw"
    _num = {
        1: "one",
        2: "two",
        3: "three",
        4: "four",
        5: "five",
        6: "six",
        7: "seven",
        8: "eight",
        9: "nine",
    }

    class Colour:
        """Like a string, but with colour"""
        __slots__ = ("_str", "_int")

        def __init__(self, num: int) -> None:
            self._int = int(num)
            self._str = f"\033[{num}m"

        def __repr__(self) -> str:
            return self._str

        def __str__(self) -> str:
            return self._str

        def __int__(self) -> int:
            return self._int

        def __add__(self, other) -> str:
            return self._str + other

        def __radd__(self, other) -> str:
            return other + self._str

        def __call__(self, string="", after="") -> str:
            return f"{self}{string}{after}\033[0m"

    def __init__(self, offset: int, doc: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for key, value in [
                (self._num.get(key, str(key)), value)
                for key, value in self.copy().items()
                if not str(key).isdigit()
        ]:
            self.__setattr__(key, value)
            self[key] = value

        self.__class__.__doc__ = doc
        if offset:
            for caps in True, False:
                for num, letter in enumerate(
                        list(self._letters.upper() if caps else self._letters)
                ):
                    self[letter] = self.Colour(num + offset + (60 if caps else 0))
                    self.__setattr__(letter, self[letter])

    def __repr__(self) -> str:
        return super().__repr__() + "\033[0m"


fg = ColourFormat(
    30,
    """
Console foreground colouriser
    Usage:
        fg.color("string")
        fg["colour"]("string")
        f"{fg.r}This text is now red"
        fg.R + "This text is bright red"

    k = black
    r = red
    g = green
    y = yellow
    b = blue
    m = magenta
    c = cyan
    w = white

    Capital letter = Lighter colour
""",
)
bg = ColourFormat(
    40,
    """
Console background colouriser
    Usage:
        bg.color("string")
        bg["colour"]("string")
        f"{bg.r}The background of text is now red"
        bg.R + "Background here is bright red"

    k = black
    r = red
    g = green
    y = yellow
    b = blue
    m = magenta
    c = cyan
    w = white

    Capital letter = Lighter colour
""",
)

fm = ColourFormat(
    0,
    """
Console text formatter
    Usage:
        fm[int]("string")
        fm.number("string")
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
""",
    {
        **{i: ColourFormat.Colour(i) for i in range(10)},
        "c": ColourFormat.Colour(0),
        "u": ColourFormat.Colour(4),
        "i": ColourFormat.Colour(8),
        "bg": bg,
        "fg": fg,
    },
)


def cogpr(name: str, bot: object, colour: str = "w") -> str:
    """Format cog start output"""
    log.info("Activated %s %s", fg[colour]+bot.user.name, fg.G(name))  # pylint: disable=no-member


def refresh_conn() -> Union[psycopg2.extensions.connection, None]:
    """Returns a new connection object"""
    log.debug("Refreshing connection to database")
    db_url = os.getenv("DATABASE_URL_O", os.getenv("DATABASE_URL", ""))
    conn = None
    try:
        conn = psycopg2.connect(db_url, sslmode="require")
        conn.set_session(autocommit=True)
    except psycopg2.OperationalError:
        log.error(
            "You do not have Heroku Postgress in Add-ons, "
            "or the environment variable was misconfigured"
        )
    return conn


def get_token(conn: connection) -> str:
    """Returns the bot token from environment variables, and bool for need_setup"""
    if token := os.getenv("BOT_TOKEN"):
        # Init database if doesn't exist
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT FROM
                        information_schema.tables
                    WHERE
                        table_schema LIKE 'public' AND
                        table_type LIKE 'BASE TABLE' AND
                        table_name = 'levels'
                    );
                """
            )
            if not cur.fetchone()[0]:
                cur.execute(new_db.CREATE_VL)
                conn.commit()
    else:
        log.error("NO TOKEN IN ENVIRONMENT VARS!")
        log.error(
            "Heroku:  from dashboard->settings, add the config var BOT_TOKEN\n"
            "railway: from project->worker->variables, add BOT_TOKEN"
        )
        log.error("If you're hosting locally, edit .env and update your BOT_TOKEN")
    return token

# class _prefix_factory:
#   global len_bot_guilds  # rip

#   def __init__(self, bot):
#       self.bot = bot

#   # @cachedmethod(
#   #       cache=LRUCache(maxsize=len(bot.guilds)//1.5),
#   #       key=lambda conn,
#   #       guild.id: keys.hashkey(guild.id)
#   # )
#   @cachedmethod(
#       cache=LRUCache(maxsize=len_bot_guilds//1.5),
#          key=lambda conn,
#          guild.id: keys.hashkey(guild.id)
#   ) # rip
#   def _server_prefix(conn, guild.id: int):
#       with conn.cursor() as cur:
#           cur.execute("SELECT TRIM(prefix) FROM prefixes WHERE id = %s", (str(guild.id),))
#           prefix = cur.fetchone()
#       return ',,' if prefix is None else prefix[0]

# class _prefix_factory_returner:
#   def make_factory(self, bot):
#       self._prefix_factory = _prefix_factory(bot)

# _prefix_factory_returner = _prefix_factory_returner()



class ServerPrefix:
    """Handle getting of server prefixes and its cache"""
    __slots__ = ("cache_size", "cache", "default_prefix")

    def __init__(self):
        self.cache_size = 1000
        self.cache = OrderedDict()
        self.default_prefix = os.getenv("BOT_PREFIX", ",,")  # Hard coded default

    def __call__(self, bot, guild):
        if not guild:
            return ""

        try:
            bot.conn.poll()
            bot.conn.poll()
        except psycopg2.Error as error:
            log.warning("Polling database has returned an error.\n%s", str(error))
            log.info("Attempting to reconnect")
            bot.conn = bot.refresh_conn()
            log.info("Reconnected")

        base = [
            f"<@!{bot.user.id}> ",
            f"<@!{bot.user.id}>",
            f"<@{bot.user.id}> ",
            f"<@{bot.user.id}>",
        ]

        if prefix := self.cache.get(guild.id):
            self.cache.move_to_end(guild.id)
            log.debug("Prefix in cache, using that")
            return [prefix, *base]

        log.debug("Requesting prefix for %s", guild.name)

        with bot.conn.cursor() as cur:
            cur.execute("SELECT prefix FROM prefixes WHERE id = %s", (str(guild.id),))
            prefix = cur.fetchone()

        self.cache[guild.id] = (
            self.default_prefix if prefix is None else prefix[0].lstrip()
        )
        while len(self.cache) > self.cache_size:
            self.cache.popitem(last=False)
        return [self.cache[guild.id], *base]

    def prefix_cache_pop(self, gid: int) -> None:
        """Pops the requested guild id from cache, forcing a prefix refresh next time"""
        self.cache.pop(gid, None)

server_prefix = ServerPrefix()


async def get_prefix(bot, message):
    """Sets the bot's prefix"""


    # if not bot._prefix_factory_init:

    #     global len_bot_guilds  # ripd
    #     len_bot_guilds = len(bot.guilds)  # rip

    #     prefix_factory_returner.make_factory(bot)

    # _server_prefix = _prefix_factory_returner._prefix_factory._server_prefix


    if not bot.prefix_factory_init:
        server_prefix.cache_size = (
            (len(bot.guilds) // 1.25) if len(bot.guilds) > 1000 else len(bot.guilds)
        )
        bot.prefix_factory_init = True

    # No prefix needed if not in dm
    return server_prefix(bot, message.guild)
