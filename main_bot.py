#linecount: utils\.
# this line above is for the line counting function, it tells the bot to open the utils folder and count all lines in the .py files there, including subfolders, and add that to the total line count of the bot.
# this works in any cog file. if a cog file uses external .py files, you can add a line like this with the path to that file to include it in the line count.
# if you want to count only one file, end the path with the filename.py
# if you want to count a whole folder, end the path with a backslash \ and it will count all .py files in that folder and its subfolders.
# if you want to count only the files in a folder but not its subfolders, end the path with \. and it will only count the .py files directly in that folder.
import sys
from typing import Coroutine
from utils.getMsgFromLink import getMsgFromLink
from utils.lobbyutil.lobbycog import LobbyCog
from utils.mentionCommand import mentionCommand #for using in /run maybe
import emoji
import nextcord as discord
from nextcord.ext import commands
from datetime import datetime
import os
import argparse
import time as time_module
from dotenv import load_dotenv
from utils.antimakkcen import antimakkcen

#TODO a secret identity game using emojis https://youtu.be/klXNAS4bHvc
#TODO good face bad face
#TODO cheese thief https://www.youtube.com/watch?v=50V3M5VCsdI&t=1457s
#TODO snakeoil https://youtu.be/m1KNVsG0EcQ?si=YkiiaOMqJpQkvTva
#TODO no thanks game https://www.youtube.com/watch?v=TaFTKRjMY68

#TODO add /rl


start = time_module.perf_counter()  # measuring how long it takes to boot up the bot

VERSION = "1.2rc1"  # whatever lol
PROJECT_NAME = "GamesBot"  # NAME_YOUR_CHILD (note: this name will not show up as the bot name hehe)
AUTHOR = "@theonlypeti"  # ADD_YOUR_NAME_BE_PROUD
ADMIN_ID = 617840759466360842
load_dotenv(r"./credentials/main.env")  # loading the bot login token

parser = argparse.ArgumentParser(prog=f"{PROJECT_NAME} V{VERSION}", description='A fancy discord bot.', epilog=f"Written by {AUTHOR}\nTemplate written by @theonlypeti.")

for cog in os.listdir("./cogs"):
    if cog.endswith("cog.py"):
        parser.add_argument(f"--no_{cog.removesuffix('cog.py')}", action="store_true", help=f"Disable {cog} extension.")
        parser.add_argument(f"--only_{cog.removesuffix('cog.py')}", action="store_true", help=f"Enable only the {cog} extension.")

parser.add_argument("--minimal", action="store_true", help="Disable most of the extensions.")
parser.add_argument("--debug", action="store_true", help="Enable debug mode.")
parser.add_argument("--no_testing", action="store_true", help="Disable testing module.")
parser.add_argument("--only_testing", action="store_true", help="Add testing module.")
parser.add_argument("--logfile", action="store_true", help="Turns on logging to a text file.")
parser.add_argument("--no_linecount", action="store_true", help="Turns off line counting.")
args = parser.parse_args()

from utils import mylogger, embedutil, permcheck

baselogger = mylogger.init(args)  # initializing the logger

root = os.getcwd()  # current working directory

intents = discord.Intents.default()
# intents.presences = True
# intents.members = True  # needed so the bot can see server members
# intents.message_content = True
client = commands.Bot(intents=intents, chunk_guilds_at_startup=False, activity=discord.Game(name="Booting up..."), owner_id=ADMIN_ID)
client.logger = baselogger
client.root = root
client.linecounted = []


@client.event
async def on_ready():
    game = discord.CustomActivity(
        name="Custom Status",
        state=f"{client.linecount} lines of code; V{VERSION}!"
    )
    await client.change_presence(activity=game)
    print(f"Signed in as {client.user.name} at {datetime.now()}")
    baselogger.info(f"{time_module.perf_counter() - start}s Bootup time")

@client.event
async def on_disconnect():
    global start
    start = time_module.perf_counter()


