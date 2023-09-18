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

#TODO a secret identity game using emojis https://youtu.be/klXNAS4bHvc
#TODO good face bad face
#TODO cheese thief https://www.youtube.com/watch?v=50V3M5VCsdI&t=1457s


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

from utils import mylogger
mylogger.init(args) #initializing the logger
from utils.mylogger import baselogger #mylogger.baselogger too long

root = os.getcwd()  #current working directory

intents = discord.Intents.default()
intents.members = True #needed so the bot can see server members
client = commands.Bot(intents=intents, chunk_guilds_at_startup=True,activity=discord.Game(name="Booting up..."))
client.logger = baselogger

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
    client.load_extension("cogs." + file[:-3])
    if not args.debug:
        sys.stdout.write(f"\rLoading... {(n / len(cogs)) * 100:.02f}% [{(int((n/len(cogs))*10)*'=')+'>':<10}]")
        sys.stdout.flush()
sys.stdout.write(f"\r{len(cogs)}/{cogcount} cogs loaded.".ljust(50)+"\n")
sys.stdout.flush()
os.chdir(root)

client.run(os.getenv("MAIN_DC_TOKEN"))

