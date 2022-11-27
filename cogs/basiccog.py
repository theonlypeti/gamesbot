import random
import nextcord as discord
from nextcord.ext import commands


class BasicCommands(commands.Cog): #cog for basic commands
    def __init__(self, client, baselogger):
        global logger
        logger = baselogger.getChild(f"{__name__}Logger")
        self.client = client

    @discord.slash_command(name="hello")  # type / in chat
    async def hello(self, interaction: discord.Interaction):
        await interaction.send(
            random.choice(
                ("Shut your bitch ass up",
                 "Hello ^^",
                 "HI!",
                 f"'Sup {interaction.user.name}",
                 f"Welcome to {interaction.channel.name}")
            )
        )

    @discord.user_command(name="Steal profile pic")  # right click on user
    async def stealpfp(self, interaction: discord.Interaction, user: discord.User):
        await interaction.send(user.avatar.url)

    @discord.message_command(name="You are a clown")  # right click on message
    async def randomcase(self, interaction: discord.Interaction, message: discord.Message):
        assert message.content
        await interaction.send(
            "".join(random.choice([betu.casefold(), betu.upper()]) for betu in message.content) + " <:pepeclown:803763139006693416>")

    @discord.slash_command(name="run", description="For running python code")
    async def run(self, ctx: discord.Interaction, command: str):
        if "@" in command:
            await ctx.send("oi oi oi we pinging or what?")
            return
        if any((word in command for word in ("open(", "os.", "eval(", "exec("))):
            await ctx.send("oi oi oi we hackin or what?")
            return
        try:
            await ctx.response.defer()  # for longer calculations this will wait for up to 15 mins
            a = eval(command)
            await ctx.send(a)
        except Exception as e:
            await ctx.send(f"{e}")
        # try /run ctx.user.avatar.url for example hehe


def setup(client, baselogger):
    client.add_cog(BasicCommands(client, baselogger))
