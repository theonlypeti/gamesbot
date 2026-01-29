from __future__ import annotations
from copy import deepcopy
import nextcord as discord
import emoji
from random import randint, choice
from utils import embedutil
import utils.lobbyutil.lobbycog as lobby

# guesser> each correctly found red herring = 1 point, wrong guess = 0 points
# blue kip - 1 point for each fish wasnt flipped before them being guessed minel hamarabb kibasaztni magad
# blue kip if banked before guessed then 0 points
# if red herring guessed = 0 points
# unflipped red herring - 1 point for each fish flipped before minel tovabb bennmaradni


class FishyPlayer(lobby.Player):
    def __init__(self, discorduser: discord.Member | dict | discord.User):
        super().__init__(discorduser)
        self.points = 0

    def __str__(self):
        return f"{self.name} ({self.points} points)"


class FishyLobby(lobby.Lobby):
    def __init__(self, interaction: discord.Interaction, messageid: discord.Message | None, cog: FishyCog, private=False, game: type[FishyGame] = None, minplayers: int = None, maxplayers: int = None):
        super().__init__(interaction, messageid, cog, private,
                         game=FishyGame,
                         minplayers=minplayers,
                         maxplayers=maxplayers)

        self.questions = deepcopy(self.cog.questions)


class FishyGame(lobby.Game):
    def __init__(self, lobby: FishyLobby): # Type hint with the new FishyLobby
        super().__init__(lobby)
        for player in self.lobby.players:
            player.statistics["Games played"] += 1
        self.players: list[FishyPlayer] = self.lobby.players
        self.guesser: FishyPlayer | None = None # Type hint
        self.questions = self.lobby.questions # Get questions from the lobby

    @property
    def explainers(self) -> list[FishyPlayer]:
        return [player for player in self.players if player != self.guesser]

    async def returnToLobby(self):
        self.lobby.ongoing = False
        for player in self.lobby.players:
            player.ready = False
        await self.lobby.send_lobby(self.channel) # Assuming self.channel is set during start

    async def start(self, channel: discord.TextChannel):
        self.channel = channel
        await super().start(channel)
        await self.round(channel)

    async def round(self, channel: discord.TextChannel):
        self.channel = channel

        if self.guesser:
            self.players.append(self.guesser)
            self.players.remove(self.guesser)
        self.guesser = self.players[0]

        self.truth = choice(self.explainers)
        self.lobby.cog.logger.debug(f"{self.truth.name=}")
        question = choice(self.questions)
        self.questions.remove(question)

        for p in self.explainers:
            try:
                await self.lobby.cog.client.get_user(p.userid).send(embed=discord.Embed(title=f"Your are a {'True blue kipper. Tell (and twist) the truth about the following question:' if p == self.truth else 'Red Herring. Lie about the following question:'}", description=f"Question: {question['question']}\nAnswer:||{question['answer']}||", color=discord.Color.blue() if p == self.truth else discord.Color.red()))
            except discord.HTTPException as e:
                await embedutil.error(self.channel, f"Could not send DM to {p.name}\n{e}", delete=15)
                self.lobby.cog.logger.error(f"{e}, {p.name}") # Use cog's logger
                continue

        viewObj = discord.ui.View(timeout=None)
        viewObj.add_item(GuesserDropdown(self))
        await self.channel.send(embed=discord.Embed(title=f"{self.guesser.name} is guessing", description=f"Question: {question['question']}"), view=viewObj)


