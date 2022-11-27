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

start = time_module.perf_counter() #measuring how long it takes to boot up the bot

VERSION = "0.1a" #whatever you like lol, alpha 0.1, change it as you go on
PROJECT_NAME = "Testing bot" #NAME_YOUR_CHILD (note: this name will not show up as the bot name hehe)
AUTHOR = "sanyi" #ADD_YOUR_NAME_BE_PROUD
load_dotenv(r"./credentials/main.env") #loading the bot login token

parser = argparse.ArgumentParser(prog=f"{PROJECT_NAME} V{VERSION}", description='A fancy discord bot.', epilog=f"Written by {AUTHOR}\nTemplate written by theonlypeti.")

parser.add_argument("--minimal", action="store_true", help="Disable most of the extensions.")
parser.add_argument("--debug", action="store_true", help="Enable debug mode.")
parser.add_argument("--no_testing", action="store_true", help="Disable testing module.")
parser.add_argument("--logfile", action="store_true", help="Turns on logging to a text file.")

for cog in os.listdir("./cogs"): #adding command line arguments for removing some parts of the bot
    if cog.endswith("cog.py"):
        parser.add_argument(f"--no_{cog.removesuffix('cog.py')}", action="store_true", help=f"Disable {cog} extension.")

args = parser.parse_args() #reads the command line arguments

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

with open(__file__, "r") as file: #open this file
    linecount = len(file.readlines())

cogs = [cog for cog in os.listdir("./cogs") if cog.endswith(".py")]
cogcount = len(cogs)
if args.minimal:
    cogs = ["testing.py"]
else:
    for cog in reversed(cogs): #i could put this into the comprehension but holy frick what would be ugly
        if cog.endswith("cog.py"):
            if args.__getattribute__(f"no_{cog.removesuffix('cog.py')}") or args.minimal:
                cogs.remove(cog)
cogs.remove("testing.py") if args.no_testing else None

for n, file in enumerate(cogs, start=1): #its in two only because i wouldnt know how many cogs to load and so dont know how to format loading bar
    with open("./cogs/"+file, "r", encoding="UTF-8") as f:
        linecount += len(f.readlines())
    client.load_extension("cogs." + file[:-3], extras={"baselogger": baselogger})
    if not args.debug:
        sys.stdout.write(f"\rLoading... {(n / len(cogs)) * 100:.2f}% [{(int((n/len(cogs))*10)*'=')+'>':<10}]")
        sys.stdout.flush()
sys.stdout.write(f"\r{len(cogs)}/{cogcount} cogs loaded.".ljust(50)+"\n")
sys.stdout.flush()
os.chdir(root)

client.run(os.getenv("MAIN_DC_TOKEN"))
