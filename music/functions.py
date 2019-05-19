from .utils import MusicInfo, GuildState
from concurrent.futures import ThreadPoolExecutor
import discord
import asyncio
from variables import PREFIX


guild_states = {}
executor = ThreadPoolExecutor()


def get_guild_state(guild):
    if guild.id in guild_states:
        return guild_states[guild.id]
    else:
        guild_state = GuildState()
        guild_states.update({guild.id: guild_state})
        return guild_state


async def ensure_in_voice_channel(message):
    voice_state = message.author.voice
    voice_client = message.guild.voice_client
    if voice_state is None or voice_state.channel is None:
        await message.channel.send("Please join a voice channel first.")
        return None
    if voice_client is None:
        voice_client = await voice_state.channel.connect()
        return voice_client
    elif voice_client.channel == voice_state.channel:
        return voice_client
    else:
        await message.channel.send("""
Bot is already connected to a voice channel.
Make the bot leave previous voice channel with `{0}leave`. Requires **administrator** permission.
Or ask everyone to leave the previous voice channel.
        """.format(PREFIX))
        return None


async def _play_music(message, voice_client, guild_state, skip=False):
    if guild_state.requested_skip:
        guild_state.requested_skip = False
        return
    if len(guild_state.playlist) == 0:
        await stop_bot(voice_client, message.guild.id)
        return
    guild_state.requested_skip = skip
    music = guild_state.playlist.pop(0)
    guild_state.now_playing = music
    source = discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(
            music.stream_url,
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"),
        volume=guild_state.volume)

    def after_finished(err):
        # TODO: Fix non stopping bug.
        asyncio.run_coroutine_threadsafe(
            _play_music(message, voice_client, guild_state),
            voice_client.loop)

    embed = music.get_embed()
    # embed.remove_field(1)
    await message.channel.send("Now Playing", embed=embed)
    if voice_client.is_playing():
        voice_client.stop()
    voice_client.play(source, after=after_finished)


async def stop_bot(voice_client, guild_id):
    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()
    if guild_id in guild_states:
        guild_states.pop(guild_id)
        await voice_client.disconnect()


def _get_music_info(args, message, duration):
    info = MusicInfo(' '.join(args), message.author, duration)
    if not info.is_playlist:
        info.process_url()
    return info


async def play(client, message, *args):
    voice_client = await ensure_in_voice_channel(message)
    guild_state = get_guild_state(message.guild)
    duration = 0
    if guild_state.now_playing is not None:
        duration += guild_state.now_playing.duration
    if len(guild_state.playlist) > 0:
        for i in guild_state.playlist:
            duration += i.duration
    if not voice_client:
        return
    if len(args) == 0:
        await message.channel.send(
            "Usage: `{0}play <url/search string>`. YouTube recommended.".format(PREFIX)
        )
        return
    try:
        _info = await asyncio.gather(
            client.loop.run_in_executor(executor, _get_music_info, args, message, duration)
        )
        info = _info[0]
        if info.is_playlist:
            await message.channel.send("Link leads to playlist. Adding, please wait. (Max 5 can be added.)")
            entries = info.raw_info['entries']
            entries = entries if len(entries) < 5 else entries[:5]
            for entry in entries:
                _pl_info = await asyncio.gather(
                    client.loop.run_in_executor(
                        executor, _get_music_info, entry['url'], message, duration
                    ))
                pl_info = _pl_info[0]
                pl_info.process_url()
                duration += pl_info.duration
                guild_state.playlist.append(pl_info)
                if len(guild_state.playlist) != 0 or guild_state.now_playing is not None:
                    message = await message.channel.send(
                        "Added from playlist to queue.", embed=pl_info.get_embed())
                else:
                    await _play_music(message, voice_client, guild_state)
        else:
            if len(guild_state.playlist) != 0 or guild_state.now_playing is not None:
                guild_state.playlist.append(info)
                message = await message.channel.send(
                    "Added to queue.", embed=info.get_embed())
            else:
                guild_state.playlist.append(info)
                await _play_music(message, voice_client, guild_state)
    except AssertionError:
        await message.channel.send(
            "Music was not found! If it is youtube, make sure it is a public video."
        )
        return


async def skip(client, message, *args):
    guild_state = get_guild_state(message.guild)
    voice_client = await ensure_in_voice_channel(message)
    if voice_client is None:
        return
    if guild_state.now_playing is None:
        await message.channel.send("Not playing anything now.")
        return
    if len(guild_state.playlist) == 0:
        await message.channel.send("Skipped. Nothing remains in playlist. Exiting.")
        await stop_bot(voice_client, message.guild.id)
    else:
        await message.channel.send("Skipped")
        await _play_music(message, voice_client, guild_state, True)


