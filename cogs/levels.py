"""levels cog handles commands related to the main levelling system"""
import asyncio
from collections import defaultdict
from dataclasses import dataclass
import datetime
import json
import logging
from os import getenv
import time
from typing import Any, Optional, Tuple
from math import modf
import re
import psycopg2
import discord
from discord.ext import tasks, commands
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("vl")
try:
    INTERVAL = float(getenv("BOT_SAVE_TIME", "30.0"))
except ValueError:
    INTERVAL = 30.0
GLOBAL_ALL_ACCESS = getenv("BOT_GLOBAL_ALL_LEADERBOARD_ACCESS") == "yes"


class DefaultDict(defaultdict):
    """Cleaner representation"""
    def __repr__(self):
        return dict(self).__repr__()
    def __str__(self):
        return self.__repr__()


class Timer():
    """Quick timer class for debugging"""
    __slots__ = "start_time", "end", "stop"

    def __init__(self):
        self.start()
        self.end = self.elapsed
        self.stop = self.elapsed

    def start(self):
        """Starts timer"""
        self.start_time = time.time_ns()

    def elapsed(self):
        """Returns time since object creation or timer start"""
        return (time.time_ns() - self.start_time)/1_000_000_000


def get_level_f(seconds: int) -> (int, str):
    """Function gets the level as (level: int, percentage to next level: str)"""
    decimal, integer = modf((0.75 * ((seconds / 360) ** 0.5) + 0.05 * seconds / 360) / 4)
    return int(integer), decimal


def get_level(seconds: int) -> int:
    """Function gets level as int"""
    return get_level_f(seconds)[0]


def to2(discord_id: int) -> str:
    """Returns the right two digits of the input number"""
    return str(discord_id)[-2:]


