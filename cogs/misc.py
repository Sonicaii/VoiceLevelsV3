"""misc cog with miscellaneous commands"""

from datetime import datetime, timedelta
from getpass import getuser
import logging
from os import SEEK_END
from sys import exit as exit_
from time import perf_counter
from typing import Literal, Optional, Union
from re import findall, sub
import platform
import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import snowflake_time
import distro  # pylint: disable=import-error


log = logging.getLogger("vl")


def reverse_readline(filename: str, buf_size: int=8192):
    """A generator that returns the lines of a file in reverse order"""
    # https://stackoverflow.com/questions/2301789/how-to-read-a-file-in-reverse-order
    with open(filename, encoding="utf-8") as file:
        segment = None
        offset = 0
        file.seek(0, SEEK_END)
        file_size = remaining_size = file.tell()
        while remaining_size > 0:
            offset = min(file_size, offset + buf_size)
            file.seek(file_size - offset)
            buffer = file.read(min(remaining_size, buf_size))
            remaining_size -= buf_size
            lines = buffer.split("\n")
            # The first line of the buffer is probably not a complete line so
            # we'll save it and append it to the last line of the next buffer
            # we read
            if segment is not None:
                # If the previous chunk starts right from the beginning of line
                # do not concat the segment to the last line of new chunk.
                # Instead, yield the segment first
                if buffer[-1] != "\n":
                    lines[-1] += segment
                else:
                    yield segment
            segment = lines[0]
            for index in range(len(lines) - 1, 0, -1):
                if lines[index]:
                    yield lines[index]
        # Don't yield None if the file was empty
        if segment is not None:
            yield segment


