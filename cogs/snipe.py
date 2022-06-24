"""snipe cog enables recovery of deleted messages"""

import asyncio
from dataclasses import dataclass
from io import BytesIO
from os.path import basename
from typing import Optional
from urllib.parse import urlparse
import discord
from discord import app_commands
from discord.ext import commands
from aiohttp import ClientSession


snipe_target = {}


class View(discord.ui.View):
    """A discord view, handling binning of messages"""
    def __init__(self, **kwargs):
        self.sniper_id = 0
        super().__init__()
        for key, value in kwargs.items():
            self.__setattr__(key, value)

    @discord.ui.button(
        emoji="\U0001f5d1️",
        # style=discord.ButtonStyle.danger,
    )
    async def callback(
            self, interaction: discord.Interaction, select: discord.ui.button
    ):
        """Callback on button press to remove message and audit message sender"""

        for msg in snipe_target[interaction.channel.id]:

            # locating the message, could rewrite using ordered dict instead
            if msg.id != self.msg.id:
                continue

            # the person who clicked the bin button was the original sniper
            if interaction.user.id == self.sniper_id:
                await self.deliver(interaction)(
                    f"<@{interaction.user.id}> denied their own hit."
                )
            else:
                msg.add(self.sniper_id)
                await self.deliver(interaction)(
                    "<@%i> denied hit and destroyed <@%i>'s ammunition." % (
                        interaction.user.id,
                        self.sniper_id,
                    )
                )
            await interaction.message.delete()
            await asyncio.sleep(5)

            return await interaction.delete_original_message()

        # This should never send
        await self.deliver(interaction)(
            "Something went wrong.\n"
            "Could obtain information on where the bin was attached to\n"
            "This should not have happened, "
            "please contact the bot's developer "
            "and tell them what you did to get this message",
            ephemeral=True,
        )


class Msg:
    """contains message attributes"""
    __slots__ = "denied", "content", "author", "id", "attachments"

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__setattr__(key, value)

        # set of ids of people who cannot snipe this message
        self.denied = set()

    def add(self, deny_id: int) -> None:
        """Add id to set of """
        self.denied.add(deny_id)

    def is_denied(self, id_: int) -> bool:
        """Check if the given id has been denied to snipe this message"""
        return id_ in self.denied

@dataclass  # dataclass operator useless...
class SmolAuthor:
    """Simplified author object"""
    __slots__ = ("name", "nick", "id")
    def __init__(self, author):
        for attr in ("name", "nick", "id"):
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

        # split deleted message into 1000 char chunks to avoid 2k char limit
        string = message.content
        for content in (
                string[0 + i : 1000 + i] for i in range(0, len(string) + 1, 1000)
        ):
            message.content = content
            self.o_m_d(message)

    def o_m_d(self, message):
        """Process split message in chunks of 1000 chars"""
        m_c_id = message.channel.id

        author = SmolAuthor(message.author)

        msg = self.msg(
            author=author,
            content=message.content,
            id=message.id,
            # embed=message.embeds[0] if message.embeds else False,
            attachments=[i.url for i in message.attachments],
        )

        if m_c_id in snipe_target:
            temp_append = snipe_target[m_c_id]

            # arbitrary value of 35: 3500m furthest sniper kill distance
            if len(temp_append) > 35:
                del temp_append[0]
            temp_append.append(msg)
            snipe_target[m_c_id] = temp_append

        else:
            # Beginning of list
            snipe_target[m_c_id] = [msg]

    @app_commands.command(name="snipe", description="Snipes messages")
    @app_commands.describe(dist="Target distance (how many messages away)")
    async def app_snipe(self, interaction: discord.Interaction, dist: Optional[int] = 0):
        """Snipe command as app command"""
        return await self._snipe(interaction, dist)

    @commands.command(name="snipe")
    async def cmd_snipe(self, ctx: commands.Context, dist: Optional[int] = 0):
        """Snipe command as classic command"""
        return await self._snipe(ctx, dist)

    async def _snipe(self, interaction, dist):
        """The snipe command retrieves the latest or specified deleted message"""
        m_c_id = interaction.channel.id

        if snipe_target.get(m_c_id) is None:
            # Nothing in list currently
            return await self.deliver(interaction)(
                "Couldn't find target to snipe in this channel.", ephemeral=True
            )

        snipe_range = -dist if dist <= len(snipe_target.get(m_c_id, [])) else -1

        if snipe_target[m_c_id][snipe_range].is_denied(interaction.user.id):
            return await self.deliver(interaction)(
                "You are unable to snipe this message", ephemeral=True
            )

        if dist:
            if dist > len(snipe_target[m_c_id]):
                return await self.deliver(interaction)(
                    "Couldn't find target to snipe. No targets that far out.",
                    ephemeral=True,
                )
            msg = snipe_target[m_c_id][-dist]
            range_msg = f"from {dist}00m"
            if dist > 35:
                range_msg += " which is further than the world's longest confirmed sniper kill"
        else:
            msg = snipe_target[m_c_id][-1]
            range_msg = "the closest target"

        send = "<@%i> hit %s, %s, who said\n%s\n" % (
            interaction.user.id,
            msg.author.name,
            range_msg,
            msg.content,
        )
        file = None
        if len(msg.attachments) == 1:
            async with ClientSession() as session:
                async with session.get(msg.attachments[0]) as resp:
                    if resp.status != 200:
                        send += msg.attachments[0]
                        await self.deliver(interaction)(
                            "Could not download attachment file", ephemeral=True
                        )
                    file = BytesIO(await resp.read())
        else:
            for url in msg.attachments:
                send += url + "\n"
        view = View(msg=msg, sniper_id=interaction.user.id, deliver=self.deliver)
        await self.deliver(interaction)(
            send,
            # embed=discord.Embed().from_dict(msg.embed) if msg.embed else None,
            file=discord.File(file, basename(urlparse(msg.attachments[0]).path))
            if file
            else discord.utils.MISSING,
            view=view,
        )


async def setup(bot):
    """Setup"""
    await bot.add_cog(Snipe(bot, Msg))
