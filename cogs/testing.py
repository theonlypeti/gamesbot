import nextcord as discord
from nextcord.ext import commands

TESTSERVER = (957469186798518282,) #Replace with your server id
#commands in this file will only show up in your server that you specify here


class Testing(commands.Cog):
    def __init__(self, client, baselogger):
        global logger
        logger = baselogger.getChild(f"{__name__}Logger")
        self.client = client
        if TESTSERVER[0] == 957469186798518282: #default check, ignore this if you changed it already
            logger.warning("in cogs/testing.py replace the server id to your server's id for the testing commands to show up, then you can delete this line.")

    class Testvw(discord.ui.View):
        def __init__(self, user: discord.Member):
            self.msg = None
            self.user = user
            super().__init__(timeout=30)

        @discord.ui.button(label="test")
        async def test(self, button, interaction):
            logger.info("button pressed")
            button.style = discord.ButtonStyle.green
            await self.msg.edit(view=self)

        async def on_timeout(self) -> None:
            logger.info("view timeouted, noone pressed it in time")
            self.children[0].disabled = True
            await self.msg.edit(view=self)

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            """if this button is not pressed by the command caller, it won't work."""
            return interaction.user == self.user

    class TextInputModal(discord.ui.Modal):
        def __init__(self):
            super().__init__(title="Testing")
            self.inputtext = discord.ui.TextInput(label="Say something", required=False)
            self.add_item(self.inputtext)

        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer()
            await interaction.send(f"{interaction.user} says {self.inputtext.value}")

    @discord.slash_command(name="testingvw", description="testing", guild_ids=TESTSERVER)
    async def testing(self, ctx: discord.Interaction):
        viewObj = self.Testvw(ctx.user)
        viewObj.msg = await ctx.send(content="Hello", view=viewObj, tts=True)

    @discord.slash_command(name="modaltesting", description="testing", guild_ids=TESTSERVER)
    async def modaltesting(self, ctx):
        await ctx.response.send_modal(self.TextInputModal())


def setup(client, baselogger):
    client.add_cog(Testing(client, baselogger))

