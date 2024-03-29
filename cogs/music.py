# -*- coding: utf-8 -*-

'''
Copyright (c) 2019 Valentin B.
A simple music bot written in discord.py using youtube-dl.
Though it's a simple example, music bots are complex and
require much time and knowledge until they work perfectly.
Use this as an example or a base for your own bot and
extend it as you want. If there are any bugs,
please let me know.
Requirements:
Python 3.5+
pip install -U discord.py pynacl youtube-dl
You also need FFmpeg in your PATH environment variable or
the FFmpeg.exe binary in your bot's directory on Windows.
'''

import asyncio
import functools
import itertools
import math
import random

from typing import Literal, Optional
import discord
import youtube_dl  # pylint: disable=import-error
from async_timeout import timeout
from discord.ext import commands

# Silence useless bug reports messages
youtube_dl.utils.bug_reports_message = lambda: ''


class VoiceError(Exception):
    """Exception"""


class YTDLError(Exception):
    """Exception"""


class YTDLSource(discord.PCMVolumeTransformer):  # pylint: disable=too-many-instance-attributes
    """YTDL source"""
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(
            self,
            author,
            channel,
            source: discord.FFmpegPCMAudio,
            *,
            data: dict,
            search: str,
            volume: float = 0.5
    ):
        super().__init__(source, volume)

        self.requester = author
        self.channel = channel
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        date = data.get('upload_date')
        self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4]
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

        self.search = search
        self.played = False

    def __str__(self):
        return f'**{self.title}** by **{self.uploader}**'

    @classmethod
    async def create_source(cls, author, channel, search, *, loop: asyncio.BaseEventLoop = None):
        """Creates a source"""
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError(f'Couldn\'t find anything that matches `{search}`')

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError(f'Couldn\'t find anything that matches `{search}`')

        webpage_url = process_info['webpage_url']
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError(f'Couldn\'t fetch `{webpage_url}`')

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError as exc:
                    raise YTDLError(f'Couldn\'t retrieve any matches for `{webpage_url}`') from exc

        return cls(
            author,
            channel,
            discord.FFmpegPCMAudio(
                info['url'],
                **cls.FFMPEG_OPTIONS
            ),
            data=info,
            search=search
        )

    @staticmethod
    def parse_duration(duration: int):
        """Formats duration of seconds to larger units"""
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append(f'{days} days')
        if hours > 0:
            duration.append(f'{hours} hours')
        if minutes > 0:
            duration.append(f'{minutes} minutes')
        if seconds > 0:
            duration.append(f'{seconds} seconds')

        return ', '.join(duration)


class Song:  # pylint: disable=too-few-public-methods
    """Represents a song"""
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        """Creates an embed"""
        embed = (discord.Embed(title='Now playing',
                               description=f'```css\n{self.source.title}\n```',
                               color=discord.Color.blurple())
                 .add_field(name='Duration', value=self.source.duration)
                 .add_field(name='Requested by', value=self.requester.mention)
                 .add_field(
                     name='Uploader',
                     value=f'[{self.source.uploader}]({self.source.uploader_url})'
                 )
                 .add_field(name='URL', value=f'[Click]({self.source.url})')
                 .set_thumbnail(url=self.source.thumbnail))

        return embed


class SongQueue:  # asyncio.Queue
    """Represents a queue of songs, is actually a list"""
    def __init__(self, event_loop):
        self.event_loop = event_loop
        self.loop = False
        self.current = -1
        self._queue = []

    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return len(self._queue)

    async def put(self, obj):
        """Adds song to queue"""
        self._queue.append(obj)

    async def get(self):
        """Gets next song"""
        if self.loop:
            self.current = (self.current + 1) if self.current < len(self) - 1 else 0
        else:
            self.current += 1
            if self.current >= len(self):
                self.clear()
                self.current = 0

        msg = True
        while len(self) == 0:  # blocking
            if msg:
                msg = False
            await asyncio.sleep(0.2)

        if not self._queue[self.current].source.played:
            self._queue[self.current].source.played = True
            return self._queue[self.current]

        self._queue[self.current] = Song(
            await YTDLSource.create_source(
                self._queue[self.current].source.requester,
                self._queue[self.current].source.channel,
                self._queue[self.current].source.search,
                loop=self.event_loop
            )
        )
        self._queue[self.current].source.played = True
        return self._queue[self.current]

    def clear(self):
        """Clears queue"""
        self._queue.clear()

    def shuffle(self):
        """Shuffles queue"""
        random.shuffle(self._queue)

    def remove(self, index: int):
        """Removes song"""
        del self._queue[index]

class VoiceState:  # pylint: disable=too-many-instance-attributes
    """The voice state of the bot of a specific server"""
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue(self.bot.loop)

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        """loop bool"""
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        """Sets the event loop"""
        self._loop = value

    @property
    def volume(self):
        """Volume float"""
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        """Checks if playing"""
        return self.voice and self.current

    async def audio_player_task(self):
        """Main loop"""
        while True:
            self.next.clear()

            if self.loop:
                self.songs.current -= 1
            # Try to get the next song within 3 minutes.
            # If no song will be added to the queue in time,
            # the player will disconnect due to performance
            # reasons.
            try:
                async with timeout(180):  # 3 minutes
                    self.current = await self.songs.get()
            except asyncio.TimeoutError:
                self.bot.loop.create_task(self.stop())
                return

            self.current.source.volume = self._volume

            self.voice.play(self.current.source, after=self.play_next_song)
            await self.current.source.channel.send(embed=self.current.create_embed())

            await self.next.wait()

    def play_next_song(self, error=None):
        """Gets called after current song finishes, unblocks the `await self.next.wait()`"""
        if error:
            raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        """Skips song"""
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        """Clears queue, disconnects"""
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None


