"""Help cog"""

import discord
from discord.ext import commands


class Help(commands.Cog):
    """Help cog contains help command with descriptions of each command in the bot"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """Log cog activation"""
        self.bot.cogpr("Help", self.bot)

    @commands.hybrid_command(
        name="help", description="Get help about Voice Level's functions!"
    )
    async def help(self, ctx: commands.Context):
        """Generates help command in embed"""
        message_prefix = (
            ctx.message.content.split("help")[0]
            if ctx.message.content else
            (await self.bot.get_prefix(ctx))[0]
        )

        msg = ""
        embed = discord.Embed(description="_ _\n_ _", colour=0xAEFFAE)

        desc = ["" for i in range(4)]

        modules = [
            (
                "``top     ``",
                "This command lists the server's members by voice level rank."
                "\n*``Aliases: leaderboard, all``*",
            ),
            (
                "``total   ``",
                "This command gives your total time in seconds, minutes, hours and days."
                "\n*``Aliases: seconds``*",
            ),
            (
                "``level   ``",
                "This command gives your or the mentioned person their actual calculated time."
                "\n*``Aliases: time, info``*",
            ),
            (
                "``snipe   ``",
                "This command gives you the most recent message that was deleted.\n"
                "Putting a number after \"snipe\" will get you the message that was "
                "deleted at the specified distance away.\n"
                "*``e.g. snipe 3 will get the message 3 deleted messages ago.``*"
                "> Currently deletion is broken, only slash command version for now.",
            ),
        ]

        misc: list = [
            (
                "``members ``",
                "This command gives you the amount of members of this server.",
            ),
            (
                "``ping    ``",
                "This command gives you the latency of this bot.\n*``Aliases: latency``*",
            ),
            (
                "``lookup  ``",
                "This command translate Discord snowflake IDs (any Discord ID)\n"
                "to their date of creation. Discord IDs are linked to their creation time."
                "\n*``Slash commands: user, channel, id``*",
            ),
            (
                "``prefix   ``",
                (
                    "Changes prefix of this bot for this server\n"
                    "you can set a prefix with spaces in the middle and end by entering:"
                    f"\n>    `{message_prefix}prefix NEW PREFIX    \\`"
                    "\nthe `\\` indicates the end of the prefix"
                )
            ),
        ]

        if ctx.author.id in self.bot.sudo and not ctx.guild:
            msg = "**IMPORTANT**\n**RUN \"STOP\" TO KILL BOT IN CASE OF EMERGENCY**"
            embed.add_field(
                name="**IMPORTANT**",
                value="**RUN \"STOP\" TO KILL BOT IN CASE OF EMERGENCY**",
                inline=False,
            )

        for name, description in modules:
            desc[0] += f"**{name}** - {description}\n\n"
        for name, description in misc:
            desc[1] += f"**{name}** - {description}\n\n"

        embed.add_field(name="Commands", value=desc[0])
        embed.add_field(name="_ _\nMiscellaneous", value=desc[1], inline=False)
        embed.set_author(name="Help Panel")

        try:
            await self.bot.deliver(ctx)(msg, embed=embed)
        except discord.Forbidden:
            await self.bot.deliver(ctx)(
                "Cannot send help embed, dm me `help` to view commands"
                "or enable the `embed links` permission"
            )

async def setup(bot):
    """Setup"""
    await bot.add_cog(Help(bot))
