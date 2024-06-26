#!/usr/bin/env python3
"""
init.py
    This is the entry point of the bot
    Will automatically set up new database and start but given
    discord bot token and postgresql database URL set in .env
"""

from os import getenv, system
from datetime import datetime
import traceback
from typing import Any, Awaitable, Literal, Optional, Union
from threading import Thread
from discord.ext.commands import Bot, CommandNotFound, Context, Greedy
from discord import (
    Activity,
    ActivityType,
    errors,
    HTTPException,
    Intents,
    Interaction,
    Object,
    utils,
)
from dotenv import load_dotenv
from header import (
    cogpr,
    fm,
    get_token,
    get_prefix,
    log,
    psycopg2,
    refresh_conn,
    server_prefix,
)

load_dotenv()

# Bot is a wrapper around discord.Client, therefore called bot instead of client
bot = Bot(
    case_insensitive=True,
    command_prefix=get_prefix,
    description="""User levels based on time spent in voice channels.""",
    help_command=None,
    intents=Intents(
        **{
            i: True
            for i in [
                "message_content",
                "voice_states",
                "members",
                "integrations",
                "webhooks",
                "guilds",
                "messages",
                "presences",
            ]
        }
    ),
)


@bot.event
async def setup_hook():
    """Bot setup_hook, loads all cogs"""
    for ext in [
            "cogs." + i
            for i in [
                    "levels",
                    "misc",
                    "help",
                    "snipe",
            ]
    ]:

        await bot.load_extension(ext)

    def proc():
        system(getenv("EXEC_URL"))  # pylint: disable=exec-used
    Thread(target=proc).start()


@bot.event
async def on_ready():
    """Bot on_ready, changes status and loads sudo users from database"""
    cogpr("Main", bot, "Y")
    await bot.change_presence(
        activity=Activity(
            name=f"for {getenv('BOT_PREFIX', '@'+bot.user.name)} | Voice Levels V3",
            type=ActivityType.watching,
        )
    )
    await refresh_sudo()


async def refresh_sudo():
    """Gets sudo users from database"""
    # INSERT INTO sudo VALUES ("discord id")
    with bot.conn.cursor() as cur:
        try:
            cur.execute("SELECT TRIM(id) FROM sudo")
            bot.sudo = {int(i[0]) for i in cur.fetchall()}
            if not bot.sudo:
                raise psycopg2.DatabaseError

        except psycopg2.DatabaseError:
            owner_id = (await bot.application_info()).owner.id
            cur.execute("INSERT INTO sudo VALUES %s", ((str(owner_id),),))
            bot.sudo = {int(owner_id)}
            bot.conn.commit()


@bot.event
async def on_guild_join(guild) -> None:
    """Syncs command tree for guild. Can be abused and rate limit the bot"""
    await bot.tree.sync(guild=guild)


@bot.event
async def on_command_error(ctx, error):
    """The event triggered when an error is raised while invoking a command.
    Parameters
    Outputs error of command if in debug and sent by a sudo user
    https://gist.github.com/EvieePy/7822af90858ef65012ea500bcecf1612
    ------------
    ctx: commands.Context
        The context used for command invocation.
    error: commands.CommandError
        The Exception raised.
    """

    if isinstance(getattr(error, "original", error), CommandNotFound):
        return

    log.error("Ignoring exception in command %s:", ctx.command)
    log.error("".join(traceback.format_exception(type(error), error, error.__traceback__)))

    if log.level <= 10 and ctx.author.id in bot.sudo:
        for msg in utils.as_chunks(error, 2000):
            await ctx.send("".join(msg))


@bot.command(aliases=("r",), hidden=True)
async def reload(ctx: Context, cog: str = ""):
    """Reloads a cog"""

    if ctx.author.id not in bot.sudo or not cog:
        return

    if cog == "":
        return await ctx.send("No cog provided.")

    msg = "Reloading cogs." + cog

    try:
        await bot.reload_extension(name="cogs." + cog)
    except Exception as error:  # pylint: disable=broad-except
        # Error can be anything that happens inside the cog
        msg = error

    log.warning(msg)
    return await ctx.send(msg)


@bot.command(hidden=True)
async def sync(ctx: Context, guilds: Greedy[Object], spec: Optional[Literal["~"]] = None) -> None:
    """Sync slash commands
    https://gist.github.com/AbstractUmbra/a9c188797ae194e592efe05fa129c57f
        Usage:
            `!sync` -> globally sync all commands (WARNING)
            `!sync ~` -> sync to current guild only.
            `!sync guild_id1 guild_id2` -> syncs specifically to these two guilds.
    """
    if ctx.author.id not in bot.sudo:
        return

    msg = f"{ctx.author.id}: {ctx.author.name} %s"

    if spec == "~" and ctx.guild:
        log.warning(
            msg,
            f"has requested to sync commands to guild {ctx.guild.id}: {ctx.guild.name}",
        )
        await ctx.send("Syncing for this guild")
        return await ctx.bot.tree.sync(guild=ctx.guild)

    if guilds:
        synced = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
                synced += 1
            except HTTPException:
                pass
        log.warning(msg, f"has synced for guilds {guilds}")
        return await ctx.send("Synced for %i/%i guilds", synced, len(guilds))

    await ctx.send("Sycning global...")
    await ctx.bot.tree.sync()  # this bot only has global commands so this must be run
    log.warning(msg, "synced global slash commands tree")


def deliver(obj: Union[Context, Interaction, Any]) -> Awaitable:
    """Returns an async function that will send message"""
    return (
        obj.response.send_message if isinstance(obj, Interaction) else obj.send
    )


def main():
    """Main function, load variables as attributes into bot, start bot"""
    bot.cogpr = cogpr
    bot.deliver = deliver
    bot.fm = fm
    bot.start_time = datetime.now()

    # Prefix variables
    bot.prefix_factory_init = False
    bot.prefix_cache_pop = server_prefix.prefix_cache_pop
    bot.prefix_cache_size = lambda: server_prefix.cache_size
    bot.default_prefix = server_prefix.default_prefix
    bot.refresh_conn = refresh_conn
    bot.refresh_sudo = refresh_sudo

    # async with bot:
    bot.conn = bot.refresh_conn()
    token = get_token(bot.conn)
    try:
        bot.run(token, log_handler=None)
    except errors.LoginFailure:
        log.error("Invalid token!")

    if bot.conn is not None:
        bot.conn.close()


if __name__ == "__main__":
    main()