class Misc(commands.Cog):
    """Cog containing miscellaneous commands"""
    def __init__(self, bot):
        self.bot = bot
        self.deliver = bot.deliver

    @commands.Cog.listener()
    async def on_ready(self):
        """Log cog activation"""
        self.bot.cogpr("Misc", self.bot)

    @commands.hybrid_command(description="Gets the number of members in the server")
    async def members(self, ctx: commands.Context):
        """Get total number of members in server"""
        await self.deliver(ctx)(
            f"Number of members in this server: {ctx.guild.member_count}"
        )

    @commands.command(pass_context=True, description="Get uptime of bot")
    async def uptime(self, ctx: commands.Context):
        """Uptime of bot, in duration and timestamp when it started"""
        if ctx.author.id in self.bot.sudo:
            diff = datetime.now() - self.bot.start_time
            delta = timedelta(days=diff.days, seconds=diff.seconds)
            timestamp = int(datetime.timestamp(self.bot.start_time))
            try:
                update_delta = timedelta(seconds=(datetime.now()-self.bot.update_time).seconds)
                update_timestamp = int(datetime.timestamp(self.bot.update_time))
                msg = f"Time since last update: `{update_delta}`\nOn <t:{update_timestamp}:D>\n"
            except AttributeError:
                msg = "Data has not been written in yet\n"
            msg += (
                f"interval: {self.bot.interval} minutes"
                if hasattr(self.bot, "interval")
                else "No interval set"
            )
            await self.edit_add_ping(
                ctx,
                f"Running from: {getuser()} {distro.id()} {distro.version()} {distro.name()}\n"
                f"{platform.platform()}\n"
                f"Time since last restart: `{delta}`\nOn <t:{timestamp}:D>\n{msg}"
            )

    @commands.hybrid_command(description="current latency of bot")
    async def latency(self, ctx: commands.Context):
        """Alias for ping"""
        await self._ping(ctx)

    @commands.hybrid_command(description="current latency of bot")
    async def ping(self, ctx: commands.Context):
        """Returns the bot ping"""
        await self._ping(ctx)

    async def _ping(self, ctx: commands.Context):
        # if ctx.interaction:
        # return await ctx.interaction.response.pong()  # What does this even do
        await self.edit_add_ping(ctx, f"Pinging... ~{round(self.bot.latency * 1000)}ms")

    async def edit_add_ping(self, ctx: commands.Context, *msg_args, **msg_kwargs):
        """Send message, then add the latency to the end of it"""
        start = perf_counter()
        response = await self.deliver(ctx)(*msg_args, **msg_kwargs)
        msg = f"\nCurrent latency is {(perf_counter() - start) * 1000:.2f}ms"
        try:
            if hasattr(response, "edit"):
                await response.edit(content=response.content + msg)
            else:
                await response.edit_message(content=response.content + msg)
        except discord.HTTPException:
            await self.deliver(ctx)(msg)

    async def _process_id(
            self,
            interaction: discord.Interaction,
            thing: Union[discord.Object, int, str],
            fmt: str,
    ) -> None:
        """Takes anything that can have an id extracted from it and returns with formatting"""
        try:
            msg = fmt.format(
                snowflake_time=discord.utils.format_dt(
                    snowflake_time(
                        int(thing.id)
                        if hasattr(thing, "id")
                        else int(
                            findall(r"(?<=[<@#!:a-z])(\d+)", thing)[0]
                            if isinstance(thing, str) and not thing.isdigit()
                            else thing
                        )
                    ),
                    style="F",
                )
            )
        except (ValueError, IndexError):
            msg = f"Invalid input: {thing}"
        return await self.deliver(interaction)(msg)

    @app_commands.command(name="id", description="Discord ID to time")
    @app_commands.describe(
        discord_id=(
            "The number from \"Copy ID\" in the discord context menu (right click)"
            "after enabling Settings>App Settings>Developer Mode"
        )
    )
    @app_commands.rename(discord_id="discord-id")
    async def id_(self, interaction: discord.Interaction, discord_id: str):
        """Any id as a integer. Discord cannot take id length integers so it must be a string"""
        _ = "`" if discord_id.isdigit() else ""
        await self._process_id(
            interaction,
            discord_id,
            f"{_}{discord_id}{_} is equivalent to {{snowflake_time}}",
        )

    @app_commands.command(description="Get when user account was made")
    async def user(
            self, interaction: discord.Interaction, user: Optional[discord.User] = None
    ):
        """Extract ID from discord user"""
        if not user:
            user = interaction.user
        await self._process_id(
            interaction,
            user,
            f"Account creation of {user.name} with the ID of `{user.id}`\n"
            "translates to {{snowflake_time}}",
        )

    @app_commands.command(description="Get when channel was made")
    async def channel(
            self,
            interaction: discord.Interaction,
            channel: Optional[Union[app_commands.AppCommandChannel, discord.Thread]] = None,
    ):
        """Extract ID from a channel or thread"""
        if not channel:
            channel = interaction.channel
        await self._process_id(
            interaction,
            channel,
            f"{channel.name} with the ID of `{channel.id}`\nwas created at {{snowflake_time}}",
        )

    @commands.hybrid_command(with_app_command=True)
    async def lookup(self, ctx: commands.Context, thing: Optional[str] = None):
        """Attempt to extract ID from anything the user puts in

        ...or themselves if no input"""
        if thing is None:
            thing = ctx.author.id
        await self._process_id(ctx, thing, f"{thing} translates to {{snowflake_time}}")

    @commands.command(name="prefix")
    @commands.has_permissions(manage_guild=True)
    async def cmd_prefix(self, ctx: commands.Context):
        """Classic discord command of prefix command

        To recover / reset the bot's prefix, it is possible to mention the bot as prefix
        """
        pre = ""
        for pre in await self.bot.get_prefix(ctx.message):  # 1-liner possible here
            if ctx.message.content.startswith(pre):
                break
        await self.prefix(ctx, ctx.message.content[len(pre) + 6 :])

    @app_commands.command(name="prefix")
    @commands.has_permissions(manage_guild=True)
    async def app_cmd_prefix(
        self,
        interaction: discord.Interaction,
        prefix: Optional[str],
    ):
        """Slash command version of prefix command, use this to recover bot prefix

        This can be accessed at any time and is useful to reset prefix without using it
        """
        await self.prefix(interaction, prefix)

    async def prefix(
        self,
        ctx: Union[commands.Context, discord.Interaction],
        prefix: str
    ):
        """Actual prefix command"""
        if not ctx.guild:
            self.deliver(ctx)("Setting prefixes outside servers unsupported")
        with self.bot.conn.cursor() as cur:
            msg = 'Reset prefix to: "%s"'
            if prefix:
                if prefix.endswith(" \\"):
                    prefix = prefix[:-1]
                if len(prefix) > 16:
                    return await self.deliver(ctx)(
                        "Prefix is too long, maximum 16 characters.", ephemeral=True
                    )
                async with ctx.channel.typing():
                    cur.execute(
                        """
                        INSERT INTO prefixes (id, prefix)
                        VALUES (%s, %s)
                        ON CONFLICT (id) DO UPDATE
                            SET prefix = EXCLUDED.prefix
                        """,
                        (str(ctx.guild.id), prefix),
                    )
                    await self.deliver(ctx)(msg % discord.utils.escape_markdown(prefix))
            else:
                cur.execute(
                    "DELETE FROM prefixes WHERE id ~ %s",
                    (str(ctx.guild.id),)
                )
                await self.deliver(ctx)(msg % self.bot.default_prefix)
        self.bot.conn.commit()
        self.bot.prefix_cache_pop(ctx.guild.id)

    @commands.command()
    async def tail(self, ctx: commands.Context, lines: Optional[int] = 10):
        """Print out tail of discord.log"""
        if ctx.author.id not in self.bot.sudo:
            return
        gen = reverse_readline("discord.log")
        txt = []
        length = line = 0
        try:
            while next_line := next(gen):
                if length >= 1989 or (line := line + 1) > lines:
                    await self.deliver(ctx)("```ansi\n" + "\n".join(txt[::-1])  + "```")
                    txt.clear()
                    length = 0
                if (line := line + 1) > lines:
                    break

                txt.append(next_line)
                length += len(next_line := sub(  # Add `(\033\[(\d*;?)*m)?` no colour
                    r"(\[[\w\s]*\] discord(\.(\w\w*\.?)*)?:)?(```)?",
                    "",
                    next_line,
                ).replace("[", "", 1).replace("]", "", 1)) + 1
        except StopIteration:
            pass

    @commands.command(description="STOP")
    async def kill(self, ctx: discord.Interaction):
        """Stop bot"""
        try:
            if ctx.author.id not in self.bot.sudo:
                return
            await self.deliver(ctx)(
                "Killed process (might auto-reload, run another stop after)",
                ephemeral=True,
            )
        finally:
            exit_(1)

    @commands.command()
    async def cache(self, ctx: commands.Context):
        """Check bot prefix cache size"""
        if ctx.author.id not in self.bot.sudo:
            return
        await self.deliver(ctx)(f"Cache size is: {self.bot.prefix_cache_size()}")

    @commands.command(hidden=True)
    async def sudo(
            self,
            ctx: commands.Context,
            mode: Optional[
                Literal["add", "new", "+", "remove", "rm", "-", "del", "get", "refresh"]
            ],
            user: str = ""
    ):
        """Manages sudo users"""
        try:
            if ctx.author.id not in self.bot.sudo:
                return
        except AttributeError:
            return await ctx.send("Reached AttributeError")

        # We can use match statement here, but did not because of compatibility
        if mode in ("get", None):
            return await ctx.send(self.bot.sudo)
        if mode == "refresh":
            return await self.bot.refresh_sudo()
        if not user.isdigit():
            return await ctx.send("Input was not a discord id")
        log.warning(
            "%i has attempted to %s user %s to sudo in guild %i: %s",
            ctx.author.id,
            mode,
            user,
            ctx.guild.id,
            ctx.guild.name,
        )
        with self.bot.conn.cursor() as cur:
            if mode in ("add", "new", "+"):
                if int(user) in self.bot.sudo:
                    return await ctx.send("User already has sudo access")
                cur.execute("INSERT INTO sudo VALUES (%s)", (str(user),))
                self.bot.sudo.add(int(user))
                log.warning("Successfully added")
                await ctx.send(f"Added {user} to sudo")
            elif mode in ("del", "remove", "rm", "-") and int(user) in self.bot.sudo:
                cur.execute("DELETE FROM sudo WHERE id = %s", (str(user),))
                self.bot.sudo.remove(int(user))
                log.warning("Successfully removed")
                await ctx.send(f"Removed {user} from sudo")
            else:
                await ctx.send(f"{user} was not in sudo")
        self.bot.conn.commit()


async def setup(bot):
    """Setup"""
    await bot.add_cog(Misc(bot))