@client.listen("on_message")
async def incoming_msg(msg: discord.Message):
    if not msg.guild and msg.author.id != client.user.id:
        tolog = f"{msg.author} sent DM: ['{msg.content}']{(' +' + ','.join([i.proxy_url for i in msg.attachments])) if msg.attachments else ''} "
        tolog = emoji.demojize(antimakkcen(tolog)).encode('utf-8', "ignore").decode()
        baselogger.warning(tolog, extra={"user": msg.author})

@client.listen("on_guild_join")
async def guildjoin(guild: discord.Guild):
    tolog = f"[{guild.name}] joined ({len(guild.humans)} people)]"
    tolog = emoji.demojize(antimakkcen(tolog)).encode('utf-8', "ignore").decode()
    baselogger.highlight(tolog)


@client.listen("on_guild_remove")
async def guildleave(guild: discord.Guild):
    tolog = f"Kicked from [{guild.name}] ({len(guild.humans)} people)]"
    tolog = emoji.demojize(antimakkcen(tolog)).encode('utf-8', "ignore").decode()
    baselogger.highlight(tolog)


@client.listen("on_interaction")
async def on_interaction_populate_cache(inter: discord.Interaction):
    if not client.intents.members:
        inter.client._connection._users.update({inter.user.id: inter.user._user})


@client.listen("on_interaction")
async def on_interaction(inter: discord.Interaction):
    cmdobj = inter.application_command
    if isinstance(cmdobj, discord.SlashApplicationSubcommand):
        cmd = cmdobj.parent_cmd.name + "/" + cmdobj.name
        opts = [f'{a["name"]} = {a["value"]}' for a in inter.data.get("options", [])[0]["options"]]
    elif isinstance(cmdobj, discord.SlashApplicationCommand):
        cmd = cmdobj.name
        opts = [f'{a["name"]} = {a["value"]}' for a in inter.data.get("options", [])]
    else:
        if inter.type == discord.InteractionType.component:
            buttonid = inter.data.get("custom_id", None)

            if inter.data.get("component_type", None) == 2:
                button: discord.ui.Button | None = discord.utils.find(lambda b: b.custom_id == buttonid, sum([v.children for v in client.all_views],[]))
                button: str = f"{button.__class__}: [{button.label or button.emoji=}]" if button else None
                tolog = f"[{inter.user}] used interaction [{button}] in: [{inter.guild}/{inter.channel}] on [{inter.message.created_at}]"

            elif inter.data.get("component_type", None) == 3:
                dd: discord.ui.Select | None = discord.utils.find(lambda v: v.custom_id == buttonid, [i for i in sum([v.children for v in client.all_views], [])])
                dd: str = f"{dd.__class__}: {dd.placeholder=}" if dd else None
                tolog = f"[{inter.user}] used interaction [{dd}, {inter.data.get('values')=}] in: [{inter.guild}/{inter.channel}] on [{inter.message.created_at}]"

            else:
                if inter.guild is None:
                    tolog = f"[{inter.user}] used interaction [{inter.data}] in: [DM/{inter.user}] on [{inter.message.created_at}]"
                else:
                    tolog = f"[{inter.user}] used interaction [{inter.data}] in: [{inter.guild}/{inter.channel}] on [{inter.message.created_at}]"

            tolog = emoji.demojize(antimakkcen(tolog)).encode('utf-8', "ignore").decode()
            baselogger.event(tolog)
        # baselogger.debug([i for i in dir(inter) if not i.startswith("_")])
        ...  #probably buttons, and autocomplete too
        return

    # pipikLogger.debug(inter.data.get("options", []))
    if inter.guild is None:
        tolog = f"[{inter.user}] called [{cmd} with {opts}] in: [DM/{inter.user}]"
    else:
        tolog = f"[{inter.user}] called [{cmd} with {opts}] in: [{inter.guild}/{inter.channel}]"

    tolog = emoji.demojize(antimakkcen(tolog)).encode('utf-8', "ignore").decode()
    baselogger.event(tolog, extra={"channel": inter.channel, "user": inter.user, "command": cmdobj})


