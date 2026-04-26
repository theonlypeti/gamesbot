import string
import nextcord as discord
from nextcord.ext import commands
from utils.lobbyutil.Inventory import Inventory
from utils.lobbyutil.Colored import Colored

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
        await interaction.send(ctxt + colorobj.emoji_heart)
        await interaction.send(Colored.green.text("Success!"), delete_after=5)

    @discord.slash_command(name="invtest", guild_ids=TESTSERVER)
    async def invtest(self, interaction: discord.Interaction):
        a = list(string.ascii_uppercase)
        inv: Inventory = Inventory(a)
        await inv.render(interaction, ephemeral=True)


def setup(client):
    client.add_cog(Testing(client))

