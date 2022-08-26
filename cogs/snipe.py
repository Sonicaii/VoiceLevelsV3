"""snipe cog enables recovery of deleted messages"""

import asyncio
from collections import deque
from dataclasses import dataclass
from io import BytesIO
import logging
from os import getenv
from os.path import basename
from typing import Optional
from urllib.parse import urlparse
import discord
from discord import app_commands
from discord.ext import commands
from aiohttp import ClientSession

# Arbitrary value of 35: 3500m furthest sniper kill distance
maxlen = int(getenv("BOT_SNIPE_MAX", "35"))
snipe_target = {}
log = logging.getLogger("vl")

# pylint: disable=no-member
class View(discord.ui.View):
    """A discord view, handling binning of messages"""
    __slots__ = "msg", "sniper", "deliver"

    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            self.__setattr__(key, value)

    @discord.ui.button(
        emoji="\U0001f5d1️",
        # style=discord.ButtonStyle.danger,
    )
    async def callback(
            self, interaction: discord.Interaction, _: discord.ui.button
    ):
        """Callback on button press to remove message and audit message sender"""

        # The person who clicked the bin button was the original sniper
        if interaction.user.id == self.sniper.id:
            await self.deliver(interaction)(
                f"<@{interaction.user.id}> denied their own hit."
            )
        else:
            self.msg.add(self.sniper.id)
            await self.deliver(interaction)(
                f"<@{interaction.user.id}> denied hit and destroyed "
                f"{self.sniper.display_name}'s ammunition.",
                delete_after=5
            )
        await interaction.message.delete()

        # Delete after ...
        await asyncio.sleep(5)
        return await interaction.delete_original_message()
# pylint: enable=no-member

class Msg:
    """Contains message attributes"""
    __slots__ = "denied", "content", "author", "id", "attachments"

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__setattr__(key, value)

        # Set of ids of people who cannot snipe this message
        self.denied = set()

    def add(self, deny_id: int) -> None:
        """Add id to set of """
        self.denied.add(deny_id)

    def is_denied(self, id_: int) -> bool:
        """Check if the given id has been denied to snipe this message"""
        return id_ in self.denied

@dataclass  # Dataclass operator useless...
class SmolAuthor:
    """Simplified author object"""
    __slots__ = ("name", "display_name", "id")
    def __init__(self, author):
        for attr in ("name", "display_name", "id"):
            self.__setattr__(attr, author.__getattribute__(attr))


class Snipe(commands.Cog):
    """Snipe cog

    Receives and stores deleted messages, letting users snipe them on request
    """
    def __init__(self, bot, msg):
        self.bot = bot
        self.deliver = bot.deliver
        self.msg = msg
        self.del_id = {}

    @commands.Cog.listener()
    async def on_ready(self):
        """Logs cog activation"""
        self.bot.cogpr("Snipe", self.bot)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Saves message"""
        if message.author == self.bot.user:
            # Don't log itself
            return

        # Split deleted message into 1000 char chunks to avoid 2k char limit
        string = message.content
        for content in (
                string[0 + i : 1000 + i] for i in range(0, len(string) + 1, 1000)
        ):
            message.content = content
            self.o_m_d(message)

    def o_m_d(self, message):
        """Process split message in chunks of 1000 chars"""
        msg = self.msg(
            author=SmolAuthor(message.author),
            content=message.content,
            id=message.id,
            # embed=message.embeds[0] if message.embeds else False,
            attachments=[i.url for i in message.attachments],
        )
        try:
            snipe_target[message.channel.id].appendleft(msg)
        except KeyError:
            # Beginning of list
            snipe_target[message.channel.id] = deque([msg], maxlen=maxlen)


    @app_commands.command(name="snipe", description="Snipes messages")
    @app_commands.describe(dist="Target distance (how many messages away)")
    async def app_snipe(self, interaction: discord.Interaction, dist: Optional[int] = 1):
        """Snipe command as app command

        If dist is not having the correct input, sync slash commands!
        """
        ctx = await commands.Context.from_interaction(interaction)
        return await self._snipe(ctx, dist)

    @commands.command(name="snipe")
    async def cmd_snipe(self, ctx: commands.Context, dist: Optional[int] = 1):
        """Snipe command as classic command"""
        return await self._snipe(ctx, dist)

    async def _snipe(self, ctx, dist):
        """The snipe command retrieves the latest or specified deleted message"""
        m_c_id = ctx.channel.id
        dist = abs(dist)

        if snipe_target.get(m_c_id) is None:
            # Nothing in list currently
            return await self.deliver(ctx)(
                "Couldn't find target to snipe in this channel.",
                ephemeral=True,
                delete_after=5,
            )
        if dist > maxlen:
            return await self.deliver(ctx)(
                "Distance is beyond maximum sniping distance",
                ephemeral=True,
                delete_after=5,
            )
        if dist > len(snipe_target[m_c_id]):
            return await self.deliver(ctx)(
                "Couldn't find target to snipe. No targets that far out.",
                ephemeral=True,
                delete_after=5,
            )
        if snipe_target[m_c_id][dist - 1].is_denied(ctx.author.id):
            return await self.deliver(ctx)(
                "You are unable to snipe this message", ephemeral=True
            )
        if dist:
            msg = snipe_target[m_c_id][dist - 1]
            range_msg = f"from {dist}00m"
            if dist > 35:  # Hard coded 35
                range_msg += " which is further than the world's longest confirmed sniper kill"
        else:
            msg = snipe_target[m_c_id][0]
            range_msg = "the closest target"

        send = (
            f"<@{ctx.author.id}> hit "
            + ('themselves' if msg.author.id == ctx.author.id else msg.author.name)
            + f"{range_msg}, who said\n{msg.content}\n"
        )
        file = None
        if len(msg.attachments) == 1:
            async with ClientSession() as session:
                async with session.get(msg.attachments[0]) as resp:
                    if resp.status != 200:
                        send += msg.attachments[0]
                        await self.deliver(ctx)(
                            "Could not download attachment file", ephemeral=True
                        )
                    file = BytesIO(await resp.read())
        else:
            for url in msg.attachments:
                send += url + "\n"
        view = View(msg=msg, sniper=SmolAuthor(ctx.author), deliver=self.deliver)
        await self.deliver(ctx)(
            send,
            # embed=discord.Embed().from_dict(msg.embed) if msg.embed else None,
            file=discord.File(file, basename(urlparse(msg.attachments[0]).path))
            if file
            else discord.utils.MISSING,
            view=view,
            ephemeral=False,
        )


async def setup(bot):
    """Setup"""
    await bot.add_cog(Snipe(bot, Msg))
