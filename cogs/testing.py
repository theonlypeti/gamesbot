import string
import nextcord as discord
from nextcord.ext import commands
from utils.Inventory import Inventory
from functools import wraps
from typing import Optional, Iterable, Callable
from utils.Colored import Colored

TESTSERVER = (860527626100015154,)


class Testing(commands.Cog):
    def __init__(self, client):
        global logger
        logger = client.logger.getChild(f"{__name__}Logger")
        self.client: discord.Client = client

    @discord.slash_command(name="colored", guild_ids=TESTSERVER)
    async def colored(self, interaction: discord.Interaction, txt: str, color: str = discord.SlashOption(choices=Colored.list().keys())):
        colorobj = Colored.get_color(color)
        ctxt = colorobj.text(txt)
        print(self.__class__)
        print(__class__)
        print(self.__module__)
        await interaction.send(ctxt + colorobj.emoji_heart)
        await interaction.send(Colored.green.text("Success!"), delete_after=5)

    @discord.slash_command(name="invtest", guild_ids=TESTSERVER)
    async def invtest(self, interaction: discord.Interaction):
        a = list(string.ascii_uppercase)
        inv: Inventory = Inventory(a)
        await inv.render(interaction, ephemeral=True)


    @discord.slash_command(name="userselect", guild_ids=TESTSERVER)
    async def invtest(self, interaction: discord.Interaction, usr: discord.User):
        await interaction.response.send_message(usr.display_name)


def setup(client):
    client.add_cog(Testing(client))

