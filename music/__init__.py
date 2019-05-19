from . import functions
import database


async def fetch_if_allowed(guild):
    engine = await database.prepare_engine()
    async with engine.acquire() as conn:
        fetch_query = database.Guild.select().where(
            database.Guild.c.guild == guild.id
            )
        cursor = await conn.execute(fetch_query)
        result = await cursor.fetchone()
        return result[database.Guild.c.music_enabled]


def wrapper(func):
    async def f(client, message, *args):
        allowed = await fetch_if_allowed(message.guild)
        if allowed:
            await func(client, message, *args)
        else:
            await message.channel.send("""
**This is a donator-exclusive feature.**
You are not allowed to use this command in this guild. Please donate to this bot to use this.
If you have donated already, and want to enable this feature, contact RandomGhost#0666.
            """)
    return f


music_functions = {}


for k, (a, b) in functions.music_functions.items():
    music_functions.update({k: (wrapper(a), b)})
