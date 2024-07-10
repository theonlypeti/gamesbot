from __future__ import annotations
import os
import emoji
import nextcord as discord
from utils.Inventory import Inventory
import utils.lobbyutil.lobbycog as lobby

TESTSERVER = 860527626100015154
root = os.getcwd()


class TestGameCog(lobby.LobbyCog):

    def __init__(self, client: discord.Client):
        super().__init__(client, "Charades", playerclass=self.WordsPlayer, lobbyclass=self.WordsLobby, TESTSERVER_ID=TESTSERVER)
        # super().__init__(client, "Charades")
        self.client = client
        self.logger = client.logger.getChild(f"{self.__module__}")
        self.logger.log(25, "hi")
        self.other_commands = {self.testcmd2.name: self.testcmd2}
        self.add_subcommand("ping", self.testtest, "Just testing")
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
        def __init__(self, interaction, messageid, cog, private, game, minplayers, maxplayers):
            super().__init__(interaction, messageid, cog, private,
                             lobbyView=MyButtons,
                             adminView=MyAdminView,
                             game=game,
                             minplayers=minplayers,
                             maxplayers=maxplayers)
            self.players: list[TestGameCog.WordsPlayer] = self.players  # this is just to override the typehint of the attr
            self.words = []
        def readyCondition(self):  # testing overriding methods
            return all([len(player.words) > 3 and player.is_ready() for player in self.players])

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


def setup(client):
    client.add_cog(TestGameCog(client))


