import youtube_dl
import discord
import re

YTDL_OPTS = {
    "default_search": "ytsearch",
    "format": "bestaudio/best",
    "quiet": True,
    "extract_flat": "in_playlist"
}
regex_str = "^(http:\/\/www\.|https:\/\/www\.|http:\/\/|https:\/\/)?[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(\/.*)?$"


class MusicInfo:
    def __init__(self, search_str, requested_by, time_left):
        self.is_playlist = False
        self.requested_by = requested_by
        self.time_left = time_left
        self.raw_info = self._get_info(search_str)
        if (self.is_playlist and not re.match(regex_str, search_str)):
            self.is_playlist = False
            self.raw_info = self._get_info(self.raw_info['entries'][0]['url'])

    def process_url(self):
        self.title = self.raw_info['title']
        self.duration = self.raw_info['duration']
        self.uploader = self.raw_info['uploader']
        self.thumbnail = self.raw_info['thumbnail'] if 'thumbnail' in self.raw_info else None
        self.video_url = self.raw_info['webpage_url']
        formats = {x['abr']: x for x in self.raw_info['formats'] if 'abr' in x}
        assert formats is not None and formats != {}
        abr_max = max(formats.keys())
        source = formats[abr_max]
        self.stream_url = source['url']
        self.abr = source['abr']
        self.asr = source['asr'] if 'asr' in source.keys() else None
        self.acodec = source['acodec'] if 'acodec' in source.keys() else None

    def _get_info(self, search_str):
        with youtube_dl.YoutubeDL(YTDL_OPTS) as ydl:
            try:
                info = ydl.extract_info(search_str, download=False)
                if "_type" in info and info["_type"] == "playlist":
                    self.is_playlist = True
                #     return self._get_info(info['entries'][0]['url'])
                return info
            except youtube_dl.utils.DownloadError:
                raise AssertionError

    def get_embed(self):
        embed = discord.Embed(
            title=self.title,
            description="Uploaded by: {0}".format(self.uploader),
            url=self.video_url, color=self.requested_by.colour)
        mins = self.duration//60
        secs = self.duration - mins*60
        embed.add_field(name="Average Audio Bitrate", value="{0} KBit/s".format(self.abr))
        if self.asr:
            embed.add_field(name="Audio Sampling Rate", value="{0} Hz".format(self.asr))
        if self.acodec:
            embed.add_field(name="Audio Codec", value=self.acodec)
        embed.add_field(
            name="Duration",
            value="{0:>02d}:{1:>02d}".format(mins, secs))
        if self.time_left:
            hours = self.time_left//3600
            mins = self.time_left//60 - hours*60
            secs = self.time_left - mins*60 - hours*3600
            embed.add_field(
                name="Will Play In",
                value="{0:>02d}:{1:>02d}:{2:>02d}".format(hours, mins, secs))
        if self.thumbnail:
            embed.set_thumbnail(url=self.thumbnail)
        embed.set_footer(text="Requested by: {0}".format(self.requested_by.name),
                         icon_url=self.requested_by.avatar_url)
        return embed


class GuildState:
    def __init__(self):
        self.volume = 0.6
        self.playlist = []
        self.now_playing = None
        self.requested_skip = False

        def is_requester(self, member):
            return self.now_playing.requested_by == member
