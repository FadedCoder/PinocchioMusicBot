from music import music_functions
from messages import HELP_MESSAGE
from variables import PREFIX
import shlex


async def message_resolve(client, message, cmd_prefix):
    is_bot = False
    if message.author.bot:
        is_bot = True
    if message.content.startswith(cmd_prefix):
        args = shlex.split(message.content[len(cmd_prefix):])
        if args[0] == 'help':
            if is_bot:
                return
            await print_help(client, message, *args[len(cmd_prefix):])
        elif args[0] in functions.keys():
            if is_bot:
                return
            await functions[args[0]][0](client, message, *args[len(cmd_prefix):])
    for handler in handlers:
        await handler(client, message)


async def print_help(client, message, *args):
    if len(args) == 0:
        for text in [HELP_MESSAGE[i:i+1990] for i in range(0, len(HELP_MESSAGE), 1990)]:
            await message.author.send(text)
        await message.channel.send("DM-ed the help message!")
    elif args[0] in functions.keys():
        help_string = functions[args[0]][1]
        if help_string is None:
            help_string = "No help message for this command."
        await message.channel.send("`{2}{0}`: {1}".format(args[0], help_string, PREFIX))

functions = {}
handlers = []

functions.update(music_functions)
