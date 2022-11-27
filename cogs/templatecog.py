import nextcord as discord
from nextcord.ext import commands


class Template(commands.Cog):
    def __init__(self, client, baselogger):
        global logger
        logger = baselogger.getChild(f"{__name__}Logger")
        self.client = client

    # add your own commands here
    # def ecate():
        ...


def setup(client, baselogger):
    client.add_cog(Template(client, baselogger))
