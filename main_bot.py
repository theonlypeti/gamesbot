import sys
from typing import Coroutine
from utils.getMsgFromLink import getMsgFromLink
from utils.lobbyutil.lobbycog import LobbyCog
from utils.mentionCommand import mentionCommand
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


start = time_module.perf_counter()  # measuring how long it takes to boot up the bot

VERSION = "1.0rc1"  # whatever you like lol, alpha 0.1, change it as you go on
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

from utils import mylogger, embedutil

baselogger = mylogger.init(args)  # initializing the logger

root = os.getcwd()  # current working directory

intents = discord.Intents.default()
# intents.presences = True
# intents.members = True  # needed so the bot can see server members
# intents.message_content = True
client = commands.Bot(intents=intents, chunk_guilds_at_startup=True, activity=discord.Game(name="Booting up..."), owner_id=ADMIN_ID)
client.logger = baselogger
client.root = root


@client.event
async def on_ready():
    game = discord.CustomActivity(
        name="Custom Status",
        state=f"{linecount} lines of code; V{VERSION}!"
    )
    await client.change_presence(activity=game)
    print(f"Signed in as {client.user.name} at {datetime.now()}")
    baselogger.info(f"{time_module.perf_counter() - start}s Bootup time")


@client.event
async def on_disconnect():  # happens sometimes, ensures on_ready will not display a million seconds
    global start
    start = time_module.perf_counter()


@client.event
async def on_application_command_error(inter: discord.Interaction, error: Exception):
    errmsg = str(error).split(":", maxsplit=1)[1]
    try:
        await embedutil.error(inter, f"{errmsg}", delete=10)
    except discord.HTTPException as e:
        embed = discord.Embed(title="Error", description=f"{errmsg}", color=discord.Color.red())
        if e.status == 401:
            reason = "Interaction probably timed out after maximum of 15 minutes. Blame Discord."
            embed.add_field(name="Reason", value=reason)
        await inter.channel.send(embed=embed, delete_after=10)
    inter.client.logger.error(f"Error in /{inter.application_command.name} called by {inter.user}: {errmsg}")
    if args.debug:
        raise error


@client.listen("on_interaction")
async def oninter(inter: discord.Interaction):
    cmd = inter.application_command
    if isinstance(cmd, discord.SlashApplicationSubcommand):
        cmd = cmd.parent_cmd.name + "/" + cmd.name
        opts = [f'{a["name"]} = {a["value"]}' for a in inter.data.get("options", [])[0]["options"]]
    elif isinstance(cmd, discord.SlashApplicationCommand):
        cmd = cmd.name
        opts = [f'{a["name"]} = {a["value"]}' for a in inter.data.get("options", [])]
    else:
        ...  # probably buttons
        return

    tolog = f"[{inter.user}] called [{cmd} with {opts}]  in: [{inter.guild}/{inter.channel}]"
    tolog = emoji.demojize(antimakkcen(tolog)).encode('utf-8', "ignore").decode()
    baselogger.log(25, tolog)


@client.slash_command(name="allgames", description="Lists all available games", guild_ids=(860527626100015154,))
async def listgames(interaction: discord.Interaction):
    gamelist = ""
    for c in client.cogs:
        c = client.get_cog(c)
        if isinstance(c, LobbyCog):
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
    elif "redditapi" in command and ctx.user.id != ADMIN_ID:
        await ctx.send("Lol no sorry not risking anyone else doing stuff with MY reddit account xDDD")
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
    elif "redditapi" in command and ctx.user.id != ADMIN_ID:
        await ctx.send("Lol no sorry not risking anyone else doing stuff with MY reddit account xDDD")
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

files = os.listdir(root+r"/utils")
if not args.no_linecount:  # if you don't want to open each file to read the linecount

    with open(__file__, "r") as file:  # open this file
        linecount = len(file.readlines())

    for file in files:
        if file.endswith(".py"):
            with open(os.path.join(root, "utils", file), "r", encoding="UTF-8") as f:
                linecount += len(f.readlines())
else:
    linecount = "Unknown"

allcogs = [cog for cog in os.listdir("./cogs") if cog.endswith("cog.py")] + ["testing.py"]
cogcount = len(allcogs)
cogs = []

if not args.minimal:  # if not minimal
    if not [not cogs.append(cog) for cog in allcogs if args.__getattribute__(f"only_{cog.removesuffix('cog.py').removesuffix('.py')}")]: #load all the cogs that are marked to be included with only_*
        cogs = allcogs[:]  # if no cogs are marked to be exclusively included, load all of them
        for cog in reversed(cogs):  # remove the cogs that are marked to be excluded with no_*
            if args.__getattribute__(f"no_{cog.removesuffix('cog.py').removesuffix('.py')}"):  # if the cog is marked to be excluded
                cogs.remove(cog)  # remove it from the list of cogs to be loaded
cogs.remove("testing.py") if args.no_testing else None  # remove testing.py from the list of cogs to be loaded if testing is disabled

for n, file in enumerate(cogs, start=1):  # its in two only because i wouldnt know how many cogs to load and so dont know how to format loading bar
    if not args.no_linecount:
        with open("./cogs/"+file, "r", encoding="UTF-8") as f:
            linecount += len(f.readlines())
    client.load_extension("cogs." + file[:-3])
    if not args.debug:
        sys.stdout.write(f"\rLoading... {(n / len(cogs)) * 100:.02f}% [{(int((n/len(cogs))*10)*'=')+'>':<10}]")
        sys.stdout.flush()
sys.stdout.write(f"\r{len(cogs)}/{cogcount} cogs loaded.".ljust(50)+"\n")
sys.stdout.flush()
os.chdir(root)

client.run(os.getenv("MAIN_DC_TOKEN"))

