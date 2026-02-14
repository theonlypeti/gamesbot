from __future__ import annotations
import asyncio
import os
from datetime import timedelta
from logging import Logger
import emoji
import nextcord as discord
from utils.Inventory import Inventory
import utils.lobbyutil.lobbycog as lobby
from utils.lobbyutil.teamutil import MockPlayer

TESTSERVER = 860527626100015154
root = os.getcwd()


class TestGameCog(lobby.LobbyCog):
    """Dumping ground of everything testing"""

    def __init__(self, client: discord.Client):
        super().__init__(client, "Charades",
                         playerclass=self.WordsPlayer,
                         lobbyclass=self.WordsLobby,
                         gameclass=MyGame,
                         TESTSERVER_ID=TESTSERVER)
        self.client = client
        self.logger: Logger = client.logger.getChild(f"{self.__module__}")
        self.logger.event("hi")

        self.add_subcommand("ping", self.testtest, "Just testing")
        self.add_help_category(lobby.HelpCategory(label="Testing Category",
                                                  description="Just testing", emoji="🧪",
                                                  helptext="This is a test category for testing purposes.",
                                                  image=fr"data/amogus.png"))
        self.add_help_category(lobby.HelpCategory(label="Testing Category 2",
                                                  description="Just testing 2", emoji="🧪",
                                                  helptext="This is a test category for testing online image.",
                                                  image=fr"https://cdn.discordapp.com/avatars/617840759466360842/4469b4fbf681114f046e62f08e8a22e3.png?size=1024"))

        self.other_commands = {self.testcmd2.name: self.testcmd2}

    async def testtest(self, interaction: discord.Interaction):  # testing adding subcommand to main game command
        """Pong!"""
        await interaction.send("Pong!")

    @discord.slash_command(name="mytest", guild_ids=(TESTSERVER,))  # testing adding additional commands to the cog outside of the game command
    async def testcmd(self, interaction: discord.Interaction):
        """this does not appear"""
        ...

    @testcmd.subcommand(name="mytest2")
    async def testcmd2(self, interaction: discord.Interaction):  # testing adding this command to help above
        """for testing"""
        await interaction.send("Testing")

    @testcmd.subcommand(name="mytest3")
    async def testcmd3(self, interaction: discord.Interaction):  # testing this command being left out of help
        """nor this does not appear"""
        await interaction.send("Testing3")


    class WordsPlayer(lobby.Player):

        def __init__(self, user: discord.User):
            super().__init__(user)
            self.words = []

        def __str__(self):
            return f"{self.user.display_name} ({self.words})"

    class WordsLobby(lobby.Lobby):
        def __init__(self, interaction, cog, private, game, minplayers, maxplayers):
            super().__init__(interaction, cog, private,
                             lobbyView=MyButtons,
                             adminView=MyAdminView,
                             game=game,
                             minplayers=minplayers,
                             maxplayers=maxplayers)
            self.words = []
            mplayer = MockPlayer(name="Sanyi", cog=cog)
            mplayer.points = 0
            mplayer.words = ["apple", "banana", "cherry", "date"]
            mplayer.ready = True
            self.players.append(mplayer)

        def readyCondition(self):  # testing overriding methods
            return all([len(player.words) > 3 for player in self.players]) and super().readyCondition()

        async def on_join(self, player, inter):
            await player.user.send("Welcome to the game! Please add some words to the inventory.")

        async def on_leave(self, player, reason):
            await player.user.send("You have left the game. Reason: " + reason)

        async def on_disband(self):
            print("aw")


class MyAdminView(lobby.AdminView):
    def __init__(self, lobby: TestGameCog.WordsLobby):
        super().__init__(lobby)

    @discord.ui.button(label="Manage words", style=discord.ButtonStyle.grey, emoji=emoji.emojize(":ledger:"))
    async def mngwords(self, button, inter):
        inv: Inventory = Inventory(self.lobby.words)
        await inv.render(inter, ephemeral=True)


class MyButtons(lobby.LobbyView):
    def __init__(self, lobby):
        self.middlebutton = Addwordsbutton
        super().__init__(lobby)


class Addwordsbutton(discord.ui.Button):
    def __init__(self, lobby: lobby.Lobby):
        self.lobby = lobby
        super().__init__(style=discord.ButtonStyle.primary, emoji=emoji.emojize(":plus:"))

    async def callback(self, interaction: discord.Interaction):
        """Add words"""
        user: TestGameCog.WordsPlayer = self.lobby.getPlayer(interaction.user)
        inv = Inventory(user.words, on_update=self.lobby.readyCheck)
        inv.EMPTY_INV = inv.EMPTY_INV + " Please lol."  # test overriding inventory strings
        await inv.render(interaction, ephemeral=True)

class MyGame(lobby.Game):
    def __init__(self, lobby: lobby.Lobby):
        self.lobby = lobby
        self.players = lobby.players
        self.channel = None
        self.round = 0

    async def start(self, interaction: discord.Interaction):
        self.channel = interaction.channel
        await interaction.channel.send("Game has started!")
        await self.next_turn()

    async def next_turn(self):
        self.round += 1
        await self.channel.send(f"Next turn! {self.round}")
        timer = lobby.Timer(self, duration=timedelta(seconds=10), name=f"Auto Timer {self.round}")
        # await timer.start()
        await timer.render(self.channel)
        if await timer.wait():
            await self.channel.send(f"{timer.name} ended, proceeding to next turn.")
        else:
            await self.channel.send(f"{timer.name} was stopped, proceeding to next turn.")
        # await self.channel.send()
        await asyncio.sleep(3)
        await self.next_turn()



def setup(client):
    client.add_cog(TestGameCog(client))