class Levels(commands.Cog):
    """Main cog that handles detecting, processing and displaying levels"""

    def __init__(self, bot):
        # Bot initialisation
        self.bot = bot

        # self.lock = asyncio.Lock()

        # List of users who recently disconnected
        self.user_actions = set()  # Any joins / leaves, no remove on leave
        self.user_joins = DefaultDict(lambda: int(time.time()))
        self.user_updates = {str(i).zfill(2): DefaultDict(lambda: 0) for i in range(100)}
        # '00': {}, '01': {}, '02': {}, ... , '97': {}, '98': {}, 99': {}

        @dataclass
        class Mimic:
            """Proxy class, usually to manipulate bot.deliver

            By having a method called `send` and not being an instance of discord.Interaction
            bot.deliver will return the send attribute.
            """
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    self.__setattr__(key, value)

        self.mimic = Mimic

        self.deliver = bot.deliver
        self.startup = True
        self.updater.start()  # pylint: disable=no-member

    @commands.command(hidden=True)
    async def var(self, ctx, var):
        """Returns an attribute of the cog for debugging

        Usage: `[prefix]var user_updates` returns self.user_updates
        """
        # This is all very dangerous
        if log.level > 10:
            return
        try:
            if ctx.author.id not in self.bot.sudo:
                return
        except BaseException:  # pylint: disable=broad-except
            return
        if hasattr(self, var):
            await ctx.send(getattr(self, var))

    async def disconnect_all(self):
        """Force write in by simulating everyone disconnect"""
        log.debug("Disconnecting all")
        for uid in self.user_actions.copy():
            log.debug("%i --> None", uid)
            self._on_voice_state_update(
                self.mimic(id=uid, name="mimic"),
                self.mimic(channel=1),
                self.mimic(channel=None),
            )
        log.debug("Disconnecting all finished")

    async def cog_unload(self):
        """Final data upload"""
        log.warning("Levels cog was unloaded, attempting to write_in_data() ---")
        await self.disconnect_all()
        self.write_in_data()
        log.warning("Reached end of levels unload!")

    @commands.command()
    async def update(self, ctx):
        """Manually run through all channels and update into data.json"""
        if ctx.author.id in self.bot.sudo:
            log.warning("\t--- %i Called an update ---", ctx.author.id)
            await self.disconnect_all()
            self._update()
            log.warning("Successfully executed disconnect_all and _update")
            return await ctx.send("Updated")

    @tasks.loop(minutes=INTERVAL, reconnect=True)
    async def updater(self):
        """Submits recorded seconds for each user into database every 30 mins"""
        if self.startup:
            sleep = 0  # Wait for sudo to load in init.py
            while not hasattr(self.bot, "sudo"):
                await asyncio.sleep(sleep := sleep + 10)
            # Reset when activated, prevents faulty join times due to downtime
            self._update()
            self.startup = False
        else:
            # async with self.lock:
            self.write_in_data()

    def _update(self):
        # async with self.lock(): used to be here
        # Hopefully no catastrophic errors occur while it's gone.
        self.write_in_data()  # Update everyone who is currently in

        # Rejoin everyone
        for uid in (
                uid for ids in (
                    channel.voice_states for channel in (
                        channel for channels in (
                            server.channels for server in self.bot.guilds
                        ) for channel in channels
                    ) if hasattr(channel, "voice_states")
                ) for uid in ids
        ):
            msg = f"\tfound {uid}%s"
            if uid not in self.user_actions:
                self._on_voice_state_update(
                    self.mimic(id=uid, name="mimic"),
                    self.mimic(channel=None),
                    self.mimic(channel=1),
                )
                log.debug(msg, "")
            else:
                log.debug(msg, ", but was already in user actions")

    def write_in_data(self) -> None:
        """This function writes the data into the database

        Don't even try to sql inject only with discord user id and time in seconds
           Manual import (Sometimes gets stuck if your self.bot is running.)
           >>> import psycopg2, json
           >>> var = {"id": time, "id": time ... }
           >>> results = [(str(i).zfill(2), {},) for i in range(100)]
           >>> for k, v in var.items(): results[int(str(k)[-2:])][1][k] = v
           >>> conn = psycopg2.connect( 'YOUR_DATABASE_URL', sslmode='require')
           >>> cur = conn.cursor()
           >>> cur.execute('''
                UPDATE levels SET
                    json_contents = c.json_contents
                FROM (values
                    %s
                ) AS c(right_two, json_contents)
                WHERE levels.right_two::bpchar = c.right_two::bpchar;
                ''' % ", ".join(
                    [f"('{r_t}'::bpchar, '{json.dumps(v)}'::json)" for r_t, v in results]
                ))
           >>> conn.commit()
        """
        # Get data
        try:
            cur = self.bot.conn.cursor()
        except psycopg2.InterfaceError:
            self.bot.conn = self.bot.refresh_conn()
            cur = self.bot.conn.cursor()

        occupied = tuple(key for key, value in self.user_updates.items() if value)
        log.debug("NOW WRITING IN DATA FOR %s", str(self.user_updates))
        if len(occupied) == 0:
            log.debug("NOT OCCUPIED")
            cur.close()
            return

        cur.execute(
            "SELECT right_two, json_contents FROM levels WHERE right_two IN %s",
            (occupied,),
        )
        results = cur.fetchall()  # List[Tuple(last_two: str, times: dict),]
        for index, value in enumerate(results):
            json_contents = DefaultDict(lambda: 0, value[1])
            for uid, utime in self.user_updates[value[0]].items():
                json_contents[str(uid)] += utime
            results[index] = (value[0], dict(json_contents))

        log.debug("Results = %s", str(results))

        # This doesn't work under python -OO, as __doc__s are removed
        cur.execute(
            self.write_in_data.__doc__.split("'''")[1]
            % ", ".join(
                [f"('{r_t}'::bpchar, '{json.dumps(v)}'::json)" for r_t, v in results]
            )
        )
        # psycopg2.extras.Json(v) gets inferred as type records
        # , [tuple( (r_t, psycopg2.extras.Json(v)) for r_t, v in results)]

        # )
        # { ", ".join(["('"+r_t+"'::bpchar, '"+json.dumps(v)+"'::json)" for r_t, v in results]) }

        cur.close()

        self.user_updates = {str(i).zfill(2): DefaultDict(lambda: 0) for i in range(100)}

        for uid in self.user_actions.difference(self.user_joins).copy():
            self.user_actions.discard(uid)

        self.bot.conn.commit()
        self.bot.update_time = datetime.datetime.now()

    @commands.Cog.listener()
    async def on_ready(self):
        """Log cog activation"""
        self.bot.cogpr("Levels", self.bot)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Voice Updates

            1. Check if it was a disconnect/ reconnect/ move
            2. Check if they have a previous join time ( make one if not )
            3. Check if they have an update time ( make on if not )
            4. Add their time.now - time.previous join to their update
            5. Delete their join time if their action was leave ( after.channel == None )
            6. Update their join time to current time
        """
        self._on_voice_state_update(member, before, after)

    def _on_voice_state_update(self, member, before, after):
        log.debug("%s --> %s", before.channel, after.channel)
        if before.channel == after.channel or (
                member.id not in self.user_joins and after.channel is None
        ):
            # Name of the channel unchanged: not a disconnect or move
            # Disconnected while no record of inital connection
            log.debug("No channel diff or was not found in user joins")
            return

        self.user_actions.add(member.id)

        # Add if not exist and return as it was only a join
        if member.id not in self.user_joins:
            log.debug("^ this was just a join, now in user_joins")
            self.user_joins[member.id] = int(time.time())
            return

        # Add duration
        duration = int(time.time()) - self.user_joins[member.id]
        self.user_updates[to2(member.id)][member.id] += duration

        # Removes from needing updates
        if after.channel is None:
            del self.user_joins[member.id]
        else:
            # If it was not a leave: refresh the count
            self.user_joins[member.id] = int(time.time())

        log.debug("^ Added duration of %i seconds", duration)

    @commands.hybrid_command(name="total", description="Shows total time in seconds")
    async def total(self, ctx: commands.Context, user: Optional[discord.User] = None):
        """Returns the user's time in seconds"""
        await self._total(ctx, user)

    @commands.hybrid_command(name="seconds", description="Shows total time in seconds")
    async def seconds(self, ctx: commands.Context, user: Optional[discord.User] = None):
        """Returns the user's time in seconds"""
        await self._total(ctx, user)

    async def _total(self, ctx, user):
        """Gets total time of user in seconds"""
        lookup = ctx.author if user is None else user

        # Opens the corresponding file
        with self.bot.conn.cursor() as cur:
            cur.execute(
                "SELECT json_contents FROM levels WHERE right_two = %s",
                (to2(lookup.id),),
            )
            user_times = cur.fetchone()[0]
            # Wow it already converted from json to py objects!

        if str(lookup.id) not in user_times:
            # Record does not exist
            return await self.deliver(ctx)(f"<@!{lookup.id}> has no time saved yet.")

        # Gets live info and the user times
        current_user_time = user_times[str(lookup.id)] + self._add_current_time(lookup.id)

        return await self.deliver(ctx)(
            f"{lookup.name} has spent {current_user_time} seconds in voice channels"
        )

    @commands.hybrid_command(
        name="level",
        description="Gets the time spent in voice channel of a specified user",
    )
    async def level(self, ctx: commands.Context, user: Optional[str] = None):
        """Returns human ctx text"""
        await self._level(ctx, user)

    @commands.hybrid_command(
        name="info",
        description="Gets the time spent in voice channel of a specified user",
    )
    async def info(self, ctx: commands.Context, user: Optional[str] = None):
        """Alias for level"""
        await self._level(ctx, user)

    @commands.hybrid_command(
        name="time",
        description="Gets the time spent in voice channel of a specified user",
    )
    async def time(self, ctx: commands.Context, user: Optional[str] = None):
        """Alias for level"""
        await self._level(ctx, user)

    async def _level(self, ctx, user):
        """Returns the level of the user along with human readable time"""
        lookup = ctx.author if ctx.interaction is None else ctx.interaction.user
        if user is not None:
            if len(ctx.message.mentions) > 0:
                lookup = ctx.message.mentions[0]
            elif user.isdigit():
                lookup = discord.Object(id=int(user))
                lookup.name = user
            else:
                def fmt(string):
                    return re.findall(r"(?<=[<@#!:a-z])(\d+)", string)
                if found_id := fmt(ctx.message.content):
                    pass
                elif found_id := fmt(user):
                    pass
                else:
                    found_id = False

                if found_id:
                    lookup = discord.Object(id=found_id[0])
                    lookup.name = user
                else:
                    return await self.deliver(ctx)("Invalid input")

        # Opens the corresponding part
        with self.bot.conn.cursor() as cur:
            cur.execute(
                "SELECT json_contents FROM levels WHERE right_two = %s",
                (to2(lookup.id),),
            )
            user_times = cur.fetchone()[
                0
            ]  # wow it already converted from json to py objects!

        if str(lookup.id) not in user_times:
            # Record does not exist
            return await self.deliver(ctx)(f"{lookup.name} has no time saved yet.")

        # Gets live info and the user times
        total_seconds = user_times[str(lookup.id)] + self._add_current_time(lookup.id)

        cut = datetime.timedelta(seconds=total_seconds)
        hours, minutes, seconds = str(cut).split()[-1].split(":")

        minutes = minutes[-1] if minutes.startswith("0") else minutes
        seconds = seconds[-1] if seconds.startswith("0") else seconds
        total_seconds = get_level(total_seconds)

        return await self.deliver(ctx)(
            f"""{lookup.name} has spent {cut.days} days, {hours} hours, {minutes
            } minutes and {seconds} seconds on call: level {total_seconds}"""
        )

    @commands.hybrid_command(name="all", description="Leaderboard for this server")
    async def all(self, ctx: commands.Context, page=None):
        """Acts as a normal leaderboard command

        Can get users of all servers if requested by a sudo user
        Sudo users can also add raw to the page to send
        the message with raw formatting (without ```ansi)
            [prefix]all 2raw
                gives page 2, raw.
        """
        def returns(page):
            if not page.isdigit() and page.endswith("raw"):
                if len(page) == 3:
                    return 1, True
                return int(re.sub(r"\D", "", page)), True
            if page.isdigit():
                return int(page), False
            return None

        ret = returns(page) if page else None
        page, raw = (1, False) if ret is None else ret

        log.debug("All command was called")
        total_time = Timer()

        if GLOBAL_ALL_ACCESS or ctx.author.id in self.bot.sudo:
            async def process(ctx, page):
                sql_time = Timer()

                with self.bot.conn.cursor() as cur:
                    cur.execute("SELECT json_contents FROM levels")
                    results = cur.fetchall()
                log.debug("sql_time: %f", sql_time.stop())
                organise_time = Timer()
                large_dict = {
                    k: v
                    for d in [i[0] for i in results]
                    for k, v in d.items()
                }.items()

                total_pages = len(large_dict) // 20 + 1

                if page > total_pages:
                    return None, await self.deliver(ctx)(
                        f"Nothing on page {page}. Total {total_pages} pages"
                    )

                ret = (
                    {
                        int(i): j
                        for i, j in sorted(
                            large_dict, key=lambda item: item[1], reverse=True
                        )
                    },
                    {
                        member.id: member.name
                        for server in self.bot.guilds
                        for member in server.members
                    },
                )
                log.debug("organise_time: %f", organise_time.stop())
                return self._format_top(
                    ctx, ret, page, "from users of *all* servers"
                ), True
            predeliver_time = Timer()
            formatted, _, ctx = await self.predeliver(
                ctx,
                ("Loading leaderboard...", "Took too long loading leaderboard"),
                process,
                page,
            )
            log.debug("predeliver_time: %f", predeliver_time.stop())
            if not formatted:
                return None

            if raw:
                formatted = re.sub(r"```", "\\`\\`\\`", formatted).replace(">>>", "", 1)

            await self.deliver(ctx)(
                content=formatted
            )
            log.debug("total time: %f", total_time.stop())
            return None

        await self._top(ctx, page)

    @commands.hybrid_command(name="top", description="Leaderboard for this server")
    async def top(self, ctx: commands.Context, page: Optional[int] = 1):
        """Leaderboard of the server's times"""
        await self._top(ctx, page)

    @commands.hybrid_command(
        name="leaderboard", description="Leaderboard for this server"
    )
    async def leaderboard(self, ctx: commands.Context, page: Optional[int] = 1):
        """Alias for top"""
        await self._top(ctx, page)

    async def _top(self, ctx, page):

        if not isinstance(page, int) and not page.isdigit:
            page = 1

        if ctx.guild is None:
            ctx.guild = discord.Guild
            ctx.guild.members = [ctx.author, self.bot.user]
            fmt = "between us"
        else:
            fmt = "from users of this server"

        async def process(ctx, page, fmt):
            with self.bot.conn.cursor() as cur:
                cur.execute(
                    "SELECT json_contents FROM levels WHERE right_two IN %s",
                    (tuple(set(to2(i.id) for i in ctx.guild.members)),),
                )
                large_dict = {
                    k: v for d in [i[0] for i in cur.fetchall()] for k, v in d.items()
                }.items()

            list_of_ids = [i.id for i in ctx.guild.members]
            sorted_d = {
                int(k): v
                for k, v in sorted(large_dict, key=lambda item: item[1], reverse=True)
                if int(k) in list_of_ids
            }
            total_pages = len(sorted_d) // 20 + 1

            if page > total_pages:
                return None, await self.deliver(ctx)(
                    f"Nothing on page {page}. Total {total_pages} pages"
                )

            formatted = self._format_top(
                ctx,
                (sorted_d, {i.id: i.display_name for i in ctx.guild.members}),
                page,
                fmt
            )
            return formatted, True

        formatted, _, ctx = await self.predeliver(
            ctx,
            ("Loading leaderboard...", "Took too long loading leaderboard"),
            process,
            page,
            fmt
        )
        if not formatted:
            return

        return await self.deliver(ctx)(
            content=formatted
        )

    async def predeliver(
            self, ctx_main, reply_msg: Tuple[str, str], process, *args
    ) -> (Any, commands.Context):
        """Helper functions for leaderboard

        Delivers a pending message if main content takes too long to process
        then edits original message to loaded content
        """
        async with ctx_main.channel.typing():
            running_tasks = set()

            process = asyncio.create_task(process(ctx_main, *args))
            running_tasks.add(process)
            process.add_done_callback(running_tasks.discard)

            # Get data within 2 seconds (Interaction TTL is 3 seconds)
            done, _ = await asyncio.wait({process}, timeout=2)

            if done:
                return *tuple(done.pop().result()), ctx_main

            need_edit = await self.deliver(ctx_main)(reply_msg[0])
            await ctx_main.channel.typing()
            ctx_reply = self.mimic(
                author=ctx_main.author,
                guild=ctx_main.guild,
                send=need_edit.edit
            )
            try:
                return *tuple(await asyncio.wait_for(process, timeout=10)), ctx_reply
            except asyncio.exceptions.TimeoutError:
                return (
                    None,
                    await self.deliver(ctx_reply)(content=reply_msg[1]),
                    ctx_reply,
                )

    def _add_current_time(self, id_):
        return int(
            time.time() - self.user_joins.get(id_, time.time())
            + self.user_updates[to2(id_)].get(id_, 0)
        )

    def _format_highlighter(self, ctx, id_):
        if id_ == ctx.author.id:
            return lambda *_: self.bot.fm.fg.w
        return lambda default=lambda _: _: default

    def _format_row(self, ctx, entry, dicts, longest_time):
        sorted_d, dict_nicknames = dicts
        fg = self.bot.fm.fg  # pylint: disable=invalid-name
        member_id, member_seconds = entry
        highlight = self._format_highlighter(ctx, member_id)

        member_seconds += self._add_current_time(member_id)

        # Centering
        cen = divmod(divmod(member_seconds, 60)[0], 60)
        cen = f"{cen[0]}:{cen[1]:02}"
        cen = {4: "0", 6: " "}.get(len(str(cen)), "") + cen

        # Titles: rank hours level | name
        return f""" {highlight()(
                fg.r(f'{str(list(sorted_d).index(member_id) + 1)+chr(46):<4}')
            )}  {highlight()(
                self.bot.fm.bg.k(f'{cen:^7}' if longest_time < 6 else f'{cen:>7}')
            )}  {highlight(fg.y)(
                f'{get_level(member_seconds):^5}'
            )} {highlight(fg.k)(
                '|')} {highlight()(dict_nicknames.get(member_id, member_id)
            )}\n"""

    def _format_top(
            self, ctx, dicts, page, fmt="from users of this server"
    ):
        """Formats leaderboard string to send"""
        if page < 1:
            return "Page number cannot be less than 1."  # Very buggy

        format_time = Timer()

        sorted_d, dict_nicknames = dicts
        fg = self.bot.fm.fg  # pylint: disable=invalid-name
        page = list(sorted_d.items())[(page - 1) * 20 : page * 20]

        # Longest string length, then +1 if it is odd
        longest_name = (
            int(
                modf(
                    (
                        (max(len(dict_nicknames.get(i, str(i))) for i, j in page) - 1)
                        / 2
                    ) + 1
                )[1]
            ) * 2
        )
        # Used to center and align the colons
        longest_time = max(
            len(f"{(k:=divmod(divmod(j, 60)[0], 60))[0]}:{k[1]:02}") for i, j in page
        )
        name = " Name ".center(longest_name, "-").replace(
            "Name", "\033[0;1;4mName" + fg.k
        )
        titles = self.bot.fm[4](self.bot.fm[1]((
            f"{fg.k} {fg.r}Rank{fg.k}   {fg.c}Hours{fg.k}   {fg.y}Level{fg.k} | {name}"
        )))
        fmt = f"""Leaderboard of global scores {fmt}\n>>> ```ansi\n{titles}\n{
            ''.join(map(lambda x: self._format_row(ctx, x, dicts, longest_time), page))
            }```
        """

        # Remove colour formatting if user is on mobile
        # Discord mobile does not support colour rendering in code blocks yet
        if ctx.author.is_on_mobile():
            fmt = re.sub(
                r"(?<=^.{14} ).{6}",
                "",
                re.sub(r"\033\[(\d*;?)*m", "", fmt),
                flags=re.MULTILINE,
            )
            fmt = re.sub(r"-* Name -*", "Name", fmt, count=1)
        else:
            # Removes colour formatting until within message length limit
            removes = iter([40, 34, 33, 36, 31])
            while len(fmt) > 1900:
                fmt = re.sub(fr"\033\[({next(removes)};?)*m", "", fmt)
        log.debug(fmt)
        log.debug("format time: %f", format_time.stop())
        return fmt


async def setup(bot):
    """Setup"""
    await bot.add_cog(Levels(bot))
