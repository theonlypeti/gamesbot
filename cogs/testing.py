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

    import cooldowns

    ...

    @discord.slash_command(
        description="Ping command",
        guild_ids=TESTSERVER
    )
    @cooldowns.cooldown(1, 5, bucket=cooldowns.SlashBucket.author)
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pong!")

    @cooldowns.cooldown(1, 5, bucket=cooldowns.SlashBucket.author)
    async def bcallback(self, interaction: discord.Interaction):
        await interaction.send("pong")


    @discord.slash_command(
        description="Ping command2",
        guild_ids=TESTSERVER
    )
    @cooldowns.cooldown(1, 5, bucket=cooldowns.SlashBucket.author)
    async def sendb(self, interaction: discord.Interaction):
        view = discord.ui.View()
        b = discord.ui.Button(label="hi")
        b.callback = self.bcallback
        view.add_item(b)
        await interaction.send(view=view)


def setup(client):
    client.add_cog(Testing(client))

