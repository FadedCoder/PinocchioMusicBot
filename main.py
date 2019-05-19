import discord
import logging
import asyncio
import variables
import database
from modules import message_resolve
from music import functions
# import uvloop


logging.basicConfig(level=logging.DEBUG)
# asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.get_event_loop()
loop.create_task(database.prepare_tables())
client = discord.Client(
    loop=loop,
    activity=discord.Game(
        name=f"{variables.PREFIX}help | Pinocchio Bot's Sister"))


@client.event
async def on_ready():
    logging.info("Logged in as {0} - {1}.".format(client.user.name, client.user.id))


@client.event
async def on_message(message):
    await message_resolve(client, message, variables.PREFIX)


@client.event
async def on_voice_state_update(member, before, after):
    await functions.on_voice_state_update(member, before, after)

client.run(variables.TOKEN)
