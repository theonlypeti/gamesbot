from __future__ import annotations
import asyncio
import os
from datetime import timedelta
import emoji
import nextcord as discord
from utils.lobbyutil.Colored import Colored
from utils.lobbyutil.Inventory import Inventory
import utils.lobbyutil.lobbycog as lobby
from utils.lobbyutil.Timer import Timer
from utils.lobbyutil.teamutil import MockPlayer, Team

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
        self.logger.event("hi")


        self.add_help_category(lobby.HelpCategory(label="Testing Category",
                                                  description="Just testing", emoji="🧪",
                                                  helptext="This is a test category for testing purposes.",
                                                  image=fr"data/amogus.png"))
        self.add_help_category(lobby.HelpCategory(label="Testing Category 2",
                                                  description="Just testing 2", emoji="🧪",
                                                  helptext="This is a test category for testing online image.",
                                                  image=fr"https://cdn.discordapp.com/avatars/617840759466360842/4469b4fbf681114f046e62f08e8a22e3.png?size=1024"))

        self.add_subcommand("ping", self.pingcmd, "Just testing")

    async def pingcmd(self, interaction: discord.Interaction):  # testing adding subcommand to main game command
        """Pong!"""
        await interaction.send("Pong!")

    @discord.slash_command(name="mytest", guild_ids=(TESTSERVER,))  # testing adding additional commands to the cog outside of the game command
    async def testcmd(self, interaction: discord.Interaction):
        """this does not appear"""
        ...

    @testcmd.subcommand(name="sub")
    async def testcmd2(self, interaction: discord.Interaction):  # testing adding this command to help above
        """for testing subcommands"""
        await interaction.send("Testing")

    @testcmd.subcommand(name="sub2")
    async def testcmd3(self, interaction: discord.Interaction):  # testing this command being left out of help
        """Oh my another subcommand!"""
        await interaction.send("Testing2")

    @discord.slash_command(name="baseonly", guild_ids=(TESTSERVER,))  # testing adding additional commands to the cog outside of the game command
    async def testcmdbase(self, interaction: discord.Interaction):
        """testing base only command"""
        await interaction.send("Working")



    class WordsPlayer(lobby.Player):

        def __init__(self, user: discord.User):

            self.money = 100
            super().__init__(user)
            self.words = []
            self.points = 0

        def __str__(self):
            return f"{self.user.display_name} ({self.words}) (${self.money}) ({self.points} pts)"

        def can_ready(self, lobby):
            if len(self.words) < 4:
                return False, "You need at least 4 words to be ready!"
            return True, ""

    class WordsLobby(lobby.Lobby):
        def __init__(self, interaction, cog, private, game, minplayers, maxplayers):
            super().__init__(interaction, cog, private,
                             lobbyView=MyButtons,
                             adminView=MyAdminView,
                             game=game,
                             minplayers=minplayers,
                             maxplayers=maxplayers)

            mplayer = MockPlayer(name="Sanyi", cog=cog)
            mplayer.words = ["apple", "banana", "cherry", "date"]
            mplayer.ready = True
            mplayer.points = 0
            mplayer.team = Team.from_color(Colored.get_color("red")) #pre-adding anything possible, just for fun
            self.players.append(mplayer)

        # def readyCondition(self):  # testing overriding methods
        #     return super().readyCondition() and all([len(player.words) > 3 for player in self.players])

        # async def on_join(self, player, inter):
        #     await player.user.send("Welcome to the game! Please add some words to the inventory.")
        #
        # async def on_leave(self, player, reason):
        #     await player.user.send("You have left the game. Reason: " + reason)

        async def on_ready(self, player, inter):
            player.money += 50 #testing, please don't actually do this lol
            self.cog.savePlayers(player)

        async def on_disband(self):
            print("aw")


class MyAdminView(lobby.AdminView):
    def __init__(self, lobby: TestGameCog.WordsLobby):
        self.lobby = lobby
        super().__init__(lobby)

    @discord.ui.button(label="Manage words", style=discord.ButtonStyle.grey, emoji=emoji.emojize(":ledger:"))
    async def mngwords(self, button, inter):
        inv: Inventory = Inventory([p.words for p in self.lobby.players], on_update=self.lobby.readyCheck)
        # inv.children[3].disabled = True
        inv.buttons["add"].disabled = True
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
        while self.round < 5:
            await asyncio.sleep(3)
            self.round += 1
            await self.next_turn()

        await self.channel.send(
            embed=discord.Embed(title="Thanks for playing!", color=discord.Color.green()),
            view=self.ReturnButtonView(self)
        )


    async def next_turn(self):
        await self.channel.send(f"Next turn! {self.round}")
        timer = Timer(self, duration=timedelta(seconds=12), name=f"Auto Timer {self.round}")
        await timer.start()
        await timer.render(self.channel)
        if await timer.wait():
            await self.channel.send(f"{timer.name} ended, proceeding to next turn.")
        else:
            await self.channel.send(f"{timer.name} was stopped, proceeding to next turn.")
        if timer.stopped_by:
            self.lobby.logger.info(timer.stopped_by)
            self.lobby.logger.info(self.getPlayer(timer.stopped_by).points)
            self.getPlayer(timer.stopped_by).points += 50
            self.lobby.logger.info(self.getPlayer(timer.stopped_by).points)
        # await self.channel.send()


def setup(client):
    client.add_cog(TestGameCog(client))