class GuesserDropdown(discord.ui.Select):
    def __init__(self, game: FishyGame): # Type hint with FishyGame
        super().__init__()
        self.game: FishyGame = game
        self.placeholder = "Who is a lying red herring?"
        self.options = [discord.SelectOption(label=player.name, value=str(player.userid)) for player in self.game.explainers] + [discord.SelectOption(label="Take points & end turn", value="0", emoji=emoji.emojize(":outbox_tray:"))]

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id == self.game.guesser.userid:
            if self.values[0] == "0":
                guesser_points = len(self.game.explainers) - len(self.options) + 1
                self.game.guesser.points += guesser_points
                self.game.guesser.statistics["Times banked points"] += 1

                embedVar = discord.Embed(title="Nice!", description=f"{self.game.guesser.name} banked their points.", color=discord.Color.green())
                embedVar.add_field(name="Guesser points", value=f"{guesser_points}")
                embedVar.add_field(name="Blue kip points", value=f"{0}")
                embedVar.add_field(name="Not revealed Red herring points", value=f"{len(self.game.explainers) - len(self.options) + 1}")

                for player_option in self.options:
                    if player_option.value != "0":
                        herring_player = next((p for p in self.game.players if str(p.userid) == player_option.value), None)
                        if herring_player:
                            herring_player.points += guesser_points
                            herring_player.statistics["Guessers fooled"] += 1

                self.game.savePlayers()

                await interaction.response.edit_message(embed=embedVar, view=NextButton(self.game))
            else:
                chosen_userid = int(self.values[0])
                chosen: FishyPlayer | None = next((p for p in self.game.players if p.userid == chosen_userid), None)

                if chosen == self.game.truth:
                    embedVar = discord.Embed(title="Oh no!", description=f"{chosen.name} was telling the truth", color=discord.Color.blue())
                    guesser_points = 0
                    embedVar.add_field(name="Guesser points", value=f"{guesser_points}")
                    blue_kip_points = len(self.options) - 1
                    embedVar.add_field(name="Blue kip points", value=f"{blue_kip_points}")
                    embedVar.add_field(name="Not revealed Red herring points", value=f"{len(self.game.explainers) - len(self.options) + 1}")

                    for player_option in self.options:
                        if player_option.value != "0":
                            herring_player = next((p for p in self.game.players if str(p.userid) == player_option.value), None)
                            if herring_player:
                                herring_player.statistics["Guessers fooled"] += 1
                                herring_player.points += (len(self.game.explainers) - len(self.options) + 1)

                    if self.game.truth:
                         self.game.truth.statistics["Guessers fooled"] += 1
                         self.game.truth.points += blue_kip_points

                    self.game.guesser.statistics["Times got fooled"] += 1

                    await interaction.response.edit_message(embed=embedVar, view=NextButton(self.game))
                    self.game.savePlayers()
                else:
                    self.options = [option for option in self.options if int(option.value) != chosen_userid]
                    if len(self.options) == 2: # Only "Take points" and the last herring remain
                        embedVar = discord.Embed(title=f"Every red herring revealed!",
                                                 color=discord.Color.green())
                        guesser_points = len(self.game.explainers) - 1
                        embedVar.add_field(name="Guesser points", value=f"{guesser_points}")
                        self.game.guesser.points += guesser_points
                        self.game.guesser.statistics["Cleared all herrings"] += 1
                        self.game.savePlayers()
                        await interaction.response.edit_message(embed=embedVar, view=NextButton(self.game))
                    else:
                        embedVar = discord.Embed(title=f"Nice! {chosen.name} is a red herring!",
                                                 description=f"Do you wish to continue?",
                                                 color=discord.Color.red())
                        await interaction.response.edit_message(embed=embedVar, view=self.view)
                        self.game.guesser.statistics["Red herrings revealed"] += 1

        else:
            await embedutil.error(interaction, "It is not your turn to guess!", ephemeral=True)


class NextButton(discord.ui.View): # TODO if the guesser hasnt made a move in a while this should appear
    def __init__(self, game: FishyGame): # Type hint with FishyGame
        super().__init__(timeout=None)
        self.game = game

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.game.guesser.userid

    @discord.ui.button(label="Next round", emoji=emoji.emojize(":right_arrow:"), style=discord.ButtonStyle.green)
    async def nextbutton(self, button, interaction: discord.Interaction):
        await interaction.message.delete()
        await self.game.round(interaction.channel)

    @discord.ui.button(label="Back to Lobby (see points)")
    async def lobby(self, button, interaction: discord.Interaction):
        await interaction.message.delete()
        await self.game.returnToLobby()


class FishyCog(lobby.LobbyCog):
    def __init__(self, client1: discord.Client):
        super().__init__(client1,
                         GAME_NAME="Sounds Fishy",
                         BASE_CMD_NAME="fishy",
                         playerclass=FishyPlayer,
                         lobbyclass=FishyLobby,
                         gameclass=FishyGame,
                         minplayers=3)

        self.logger.debug("Fishy cog loaded")

        from data import fishyquestions
        self.questions = fishyquestions.questions


        self.rules = """Each turn there will be __one guesser__ whose task is to reveal __all red herrings__.
            Everyone else will be a __red herring__ except one player who is the __true blue kipper__.

            The guesser will read aloud a question and everyone else has to answer it.
            The __blue kipper__ will __tell the truth__, while the __red herrings__ will __lie__.
            The blue kipper may twist and turn the truth, but they must not lie.

            After everyone has answered, the guesser will __one by one__ try to reveal the red herrings.
            The guesser may __stop anytime__ and take the points, however __incorrectly guessing__
            and revealing the blue kipper will result in the guesser __getting 0 points__.
            Other players are getting points based on how many fish are revealed before them.
            """

        self.credits = """The game is based on the tabletop board game **Sounds fishy** by Big Potato Games
                     https://bigpotato.co.uk/
                     https://bigpotato.co.uk/collections/all/products/sounds-fishy
                     Bot and game adaptation created by @theonlypeti
                     https://github.com/theonlypeti"""

def setup(client):
    client.add_cog(FishyCog(client))