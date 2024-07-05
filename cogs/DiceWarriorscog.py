from __future__ import annotations
from random import randint
from utils.embedutil import error
import emoji
import nextcord as discord
import utils.lobbyutil.lobbycog as lobby

TESTSERVER = 860527626100015154
dice = {n: v for n, v in enumerate((":one:", ":two:", ":three:", ":four:", ":five:", ":six:"), start=1)}


class DiceCog(lobby.LobbyCog):
    def __init__(self, client: discord.Client):
        super().__init__(client,
                         GAME_NAME="Dice Warriors",
                         BASE_CMD_NAME="dice",
                         maxplayers=2,
                         gameclass=DiceGame,
                         playerclass=DicePlayer)
                         # TESTSERVER_ID=TESTSERVER)

        self.logger = client.logger.getChild(f"{self.__module__}")
        self.logger.debug("DiceWarriors cog loaded")
        self.logger.debug(__class__)

        self.rules = """
        Each players takes turn attacking the other player. 
        Roll the dice to accumulate damage. You may stop anytime and deal the accumulated damage to the other player. 
        Rolling 1 nullifies the damage and ends your turn.
        The first player to reach 0 health loses."""

        self.credits = """Made by @theonlypeti"""

        self.add_help_category(lobby.HelpCategory(label="Test category",
                                                 description="This category is for testing the help command",
                                                 emoji="🎲",
                                                 helptext="This category seems to be working"))

        self.add_subcommand("leaderboard", self.leaderboard)

    async def leaderboard(self, interaction: discord.Interaction):
        """Displays the best player (not really)"""
        await interaction.send("@theonlypeti obviously.")
        # access self.ldb or smth


class DicePlayer(lobby.Player):
    def __init__(self, user: discord.User):
        super().__init__(user)
        self.starthealth = 100
        self.health = 100


class DiceGame(lobby.Game):
    def __init__(self, lobby: lobby.Lobby):
        super().__init__(lobby)
        for p in self.players:  # type: DicePlayer
            p.statistics["Games Played"] += 1
            p.health = p.starthealth  # in case people are replaying a game again after finishing it
        self.gamemsg: discord.Message = None  # the game message that displays the UI
        self.activeplayer = self.players[0]
        self.otherplayer = self.players[1]

    def swap_players(self):
        self.activeplayer, self.otherplayer = self.otherplayer, self.activeplayer

    async def start(self, interaction: discord.Interaction) -> None:
        self.gamemsg: discord.Message = await interaction.channel.send("Starting the game")
        while all([p.health > 0 for p in self.players]):  # main game loop, while both players are alive
            await self.show_ui(self.activeplayer)

        # game over
        self.lobby.ongoing = False  # set the lobby to be not in an ongoing game, so we can start a new game or let people join
        winner = self.otherplayer
        winner.statistics["Games Won"] += 1
        self.savePlayers()
        embed = self.show_embed(winner)
        embed.title = f"Game Over. {winner.name} wins!"
        await self.gamemsg.edit(content=None, embed=embed, view=None)
        # now here it is advised to send a message with a button asking them to resend the lobby, as interactions expire after 15 minutes and games can last longer than that
        await self.lobby.send_lobby(interaction)  # resend the lobby if they want rematch

    async def show_ui(self, player):
        """Show the game UI and wait for player to take action.
         If the player is AFK, automatically advance to the next player."""
        view = self.DiceView(self)
        embed = self.show_embed(player)
        self.gamemsg = await self.gamemsg.edit(content=None, embed=embed, view=view)
        if await view.wait():
            player.statistics["Times AFK'd"] += 1
        else:  # an action was taken
            ...  # handled by the view's button callbacks

    def show_embed(self, p):
        embed = discord.Embed(title=f"{p.user.name} it's your turn to roll the dice", color=p.user.color)
        for p in self.players:
            embed.add_field(name=p.user.display_name, value=f"Health: {p.health}")
        return embed

    class DiceView(discord.ui.View):
        def __init__(self, game: DiceGame):
            self.game = game
            self.dmg = 0
            super().__init__(timeout=30, auto_defer=False)

        @discord.ui.button(label="Roll", emoji=emoji.emojize(":game_die:", language="alias"), style=discord.ButtonStyle.primary)
        async def roll(self, button: discord.ui.Button, interaction: discord.Interaction):
            if interaction.user.id == self.game.activeplayer.user.id:
                roll = randint(1, 6)
                if roll == 1:
                    self.game.activeplayer.statistics["Damage lost"] += self.dmg
                    self.game.swap_players()
                    self.stop()
                    await interaction.send(f"{interaction.user.mention} rolled a 1, no damage dealt", delete_after=10)
                    return

                self.dmg += roll

                embed = self.game.gamemsg.embeds[0]
                embed.description = f"{interaction.user.mention} rolled {emoji.emojize(dice[roll], language='alias')} with a total of __**{self.dmg}**__ damage"

                button: discord.ui.Button = self.children[1]
                button.disabled = False
                button.label = f"Deal {self.dmg} damage"
                await interaction.edit(embed=embed, view=self)
            else:
                await error(interaction, "It's not your turn.")

        @discord.ui.button(label="Attack", style=discord.ButtonStyle.danger, disabled=True)
        async def attack(self, button, interaction: discord.Interaction):
            if interaction.user.id == self.game.activeplayer.userid:
                self.game.otherplayer.health -= self.dmg
                self.game.otherplayer.statistics["Damage taken"] += self.dmg
                self.game.activeplayer.statistics["Damage dealt"] += self.dmg

                await interaction.send(f"{self.game.activeplayer.user.mention} dealt {self.dmg} damage to {self.game.otherplayer.user.mention}", delete_after=10)
                self.game.swap_players()
                self.stop()
            else:
                await error(interaction, "It's not your turn.")


def setup(client):
    client.add_cog(DiceCog(client))
