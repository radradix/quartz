import youtube_dl
import asyncio
import discord
import pprint
from discord.utils import get
from discord.ext import commands
from discord import FFmpegPCMAudio
from index import client

song_queue = {}

class Song(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.command()
    async def define_as(self, prompt: str):
        await self.do_setup(prompt)

    async def do_setup(self, prompt: str):
        YTDL_OPTIONS = {
            'format': 'bestaudio',
            'default_search': 'auto',
            'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'source_address': '0.0.0.0'
            }
        ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)
        # https://qa.wujigu.com/qa/?qa=1057550/python-3-x-playing-music-with-a-bot-from-youtube-without-downloading-the-file
        info = ytdl.extract_info(prompt, download=False)
        if 'entries' in info:
            info = info['entries'][0]
        
        self.title = info['title']
        # print(self.title)
        self.artist = info['channel']
        # print(self.artist)
        self.bot_url = info['url']
        # print(self.bot_url)
        self.human_url = f"https://youtube.com/watch?q={info['display_id']}"
        # print(self.human_url)
        FFMPEG_OPTIONS = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn'
                }
        self.audio_source = discord.FFmpegPCMAudio(self.bot_url, **FFMPEG_OPTIONS)
        return self 

@commands.command(aliases=['play', 'p', 'pl', 'pla'])
async def _play(ctx, *args):
    prompt = " ".join(args)
    if not prompt:
        return await ctx.send("I need a song name to look up!")
    if ctx.author.voice is None:
        return await ctx.send("You are not in a voice channel!")
    if ctx.voice_client is None:
        await ctx.author.voice.channel.connect()
    else:
        await ctx.voice_client.move_to(ctx.author.voice.channel)

    chanson = Song(client)
    await chanson.define_as(prompt)
    print(f"Song: {chanson.title}")

    enqueue(ctx.guild, chanson)

    # If not already playing music, then play the first song to get started,
    # then call play_next() once finished
    if not ctx.voice_client.is_playing():
        await ctx.send(f'Playing "{chanson.title}" by {chanson.artist}')
        ctx.voice_client.play(song_queue[ctx.guild.id][0].audio_source, after=lambda e:
                asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))
    else:
        await ctx.send(f'Enqueued "{song_title}"')

def enqueue(guild: discord.guild.Guild, chanson: Song):
    '''
    song_queue = {
            guild1_id: [Song song1, Song song2]
            guild2_id: [Song song3, Song song4]
            }
    '''      
    if not song_queue.get(guild.id):
        song_queue[guild.id] = []
    song_queue[guild.id].append(chanson)

async def play_next(ctx):
    song_queue[ctx.guild.id].pop(0)
    new_song = song_queue[ctx.guild.id][0]
    await ctx.send(f'Moving on to "{new_song["title"]}"...')
    ctx.voice_client.play(new_song['source'], after=lambda e:
            asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))

@commands.command(aliases=['now_playing', 'np'])
async def _now_playing(ctx):
    if not ctx.voice_client or not song_queue[ctx.guild.id]:
        await ctx.send(f'Not playing anything at the moment ;)')
    else:
        await ctx.send(f'Now playing "{song_queue[ctx.guild.id][0]["title"]}"')

@commands.command(aliases=['queue', 'q'])
async def _queue(ctx):
    if ctx.guild.id not in song_queue.keys() or len(song_queue[ctx.guild.id]) == 0:
        return await ctx.send("Nothing in queue")
    embed = discord.Embed(title="Current queue", color=0xb2558d)
    index = 0
    for song in song_queue[ctx.guild.id]:
        index += 1
        embed.add_field(
                name=f"{index}. {song['title']}",
                value=song['url'],
                inline=False)
    return await ctx.send(embed=embed)

@commands.command(aliases=['stop', 'disconnect', 'dc'])
async def _stop(ctx):
    song_queue[ctx.guild.id] = []
    if ctx.voice_client is not None:
        await ctx.voice_client.disconnect()
        await ctx.send(f"Disconnected")
    else:
        await ctx.send(f"Wasn't connected in the first place lol")

def setup(bot):
    bot.add_command(_play)
    bot.add_command(_now_playing)
    bot.add_command(_queue)
    bot.add_command(_stop)
    bot.add_cog(Song(bot))