@client.event
async def on_application_command_error(inter: discord.Interaction, error: Exception):
    try:
        errmsg = str(error).split(":", maxsplit=1)[1]
    except IndexError:
        errmsg = error
    try:
        await embedutil.error(inter, f"{errmsg}", delete=10)
        if "403" in errmsg and inter.guild is None:
            await embedutil.error(inter, f"This command will not work if the bot is not invited to the server, or called in a DM.", delete=25)
        elif "403" in errmsg:
            perms = permcheck.can_i(inter)
            if not perms.send_messages:
                await embedutil.error(inter, f"Missing permission: Send messages", delete=10)
            if not perms.attach_files:
                await embedutil.error(inter, f"Missing permission: Attach files", delete=10)
            if not perms.embed_links:
                await embedutil.error(inter, f"Missing permission: Embed links", delete=10)
    except discord.HTTPException as e:
        embed = discord.Embed(title="Error", description=f"{errmsg}", color=discord.Color.red())
        if e.status == 401:
            reason = "Interaction probably timed out after maximum of 15 minutes. Blame Discord."
            embed.add_field(name="Reason", value=reason)
        await inter.channel.send(embed=embed, delete_after=10)
    inter.client.logger.error(f"Error in /{inter.application_command.name} called by {inter.user}: {errmsg}", extra={"channel": inter.channel, "user": inter.user, "command": inter.application_command})
    if args.debug:
        raise error


@client.slash_command(name="allgames", description="Lists all available games", guild_ids=(860527626100015154,))
async def listgames(interaction: discord.Interaction):
    gamelist = ""
    for c in client.cogs:
        c = client.get_cog(c)
        if isinstance(c, LobbyCog): # TODO only list cogs that have the guild_ids set to None or the current guild id
            gamelist += f"{c.GAME_NAME} = {c.startcmd.get_mention(interaction.guild)}\n"
    await interaction.send(embed=discord.Embed(title="Available games", description=gamelist))



@client.slash_command(name="run", description="For running python code")
async def run(ctx: discord.Interaction, command: str):
    if "@" in command and ctx.user.id != ADMIN_ID:
        await ctx.send("oi oi oi we pinging or what?")
    elif any((word in command for word in ("open(", "os.", "eval(", "exec("))) and ctx.user.id != ADMIN_ID:
        await ctx.send("oi oi oi we hackin or what?")
    elif command.startswith("print"):
        await embedutil.error(ctx, "This command evaluates any expression and sends the result.\nThe **print** function however **returns nothing**. \nYou might want to just input the desired string in quotes.", delete=30)

    else:
        await ctx.response.defer()
        a = eval(command)
        await ctx.send(a)


@client.slash_command(name="arun", description="For running async python code")
async def arun(ctx: discord.Interaction, command: str, del_after: int=None):

    async def delmsg(msglink: str):
        a = await getMsgFromLink(client, msglink)
        await a.delete()

    if "@" in command and ctx.user.id != ADMIN_ID:
        await ctx.send("oi oi oi we pinging or what?")
        return
    if any((word in command for word in
            ("open(", "os.", "eval(", "exec("))) and ctx.user.id != ADMIN_ID:
        await ctx.send("oi oi oi we hackin or what?")
        return

    await ctx.response.defer()
    commands = command.split(";")
    for command in commands:
        if command and isinstance(command, str) and command.startswith("*"):
            commands.extend(eval(command[1:], globals().update({"ctx": ctx})))
            continue
        elif command and isinstance(command, Coroutine):
            a = await command
        elif command and callable(command):
            a = command()
        elif command and isinstance(command, str):
            try:
                a = await eval(command)
                if command.startswith("ctx.send"):
                    continue #lets not spam
            except TypeError:
                a = eval(command, globals().update({"ctx": ctx}))
            except Exception as e:
                await ctx.send(f"```diff\n-{e.__class__}: {e}\n```", delete_after=30)
                continue
        else:
            a = "impossible"
        if command and isinstance(command, str) and command.startswith("delmsg"):
            await embedutil.success(ctx, "Done.", delete=1)
        else:
            await ctx.send(str(a)[:2000], delete_after=del_after)


