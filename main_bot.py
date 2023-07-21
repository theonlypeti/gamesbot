import sys
import nextcord as discord
from nextcord.ext import commands
from datetime import datetime
import os
import argparse
import time as time_module
import logging
from dotenv import load_dotenv
import coloredlogs

#TODO a sounds fishy game https://youtu.be/8FyXkwnnLc8

start = time_module.perf_counter() #measuring how long it takes to boot up the bot

VERSION = "1.0rc1" #whatever you like lol, alpha 0.1, change it as you go on
PROJECT_NAME = "GamesBot" #NAME_YOUR_CHILD (note: this name will not show up as the bot name hehe)
AUTHOR = "@theonlypeti" #ADD_YOUR_NAME_BE_PROUD
load_dotenv(r"./credentials/main.env") #loading the bot login token

parser = argparse.ArgumentParser(prog=f"{PROJECT_NAME} V{VERSION}", description='A fancy discord bot.', epilog=f"Written by {AUTHOR}\nTemplate written by theonlypeti.")

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

baselogger = logging.getLogger("Base")

#formatting the colorlogger
fmt = "[ %(asctime)s %(filename)s %(lineno)d %(funcName)s %(levelname)s ] %(message)s"
coloredlogs.DEFAULT_FIELD_STYLES = {'asctime': {'color': 'green'}, 'lineno': {'color': 'magenta'}, 'levelname': {'bold': True, 'color': 'black'}, 'filename': {'color': 'blue'},'funcname': {'color': 'cyan'}}
coloredlogs.DEFAULT_LEVEL_STYLES = {'critical': {'bold': True, 'color': 'red'}, 'debug': {'bold': True, 'color': 'black'}, 'error': {'color': 'red'}, 'info': {'color': 'green'}, 'notice': {'color': 'magenta'}, 'spam': {'color': 'green', 'faint': True}, 'success': {'bold': True, 'color': 'green'}, 'verbose': {'color': 'blue'}, 'warning': {'color': 'yellow'}}


if args.logfile: #if you need a text file
    FORMAT = "[{asctime}][{filename}][{lineno:4}][{funcName}][{levelname}] {message}"
    formatter = logging.Formatter(FORMAT, style="{")  #this is for default logger
    filename = f"./logs/bot_log_{datetime.now().strftime('%m-%d-%H-%M-%S')}.txt"
    os.makedirs(r"./logs", exist_ok=True)
    with open(filename, "w") as f:
        pass
    fl = logging.FileHandler(filename)
    fl.setFormatter(formatter)
    fl.setLevel(logging.DEBUG)
    #fl.addFilter(lambda rec: rec.levelno <= 10) #if u only wanna filter debugs
    baselogger.addHandler(fl)

baselogger.setLevel(logging.DEBUG) #base is debug, so the file handler could catch debug msgs too
if args.debug:
    coloredlogs.install(level=logging.DEBUG, logger=baselogger, fmt=fmt)
else:
    coloredlogs.install(level=logging.INFO, logger=baselogger, fmt=fmt)

root = os.getcwd()  #current working directory

intents = discord.Intents.default()
intents.members = True #needed so the bot can see server members
client = commands.Bot(intents=intents, chunk_guilds_at_startup=True,activity=discord.Game(name="Booting up..."))

@client.event
async def on_ready():
    game = discord.Game(f"{linecount} lines of code; V{VERSION}!")
    await client.change_presence(status=discord.Status.online, activity=game)
    print(f"Signed in as {client.user.name} at {datetime.now()}")
    baselogger.info(f"{time_module.perf_counter() - start}s Bootup time")

@client.event
async def on_disconnect(): #happens sometimes, ensures on_ready will not display million seconds
    global start
    start = time_module.perf_counter()

#-------------------------------------------------#

os.chdir(root)

files = os.listdir(root+r"/utils")
if not args.no_linecount: #if you don't want to open each file to read the linecount

    with open(__file__, "r") as file: #open this file
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

for n, file in enumerate(cogs, start=1): #its in two only because i wouldnt know how many cogs to load and so dont know how to format loading bar
    if not args.no_linecount:
        with open("./cogs/"+file, "r", encoding="UTF-8") as f:
            linecount += len(f.readlines())
    client.load_extension("cogs." + file[:-3], extras={"baselogger": baselogger})
    if not args.debug:
        sys.stdout.write(f"\rLoading... {(n / len(cogs)) * 100:.02f}% [{(int((n/len(cogs))*10)*'=')+'>':<10}]")
        sys.stdout.flush()
sys.stdout.write(f"\r{len(cogs)}/{cogcount} cogs loaded.".ljust(50)+"\n")
sys.stdout.flush()
os.chdir(root)

client.run(os.getenv("MAIN_DC_TOKEN"))