async def leave(client, message, *args):
    if not message.author.guild_permissions.administrator:
        await message.channel.send("This command is restricted, to be used only by gods.")
        return
    voice_client = message.guild.voice_client
    if voice_client is None:
        await message.channel.send("Not connected to any voice channels.")
        return
    await stop_bot(voice_client, message.guild.id)


async def queue(client, message, *args):
    voice_client = await ensure_in_voice_channel(message)
    guild_state = get_guild_state(message.guild)
    if not voice_client:
        return
    playlist = guild_state.playlist.copy()
    if guild_state.now_playing is not None:
        playlist.insert(0, guild_state.now_playing)
    if len(playlist) == 0:
        await message.channel.send("Playlist is empty.")
    else:
        msg = "Current Queue:\n"
        duration = 0
        for i, v in enumerate(playlist):
            hours = duration//3600
            mins = duration//60 - hours*60
            secs = duration - mins*60 - hours*3600
            plays_in_txt = (
                "Plays in: {0:>02d}:{1:>02d}:{2:>02d}".format(hours, mins, secs)
                if duration > 0 else "Now Playing")
            hours = v.duration//3600
            mins = v.duration//60 - hours*60
            secs = v.duration - mins*60 - hours*3600
            duration_txt = "{0:>02d}:{1:>02d}:{2:>02d}".format(hours, mins, secs)
            msg += "{0}. **{1}** by *{2}*. Duration: {3}. {4}.\n".format(
                i + 1, v.title, v.uploader, duration_txt, plays_in_txt)
            duration += v.duration
            if len(msg) > 1800:
                await message.channel.send(msg)
                msg = ""
        if msg != "":
            await message.channel.send(msg)


async def volume(client, message, *args):
    voice_client = await ensure_in_voice_channel(message)
    if voice_client is None:
        return
    guild_state = get_guild_state(message.guild)
    if len(args) != 1 or not args[0].isdigit() or not (1 <= int(args[0]) <= 100):
        await message.channel.send("Usage: {0}volume <volume % between 1 to 100>".format(PREFIX))
        return
    volume = int(args[0])/100
    guild_state.volume = volume
    await message.channel.send(
        "Set volume to {0}%. Please skip current song. :thumbsup:".format(args[0]))


async def pause(client, message, *args):
    voice_client = await ensure_in_voice_channel(message)
    if voice_client is None:
        return
    if not voice_client.is_playing():
        await message.channel.send("Not playing anything.")
        return
    voice_client.pause()
    await message.channel.send("Paused music. :thumbsup:")


async def resume(client, message, *args):
    voice_client = await ensure_in_voice_channel(message)
    if voice_client is None:
        return
    if not voice_client.is_paused():
        await message.channel.send("Not paused.")
        return
    voice_client.resume()
    await message.channel.send("Resumed music. :thumbsup:")


async def status(client, message, *args):
    voice_client = await ensure_in_voice_channel(message)
    if voice_client is None:
        return
    guild_state = get_guild_state(message.guild)
    if guild_state.now_playing is None and len(guild_state.playlist) == 0:
        await message.channel.send("Not playing anything and queue is empty.")
        return
    embed = discord.Embed(title="Music Status", color=0x35fd24)
    if guild_state.now_playing.thumbnail:
        embed.set_thumbnail(url=guild_state.now_playing.thumbnail)
        embed.add_field(name="Currently Playing", value=guild_state.now_playing.title, inline=False)
        next_playing = "Nothing in queue."
    if len(guild_state.playlist) > 0:
        next_playing = guild_state.playlist[0].title
        embed.add_field(name="Next Playing", value=next_playing, inline=False)
        mins = guild_state.now_playing.duration//60
        secs = guild_state.now_playing.duration - mins*60
        embed.add_field(
            name="Current Music Duration", value="{0:>02d}:{1:>02d}".format(mins, secs), inline=False)
        req_by = guild_state.now_playing.requested_by
        embed.set_footer(
            text="Current one requested by: {0}".format(req_by.name), icon_url=req_by.avatar_url)
        await message.channel.send(embed=embed)


async def lyrics(client, message, *args):
    if len(args) == 0:
        await message.channel.send("Usage: {0}lyrics <song name>".format(PREFIX))
        name = " ".join(args)


async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    voice_client = member.guild.voice_client
    if voice_client:
        members_list = [x for x in voice_client.channel.members if not x.bot]
    else:
        members_list = 0
    if voice_client is not None and len(members_list) == 0:
        await stop_bot(voice_client, member.guild.id)


music_functions = {
    'p': (play, "Play some musix."),
    'play': (play, "Play some musix."),
    'leave': (leave, "Leave the voice channel."),
    'skip': (skip, "Skip the current song."),
    'queue': (queue, "View current queue."),
    'volume': (volume, "Set volume (default 100%)."),
    'pause': (pause, "Pause the music."),
    'resume': (resume, "Resume the music."),
    'status': (status, "Get current playing, next one etc.")
}
