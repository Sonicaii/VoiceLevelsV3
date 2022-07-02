"""levels cog handles commands related to the main levelling system"""
import asyncio
from dataclasses import dataclass
import datetime
import json
import logging
import time
from typing import Any, Optional, Tuple, Union
from math import modf
from re import findall, sub
import psycopg2
import discord
from discord.ext import tasks, commands

log = logging.getLogger("vl")


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
        return time.time_ns() - self.start_time


def get_level_f(seconds: int) -> (int, str):
    """Function gets the level in (level: int, percentage to next level: str)"""
    decimal, integer = modf((0.75 * ((seconds / 360) ** 0.5) + 0.05 * seconds / 360) / 4)
    return int(integer), decimal

def get_level(seconds: int) -> int:
    """Function gets level in int"""
    return get_level_f(seconds)[0]


def to2(discord_id: int) -> str:
    """Returns the right two digits of the input number"""
    return str(discord_id)[-2:]


class Levels(commands.Cog):
    """Main cog that handles detecting, processing and displaying levels"""

    def __init__(self, bot):
        # bot initialisation
        self.bot = bot

        # self.lock = asyncio.Lock()

        self.deliver = bot.deliver
        self.startup = True
        self.updater.start()

        # list of users who recently disconnected
        self.user_actions = set()
        self.user_joins = {}
        self.user_updates = {str(i).zfill(2): {} for i in range(100)}
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

    # @commands.command(hidden=True)
    # async def var(self, ctx, var):
    #     """Returns an attribute of the cog for debugging"""
    #     if log.level > 10:
    #        return
    #     try:
    #         if ctx.author.id not in self.bot.sudo:
    #             return
    #     except (AttributeError, TypeError, BaseException):
    #         return
    #     if hasattr(self, var):
    #         await ctx.send(eval("self."+var))

    async def disconnect_all(self):
        # Force write in by making everyone disconnect
        for uid in self.user_actions.copy():
            await self._on_voice_state_update(
                self.mimic(id=uid, name="mimic"),
                self.mimic(channel=1),
                self.mimic(channel=None),
            )

    async def cog_unload(self):
        """Final data upload"""
        log.warning("Levels cog was unloaded, attempting to write_in_data()")
        await self.disconnect_all()
        await self.write_in_data()
        log.warning("Reached end of levels unload!")

    async def write_in_data(self) -> None:
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
        if not occupied:
            log.debug("NOT OCCUPIED")
            return cur.close()

        cur.execute(
            "SELECT right_two, json_contents FROM levels WHERE right_two IN %s",
            (occupied,),
        )
        results = cur.fetchall()
        for right_two, json_contents in results:
            for uid, utime in self.user_updates[right_two].items():
                try:
                    json_contents[str(uid)] += utime
                except KeyError:
                    json_contents[str(uid)] = utime
        log.debug("Current updates = %s", str(self.user_updates))
        log.debug("Results = %s", str(results))
        # Lets perform python -OO optimisation malfunctions! Documentation above all??
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

        self.user_updates = {str(i).zfill(2): {} for i in range(100)}
        # '00': {}, '01': {}, '02': {}, ... , '97': {}, '98': {}, 99': {}

        for uid in self.user_actions.copy():
            if uid not in self.user_joins:
                self.user_actions.remove(uid)

        self.bot.conn.commit()

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
        await self._on_voice_state_update(member, before, after)

    async def _on_voice_state_update(self, member, before, after):
        log.debug("%s --> %s", before.channel, after.channel)
        if before.channel == after.channel or (
                member.id not in self.user_joins and after.channel is None
        ):
            # Name of the channel unchanged: not a disconnect or move
            # Disconnected while no record of inital connection
            return

        self.user_actions.add(member.id)

        # Add if not exist and return as it was only a join
        if member.id not in self.user_joins:
            log.debug("was just a join, now in user_joins")
            self.user_joins[member.id] = int(time.time())
            return

        # Add duration, and add to dict if doesn't exist
        try:
            self.user_updates[to2(member.id)][member.id] += (
                int(time.time()) - self.user_joins[member.id]
            )
            log.debug(
                "added %i seconds to %i",
                int(time.time()) - self.user_joins[member.id],
                member.id,
            )
        except KeyError:
            log.debug("new entry for %i", member.id)
            self.user_updates[to2(member.id)][member.id] = int(time.time()) - self.user_joins[member.id]

        # Removes from needing updates
        if after.channel is None:
            del self.user_joins[member.id]
        else:
            # If it was not a leave: refresh the count
            self.user_joins[member.id] = int(time.time())

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

        # opens the corresponding file
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
        current_user_time = (
            user_times[str(lookup.id)] + int(time.time()) - self.user_joins[lookup.id]
            if lookup.id in self.user_joins
            else user_times[str(lookup.id)]
        )

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
                fmt = lambda string: findall(r"(?<=[<@#!:a-z])(\d+)", string)
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

        # opens the corresponding part
        with self.bot.conn.cursor() as cur:
            cur.execute(
                "SELECT json_contents FROM levels WHERE right_two = %s",
                (to2(lookup.id),),
            )
            user_times = cur.fetchone()[
                0
            ]  # wow it already converted from json to py objects!

        if str(lookup.id) not in user_times:
            # record does not exist
            return await self.deliver(ctx)(f"{lookup.name} has no time saved yet.")

        # gets live info and the user times
        # current_user_times
        total_seconds = user_times[str(lookup.id)]
        if lookup.id in self.user_joins:
            total_seconds += int(time.time()) - self.user_joins[lookup.id]
        if lookup.id in self.user_updates[to2(lookup.id)]:
            total_seconds += self.user_updates[to2(lookup.id)][lookup.id]

        cut = datetime.timedelta(seconds=total_seconds)
        hours, minutes, seconds = str(cut).split()[-1].split(":")

        return await self.deliver(ctx)(
            "%s has spent %s days, %s hours, %s minutes and %s seconds on call: level %i" % (
                lookup.name,
                cut.days,
                hours,
                minutes.lstrip('0'),
                seconds.lstrip('0'),
                get_level(total_seconds),
            )
        )

    @commands.hybrid_command(name="all", description="Leaderboard for this server")
    async def all(self, ctx: commands.Context, page: Optional[int] = 1):
        """Acts as a normal leaderboard command

        Can get users of all servers if requested by a sudo user
        """
        if not isinstance(page, int) and not page.isdigit():
            page = 1

        log.debug("All command was called")
        total_time = Timer()

        if ctx.author.id in self.bot.sudo:
            async def process(ctx, page):

                sql_time = Timer()
                with self.bot.conn.cursor() as cur:
                    cur.execute("SELECT json_contents FROM levels")
                    results = cur.fetchall()
                log.debug("sql_time: %i", sql_time.stop())
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
                log.debug("organise_time: %i", organise_time.stop())
                return await self._format_top(
                    ctx, ret, page, "from users of *all* servers"
                ), True
            predeliver_time = Timer()
            formatted, _, ctx = await self.predeliver(
                ctx,
                ("Loading leaderboard...", "Took too long loading leaderboard"),
                process,
                page,
            )
            log.debug("predeliver_time: %i", predeliver_time.stop())
            if not formatted:
                return

            await self.deliver(ctx)(
                content=formatted
            )
            log.debug("total time: %i", total_time.stop())
            return

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

            formatted = await self._format_top(
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

        delivers a pending message if main content takes too long to process
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

    async def _format_top(
            self, ctx, dicts, page, fmt="from users of this server"
    ):
        """Formats leaderboard string to send"""
        format_time = Timer()

        sorted_d, dict_nicknames = dicts
        fg = self.bot.fm.fg
        bg = self.bot.fm.bg
        page = list(sorted_d.items())[(page - 1) * 20 : page * 20]

        # Longest string length, then +1 if it is odd
        longest_name = (
            int(
                modf(
                    (
                        (max([len(dict_nicknames.get(i, str(i))) for i, j in page]) - 1)
                        / 2
                    ) + 1
                )[1]
            ) * 2
        )
        # Used to center and align the colons
        longest_time = max(
            [len("%d:%02d" % divmod(divmod(j, 60)[0], 60)) for i, j in page]
        )

        name = " Name ".center(longest_name, "-").replace(
            "Name", "\033[0;1;4mName" + fg.k
        )

        titles = self.bot.fm[4](self.bot.fm[1]((
            f"{fg.k} {fg.r}Rank{fg.k}   {fg.c}Hours{fg.k}   {fg.y}Level{fg.k} | {name}"
        )))

        fmt = [f"Leaderboard of global scores {fmt}\n>>> ```ansi\n{titles}\n"]

        highlighter = (
            lambda id_:
                (lambda *_: fg.w)
            if id_ == ctx.author.id else
                (lambda default = lambda _:_: default)
        )

        aligners = {4: "0", 6: " "}

        for member_id, member_seconds in page:

            highlight = highlighter(member_id)

            # Add current time
            if member_id in self.user_actions:
                member_seconds += self.user_updates[to2(member_id)][member_id]
                if member_id in self.user_joins:
                    member_seconds += int(time.time()) - self.user_joins[member_id]

            cen = "%d:%02d" % divmod(divmod(member_seconds, 60)[0], 60)
            cen = aligners.get(len(str(cen)), "") + cen

            nickname = dict_nicknames.get(member_id, member_id)
            rank = fg.r(f"{str(list(sorted_d).index(member_id) + 1)+'.':<4}")
            hours = bg.k(f"{cen:^7}" if longest_time < 6 else f"{cen:>7}")
            level = f"{get_level(member_seconds):^5}"

            rank, hours, level, nickname = (
                highlight()(rank),
                highlight()(hours),
                highlight(fg.y)(level),
                highlight(fg.b)(nickname),
            )

            fmt.append(f" {rank}  {hours}  {level} {highlight(fg.k)('|')} {nickname}\n")

        fmt.append("```")
        fmt = "".join(fmt)

        # Remove colour formatting if user is on mobile
        # Discord mobile does not support colour rendering in code blocks yet
        if (await ctx.guild.fetch_member(ctx.author.id)).is_on_mobile():
            fmt = sub(r"\033\[(\d*;?)*m", "", fmt)
        else:
            # Removes colour formatting until within message length limit
            removes = iter([40, 34, 33, 36, 31])
            while len(fmt) > 1900:
                fmt = sub(r"\033\[(%i;?)*m" % next(removes), "", fmt)
        log.debug(fmt)
        log.debug("format time: %i", format_time.stop())
        return fmt

    @commands.command(pass_context=True)
    async def update(self, ctx):
        """Manually run through all channels and update into data.json"""
        if ctx.author.id in self.bot.sudo:
            await self._update(ctx)

    async def _update(self, ctx, automated=False):
        if ctx.author.id not in self.bot.sudo:
            return

        # async with self.lock(): used to be here
        # Hopefully no catastrophic errors occur while it's gone.
        if not automated:
            await self.disconnect_all()
        await self.write_in_data()  # Update everyone who is currently in

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
                self.user_updates[to2(uid)][uid] = 0
                self.user_joins[uid] = int(time.time())
                self.user_actions.add(uid)
                log.debug(msg, "")
            else:
                log.debug(msg, ", but was already in user actions")
        # for server in self.bot.guilds:  # List of guilds
        #     for details in server.channels:  # List of server channels
        #         if hasattr(details, "voice_states"):
        #             if details.voice_states:
        #                 for uid in details.voice_states:  # dict { id : info}
        #                     if uid not in self.user_actions:
        #                         self.user_updates[to2(uid)][uid] = 0
        #                         self.user_joins[uid] = int(time.time())
        #                         self.user_actions.add(uid)
        #                     log.debug(
        #                         f"\t\tfound {uid}%s",
        #                         ", but was already in user_actions"
        #                         if uid in self.user_actions else
        #                         ""
        #                     )
        # channels = [channel for channels in [
        # server.channels for server in self.bot.guilds] for channel in channels]
        # selected_channels_voice_states = [
        # channel.voice_states for channel in channels if hasattr(channel, "voice_states")]
        # ids = [uid for ids in selected_channels_voice_states for uid in ids]
        # ids = [uid for ids in [channel.voice_states for channel in [channel for channels in [
        # server.channels for server in self.bot.guilds] for channel in channels] if hasattr(
        # channel, "voice_states")] for uid in ids]

        if not automated:
            log.warning(f"{ctx.author.id} Called an update")

        return await ctx.send("Updated")

    @tasks.loop(minutes=30.0)
    async def updater(self):
        """Submits recorded seconds for each user into database every 30 mins"""
        if self.startup:
            i = 0  # Wait for sudo to load in init.py
            while not hasattr(self.bot, "sudo"):
                await asyncio.sleep(i := i + 10)
            # Reset when activated, prevents faulty join times due to downtime
            async def send(*args, **kwargs):
                pass
            await self._update(
                self.mimic(
                    send=send,
                    author=self.mimic(id=next(iter(self.bot.sudo)))
                ),
                automated=True,
            )
            self.startup = False
        else:
            # async with self.lock:
            await self.write_in_data()


# cog setup
async def setup(bot):
    """Setup"""
    await bot.add_cog(Levels(bot))