class Music(commands.Cog):
    """Music Cog"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: commands.Context):
        """gets the voice states"""
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    async def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send(f'An error occurred: {error}')

    @commands.command(name='join', invoke_without_subcommand=True)
    async def _join(self, ctx: commands.Context):
        '''Joins a voice channel.'''

        destination = ctx.author.voice.channel
        if ctx.voice_state.voice is not None:
            return await ctx.voice_state.voice.move_to(destination)

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='summon')
    @commands.has_permissions(manage_guild=True)
    async def _summon(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):
        '''Summons the bot to a voice channel.
        If no channel was specified, it joins your channel.
        '''

        if not channel and not ctx.author.voice:
            raise VoiceError(
                'You are neither connected to a voice channel nor specified a channel to join.'
            )

        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            return await ctx.voice_state.voice.move_to(destination)

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='leave', aliases=['disconnect'])
    @commands.has_permissions(manage_guild=True)
    async def _leave(self, ctx: commands.Context):
        '''Clears the queue and leaves the voice channel.'''

        if not ctx.voice_state.voice:
            return await ctx.send('Not connected to any voice channel.')

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

    @commands.command(name='volume')
    async def _volume(self, ctx: commands.Context, *, volume: int):
        '''Sets the volume of the player.'''

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        if 0 > volume > 100:
            return await ctx.send('Volume must be between 0 and 100')

        ctx.voice_state.volume = volume / 100
        await ctx.send(f'Volume of the player set to {volume}%')

    @commands.command(name='now', aliases=['current', 'playing', 'np'])
    async def _now(self, ctx: commands.Context):
        '''Displays the currently playing song.'''

        await ctx.send(embed=ctx.voice_state.current.create_embed())

    @commands.command(name='pause')
    @commands.has_permissions(manage_guild=True)
    async def _pause(self, ctx: commands.Context):
        '''Pauses the currently playing song.'''

        if not ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='resume')
    @commands.has_permissions(manage_guild=True)
    async def _resume(self, ctx: commands.Context):
        '''Resumes a currently paused song.'''

        if not ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='stop')
    @commands.has_permissions(manage_guild=True)
    async def _stop(self, ctx: commands.Context):
        '''Stops playing song and clears the queue.'''

        ctx.voice_state.songs.clear()

        if not ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()
            await ctx.message.add_reaction('⏹')

    @commands.command(name='skip')
    async def _skip(self, ctx: commands.Context):
        '''Vote to skip a song. The requester can automatically skip.
        3 skip votes are needed for the song to be skipped.
        '''

        if not ctx.voice_state.is_playing:
            return await ctx.send('Not playing any music right now...')

        ctx.voice_state.skip()

    @commands.command(name='queue', aliases=['q'])
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        '''Shows the player's queue.
        You can optionally specify the page to show. Each page contains 10 elements.
        '''

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += f'`{i+1}.` [**{song.source.title}**]({song.source.url})\n'

        embed = discord.Embed(
            description=f'**{len(ctx.voice_state.songs)} tracks:**\n\n{queue}'
        ).set_footer(text=f'Viewing page {page}/{pages}')
        await ctx.send(embed=embed)

    @commands.command(name='shuffle')
    async def _shuffle(self, ctx: commands.Context):
        '''Shuffles the queue.'''

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.shuffle()
        await ctx.message.add_reaction('✅')

    @commands.command(name='remove')
    async def _remove(self, ctx: commands.Context, index: int):
        '''Removes a song from the queue at a given index.'''

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction('✅')

    @commands.command(name='loop')
    async def _loop(
            self,
            ctx: commands.Context,
            option: Optional[Literal['queue', 'song']] = 'queue'
    ):
        '''Loops the currently playing song.
        Invoke this command again to unloop the song.
        '''

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        if option == 'song':
            # Inverse boolean value to loop and unloop.
            ctx.voice_state.loop = not ctx.voice_state.loop
            await ctx.reply('Now looping song' if ctx.voice_state.loop else 'Now not looping song')
        if option == 'queue':
            ctx.voice_state.songs.loop = not ctx.voice_state.songs.loop
            await ctx.reply(
                'Now looping queue'
                if ctx.voice_state.songs.loop else
                'Now not looping queue'
            )
        await ctx.message.add_reaction('✅')

    @commands.command(name='play')
    async def _play(self, ctx: commands.Context, *, search: Optional[str] = ""):
        '''Plays a song.
        If there are songs in the queue, this will be queued until the
        other songs finished playing.
        This command automatically searches from various sites if no URL is provided.
        A list of these sites can be found here:
            https://rg3.github.io/youtube-dl/supportedsites.html
        '''

        if not search:
            ctx.send("Attempting to resume")
            return ctx.voice_state.voice.resume()

        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        async with ctx.typing():
            try:
                source = await YTDLSource.create_source(
                    ctx.author,
                    ctx.channel,
                    search,
                    loop=self.bot.loop
                )
            except YTDLError as error:
                await ctx.send(f'An error occurred while processing this request: {error}')
            else:
                song = Song(source)

                await ctx.voice_state.songs.put(song)
                await ctx.send(f'Enqueued {source}')

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        """Checks if connected to voice channel"""
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError('You are not connected to any voice channel.')

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError('Bot is already in a voice channel.')


async def setup(bot):
    """Setup"""
    await bot.add_cog(Music(bot))