#-------------------------------------------------#

os.chdir(root)

async def set_linecount_activity():
    game = discord.CustomActivity(
        name="Custom Status",
        state=f"{linecount} lines of code; V{VERSION}!"
    )
    await client.change_presence(activity=game)

def readlinecount(fpath):
    with open(fpath, "r", encoding="UTF-8") as f:  # type: TextIOWrapper
        firstline = f.readline()
        lc = 1
        if firstline.startswith("#linecount:") or firstline.startswith("# linecount:"):
            toopen = firstline.split(":")[1].strip()
            if toopen:
                if toopen.endswith(".py"):
                    toopen = os.path.join(root, toopen)
                    # baselogger.debug(f"found file, Opening {toopen}")
                    lc = readlinecount(toopen)  # recursion makes me scared
                elif toopen.endswith("\\"):
                    # baselogger.debug(f"found folder walk, Opening {toopen}")
                    for lroot, dirs, files in os.walk(toopen):
                        for file in files:
                            if file.endswith(".py"):
                                #baselogger.debug(f"found file, Opening {os.path.join(lroot, file)}")
                                lc += readlinecount(os.path.join(lroot, file))
                elif toopen.endswith("\\."):
                    # baselogger.debug(f"found folder only, Opening {toopen}")
                    for file in os.listdir(toopen):
                        if file.endswith(".py"):
                            # baselogger.debug(f"found file, Opening {os.path.join(toopen, file)}")
                            lc += readlinecount(os.path.join(toopen, file))
                else:
                    baselogger.debug(f"malformed {fpath}")
                    ...
        lc += len(f.readlines())
        # baselogger.debug(f"finished {fpath}, {lc}")
        return lc


if __name__ == "__main__":
    os.chdir(root)
    linecount = 0
    if not args.no_linecount:
        client.linecount = readlinecount(os.path.join(root, __file__))

allcogs = [cog for cog in os.listdir("./cogs") if cog.endswith("cog.py")] + ["testing.py"]
cogcount = len(allcogs)
cogs = []
if not args.minimal:  # if not minimal
    if not [not cogs.append(cog) for cog in allcogs if args.__getattribute__(f"only_{cog.removesuffix('cog.py').removesuffix('.py')}")]: #load all the cogs that are marked to be included with only_*
        cogs = allcogs[:]  # if no cogs are marked to be exclusively included, load all of them
        for cog in reversed(cogs):  # remove the cogs that are marked to be excluded with no_*
            if args.__getattribute__(f"no_{cog.removesuffix('cog.py').removesuffix('.py')}"):  # if the cog is marked to be excluded
                cogs.remove(cog)  # remove it from the list of cogs to be loaded
# cogs.remove("testing.py") if args.no_testing else None  # remove testing.py from the list of cogs to be loaded if testing is disabled // no need to uncomment this line!

client.coglist = cogs  # for use in reload command
for n, file in enumerate(cogs, start=1): #it's in two only because i wouldn't know how many cogs to load and so dont know how to format loading bar
    profstart = time_module.perf_counter()
    if not args.no_linecount:
        fpath = os.path.join(root, "cogs", file)
        if fpath not in client.linecounted:
            client.linecounted += fpath
            client.linecount += readlinecount(fpath)
            # baselogger.debug(f"linecount: {client.linecount}")
    client.load_extension("cogs." + file[:-3])
    if not args.debug:
        sys.stdout.write(f"\rLoading... {(n / len(cogs)) * 100:.02f}% [{(int((n/len(cogs))*10)*'=')+'>':<10}]")
        sys.stdout.flush()

sys.stdout.write(f"\r{len(cogs)}/{cogcount} cogs loaded.".ljust(50)+"\n")
sys.stdout.flush()
os.chdir(root)

client.run(os.getenv("MAIN_DC_TOKEN"))

