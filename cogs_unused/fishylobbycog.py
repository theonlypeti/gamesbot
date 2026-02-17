from __future__ import annotations
import os
import string
from copy import deepcopy

from utils.antimakkcen import antimakkcen
from typing import Optional
import nextcord as discord
import nextcord.errors
from nextcord.ext import commands
import json
import emoji
from random import randint, choice
from collections import defaultdict
from utils.mentionCommand import mentionCommand # Assuming this is needed elsewhere or adapted
from utils.paginator import Paginator # Assuming this is needed elsewhere
from utils import embedutil
import utils.lobbyutil.lobbycog as lobby # Import the lobby framework

#INFO: This is the implementation of sounds fishy, redone by AI. i was curious if it could handle the transition from the original code to my lobbycog framework thing by itself, without help. this is its attempt.

# Assuming root is defined elsewhere or handled by the framework
# root = os.getcwd()

# Game logic comments (can keep or adapt)
# guesser> each correctly found red herring = 1 point, wrong guess = 0 points
# blue kip - 1 point for each fish wasnt flipped before them being guessed minel hamarabb kibasaztni magad
# blue kip if banked before guessed then 0 points
# if red herring guessed = 0 points
# unflipped red herring - 1 point for each fish flipped before minel tovabb bennmaradni


# --- Player Class ---
# Moved and adapted from the nested FishyCog.Player
class FishyPlayer(lobby.Player):
    def __init__(self, discorduser: discord.Member | dict | discord.User):
        super().__init__(discorduser)
        # Keep existing Fishy-specific attributes
        # self.words: list[str] = [] # This was commented out, decide if needed
        self.points = 0
        # Ensure 'points' is saved if needed persistently
        self._important.append("points") # Add 'points' to the list of attributes to save

    # The 'name' property can likely be removed, as lobby.Player has one
    # @property
    # def name(self):
    #     return client.get_user(self.userid).display_name # client is likely available via self.user in base Player

    # The 'isReady' method can be renamed to 'is_ready' to match lobby.Player protocol
    # It seems the base lobby.Player.is_ready() which just checks self.ready is sufficient here.
    # def isReady(self):
    #     return self.ready

    # Keep __str__ for displaying player points
    def __str__(self):
        # Use self.name from base Player class
        return f"{self.name} ({self.points} points)"

    # __hash__, __repr__, __eq__ can likely be removed, as lobby.Player provides these

    # toDict can likely be removed, as lobby.Player handles saving _important attributes
    # def toDict(self):
    #     return {k: v for k, v in self.__dict__.items() if k not in ("words", "inLobby", "ready")}


# --- Lobby View ---
# Adapted from the nested FishyCog.LobbyView
class FishyLobbyView(lobby.LobbyView):
    def __init__(self, lobby: FishyLobby): # Type hint with the new FishyLobby
        super().__init__(lobby)
        # You can customize/add buttons here if needed
        # The default LobbyView has join, leave, middle, ready, start buttons.
        # You can adapt the 'middlebutton' or add new ones.
        # self.children[0] is join, self.children[1] is leave, self.children[2] is middle, etc.
        # Based on your original LobbyView, the third button (index 2) was disabled and unused.
        # You can either remove it or assign a different button using customize_middle_button.

    # If the default join/leave/ready/start logic is sufficient in the base LobbyView,
    # you don't need to redefine these methods here.


# --- Admin View ---
# Adapted from the nested FishyCog.MngmntView
class FishyAdminView(lobby.AdminView):
    def __init__(self, lobby: FishyLobby): # Type hint with the new FishyLobby
        super().__init__(lobby)
        # The base AdminView has a kick button and resend button.
        # You can keep these or add more admin-specific buttons for Fishy if needed.

    # The KickPlayerDropdown logic can potentially be kept as a nested class
    # within FishyAdminView if it's only used here, or made a separate class
    # if reused elsewhere. For simplicity in refactoring, let's keep it nested for now.
    class FishyKickPlayerDropdown(discord.ui.Select):
        def __init__(self, lobby: FishyLobby): # Type hint with the new FishyLobby
            self.lobby = lobby
            # Access cog via lobby.cog
            self.cog: FishyCog = lobby.cog
            # Access players via lobby.players
            self.players = [player for player in self.lobby.players if player.userid != self.lobby.lobbyleader.id]
            optionslist = [discord.SelectOption(label=i.name, value=str(i.userid)) for i in self.players] # Value should be string for SelectOption
            optionslist.append(discord.SelectOption(label="Cancel", value="-1", emoji=emoji.emojize(":cross_mark:")))
            super().__init__(options=optionslist, placeholder="Pick a player to kick")

        async def callback(self, inter):
            result = self.values[0]
            if result != "-1":
                # Use lobby.cog.getPlayer
                tokick = self.cog.getPlayer(int(self.values[0]))
                # Use lobby.removePlayer - Note: removePlayer in base Lobby expects Interaction or TextChannel
                # The original used inter, which is an Interaction, so this should work.
                await self.lobby.removePlayer(inter, tokick)
                # The message update is handled by removePlayer in the base Lobby.
                # await self.lobby.messageid.edit(embed=self.lobby.show()) # This might be redundant

            # After kicking or canceling, update the view. Access the admin view via the original interaction if possible,
            # or refetch the message and edit its view.
            # For simplicity, let's assume editing the current interaction's view is okay if still valid.
            await inter.edit(view=FishyAdminView(self.lobby)) # Use the new FishyAdminView

    @discord.ui.button(label="Kick Player", style=discord.ButtonStyle.red, emoji=emoji.emojize(":boot:", language="alias"))
    async def kickbutton(self, button, inter):
        viewObj = discord.ui.View()
        viewObj.add_item(self.FishyKickPlayerDropdown(self.lobby)) # Use the nested dropdown
        await inter.response.edit_message(view=viewObj) # Use response.edit_message for interactions

    # The resendbutton can likely stay as is, using self.lobby
    # @discord.ui.button(label="Resend lobby message", style=discord.ButtonStyle.grey, emoji=emoji.emojize(":right_arrow_curving_left:"))
    # async def resendbutton(self, button, inter):
    #     await self.lobby.messageid.edit(embed=discord.Embed(title="The lobby you are looking for has moved", description="see below"), view=None, delete_after=30.0)
    #     lobbymessage = await inter.channel.send(embed=discord.Embed(title="Generating lobby..."))
    #     self.lobby.messageid = lobbymessage
    #     await self.lobby.messageid.edit(embed=self.lobby.show(), view=FishyLobbyView(self.lobby)) # Use the new FishyLobbyView


# --- Lobby Class ---
# Moved and adapted from the nested FishyCog.Lobby
class FishyLobby(lobby.Lobby):
    # The __init__ signature should match the base lobby.Lobby
    def __init__(self, interaction: discord.Interaction, cog: FishyCog, private=False, game: type[FishyGame] = None, minplayers: int = None, maxplayers: int = None):
        # Pass custom views and game class to the super constructor
        super().__init__(interaction, cog, private,
                         lobbyView=FishyLobbyView, # Use the new FishyLobbyView
                         adminView=FishyAdminView,   # Use the new FishyAdminView
                         game=FishyGame,         # Use the new FishyGame
                         minplayers=minplayers, # Pass minplayers if provided
                         maxplayers=maxplayers) # Pass maxplayers if provided

        # Keep existing Fishy-specific lobby attributes
        self.questions = deepcopy(self.cog.questions)
        # self.ongoing is handled by the base Lobby

        # The lobby code and adding to cog.lobbies is handled by the base Lobby

    # Override show to customize the embed display
    def show(self) -> discord.Embed:
        # You can adapt your original show method here
        name = self.lobbyleader.display_name # lobbyleader is available from the base Lobby
        EmbedVar = discord.Embed(
            # Use self.GAME_NAME, self.BASE_CMD_NAME, self.private, self.code, self.ongoing from base Lobby
            title=f"{name}'s {('Public' if not self.private else 'Private')} **{self.GAME_NAME}** Lobby" + (f" ({len(self.players)}/{self.maxplayers})" if self.maxplayers else ""),
            description=("Game already running." if self.ongoing else f"use **{self.cog.joincmd.get_mention(self.cog.TESTSERVER)} {self.code}** or click the join icon") if not self.private else f"ask the lobby leader for the code, \nthen use {self.cog.joincmd.get_mention(self.cog.TESTSERVER)} *CODE*, don't worry noone will see that.") # extra space deliberate, otherwise looks stupid

        # Add footer using the base class method
        EmbedVar = self.add_footer(EmbedVar)

        # Show players using the base class method (or override show_players if needed for custom display)
        EmbedVar = self.show_players(EmbedVar)

        return EmbedVar

    # Override readyCheck to customize the start condition
    def readyCondition(self):
        # Adapt your original readyCheck logic here
        readys = [i.is_ready() for i in self.players] # Use is_ready from base/FishyPlayer
        # uniqueIcons = len({i.icon for i in self.players}) == len(self.players) # This was commented out, decide if needed

        # The base Lobby.readyCheck handles updating the start button disabled state
        # based on this method's return value.

        # if all(readys) and len(readys)>1 and uniqueIcons: # Original logic
        if all(readys) and len(readys) >= self.minplayers: # Adapted logic
            return True
        else:
            return False

    # addPlayer, removePlayer, disband logic can likely rely on the base Lobby's implementation
    # unless there's specific Fishy-related logic to add/override.
    # async def addPlayer(self, interaction: discord.Interaction, player: FishyPlayer) -> None: ...
    # async def removePlayer(self, interaction: discord.Interaction, player: FishyPlayer) -> bool: ...
    # async def disband(self): ...

    # findLobby method can be removed, as LobbyCog handles finding lobbies.
    # async def findLobby(self, lobbyid: str) -> Optional[Lobby]: ...


# --- Game Class ---
# Keep the existing FishyGame class, ensuring it subclasses lobby.Game
class FishyGame(lobby.Game):
    # The __init__ signature should match the base lobby.Game
    def __init__(self, lobby: FishyLobby): # Type hint with the new FishyLobby
        super().__init__(lobby)
        # Access players and questions via self.lobby
        for player in self.lobby.players:
            player.statistics["Games played"] += 1 # Use statistics from base Player
        self.players: list[FishyPlayer] = self.lobby.players # Reference players from the lobby
        # self.initplayers() # This initialization can likely be removed or adapted

        self.guesser: FishyPlayer | None = None # Type hint
        # self.points = {p.userid: 0 for p in self.players} # Player objects now have their own points attribute
        self.questions = self.lobby.questions # Get questions from the lobby

    # explainers property can remain
    @property
    def explainers(self) -> list[FishyPlayer]:
        return [player for player in self.players if player != self.guesser]

    # initplayers can likely be removed if self.players is referenced from the lobby
    # def initplayers(self): ...

    # returnToLobby can be adapted to use lobby.send_lobby
    async def returnToLobby(self):
        # The message editing/sending logic is handled by lobby.send_lobby
        # Ensure ongoing is set to False and players are unready in the lobby
        self.lobby.ongoing = False
        for player in self.lobby.players:
            player.ready = False
            # player.points = 0 # Reset points for the next game if needed
        await self.lobby.send_lobby(self.channel) # Assuming self.channel is set during start

    # start method
    async def start(self, channel: discord.TextChannel):
        self.channel = channel # Store channel for later use
        # The base Game.start includes a default message, you can override it or send your own
        await super().start(channel) # Call the base start method if you want its behavior
        await self.round(channel) # Start the first round

    # round method
    async def round(self, channel: discord.TextChannel):
        self.channel = channel # Ensure channel is set

        # Rotate guesser (adapt your logic)
        if self.guesser:
            # Move current guesser to the end of the list
            self.players.append(self.guesser)
            self.players.remove(self.guesser)
        self.guesser = self.players[0] # The new guesser is the first player

        self.truth = choice(self.explainers)
        self.lobby.cog.logger.debug(f"{self.truth.name=}")
        question = choice(self.questions)
        self.questions.remove(question)

        # Send DMs to explainers
        for p in self.explainers:
            try:
                await self.lobby.cog.client.get_user(p.userid).send(embed=discord.Embed(title=f"Your are a {'True blue kipper. Tell (and twist) the truth about the following question:' if p == self.truth else 'Red Herring. Lie about the following question:'}", description=f"Question: {question['question']}\nAnswer:||{question['answer']}||", color=discord.Color.blue() if p == self.truth else discord.Color.red()))
            except discord.HTTPException as e:
                # Use the cog's logger or embedutil via lobby.cog
                await embedutil.error(self.channel, f"Could not send DM to {p.name}\n{e}", delete=15)
                self.lobby.cog.logger.error(f"{e}, {p.name}") # Use cog's logger
                continue

        # Send game message with dropdown
        viewObj = discord.ui.View(timeout=None)
        viewObj.add_item(GuesserDropdown(self)) # GuesserDropdown needs to accept the game instance
        await self.channel.send(embed=discord.Embed(title=f"{self.guesser.name} is guessing", description=f"Question: {question['question']}"), view=viewObj)


# --- Game UI Components ---
# Keep as separate classes, they interact with the FishyGame instance

class GuesserDropdown(discord.ui.Select):
    def __init__(self, game: FishyGame): # Type hint with FishyGame
        super().__init__()
        self.game: FishyGame = game
        self.placeholder = "Who is a lying red herring?"
        # Access explainers from the game instance
        self.options = [discord.SelectOption(label=player.name, value=str(player.userid)) for player in self.game.explainers] + [discord.SelectOption(label="Take points & end turn", value="0", emoji=emoji.emojize(":outbox_tray:"))]

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id == self.game.guesser.userid:
            if self.values[0] == "0":
                # Update player points directly on the Player object
                guesser_points = len(self.game.explainers) - len(self.options) + 1
                self.game.guesser.points += guesser_points
                # Update statistics using the Player object's statistics attribute
                self.game.guesser.statistics["Times banked points"] += 1

                embedVar = discord.Embed(title="Nice!", description=f"{self.game.guesser.name} banked their points.", color=discord.Color.green())
                embedVar.add_field(name="Guesser points", value=f"{guesser_points}")
                embedVar.add_field(name="Blue kip points", value=f"{0}")
                embedVar.add_field(name="Not revealed Red herring points", value=f"{len(self.game.explainers) - len(self.options) + 1}")

                for player_option in self.options:
                    if player_option.value != "0":
                         # Find the actual player object
                        herring_player = next((p for p in self.game.players if str(p.userid) == player_option.value), None)
                        if herring_player:
                            herring_player.points += guesser_points
                            herring_player.statistics["Guessers fooled"] += 1

                # Save players via the game instance
                self.game.savePlayers()

                await interaction.response.edit_message(embed=embedVar, view=NextButton(self.game)) # Use interaction.response.edit_message
            else:
                chosen_userid = int(self.values[0])
                chosen: FishyPlayer | None = next((p for p in self.game.players if p.userid == chosen_userid), None) # Find the chosen player object

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

                    if self.game.truth: # Ensure truth exists
                         self.game.truth.statistics["Guessers fooled"] += 1
                         self.game.truth.points += blue_kip_points

                    self.game.guesser.statistics["Times got fooled"] += 1 # Update guesser stats

                    await interaction.response.edit_message(embed=embedVar, view=NextButton(self.game)) # Use interaction.response.edit_message
                    self.game.savePlayers()
                else:
                    # Remove the chosen player from the options
                    self.options = [option for option in self.options if int(option.value) != chosen_userid]
                    if len(self.options) == 2: # Only "Take points" and the last herring remain
                        embedVar = discord.Embed(title=f"Every red herring revealed!",
                                                 color=discord.Color.green())
                        guesser_points = len(self.game.explainers) - 1
                        embedVar.add_field(name="Guesser points", value=f"{guesser_points}")
                        self.game.guesser.points += guesser_points
                        self.game.guesser.statistics["Cleared all herrings"] += 1
                        self.game.savePlayers()
                        await interaction.response.edit_message(embed=embedVar, view=NextButton(self.game)) # Use interaction.response.edit_message
                    else:
                        embedVar = discord.Embed(title=f"Nice! {chosen.name} is a red herring!",
                                                 description=f"Do you wish to continue?",
                                                 color=discord.Color.red())
                        await interaction.response.edit_message(embed=embedVar, view=self.view) # Use interaction.response.edit_message
                        self.game.guesser.statistics["Red herrings revealed"] += 1

        else:
            await embedutil.error(interaction, "It is not your turn to guess!", ephemeral=True) # Use ephemeral for errors


class NextButton(discord.ui.View):
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


# --- Main Cog ---
# Adapted from the original FishyCog
class FishyCog(lobby.LobbyCog):
    # Remove global logger and client, access via self.logger and self.client
    def __init__(self, client1: discord.Client):
        # Call the superclass __init__ with relevant parameters
        super().__init__(client1,
                         GAME_NAME="Sounds Fishy",
                         BASE_CMD_NAME="fishyai", # Keep the base command name
                         playerclass=FishyPlayer, # Use the new FishyPlayer class
                         lobbyclass=FishyLobby,   # Use the new FishyLobby class
                         gameclass=FishyGame,     # Use the new FishyGame class
                         minplayers=3) # Set minimum players

        # Access logger via self.logger
        self.logger.debug("Fishy cog loaded")

        # User and lobbies management is handled by the base LobbyCog
        # self.users: dict[int, FishyCog.Player] = {} # Remove
        # self.lobbies: dict[int, FishyCog.Lobby] = {} # Remove
        # File handling is done by the base LobbyCog
        # os.makedirs(r"./data", exist_ok=True) # Remove
        # try: ... except ... # Remove file loading logic

        from data import fishyquestions
        self.questions = fishyquestions.questions # Keep game-specific data

        # --- Command Implementations ---
        # The base LobbyCog automatically creates slash commands for stats, help, join, leave, start.
        # You can remove your manual command definitions and adapt your methods
        # to override the base methods if needed for custom behavior.

        # @discord.slash_command(description="Commands for the games") # Remove
        # async def fishy(self, interaction): pass # Remove

        # @fishy.subcommand(name="stats", description="Shows your stats across all the games you´ve played.")
        # async def showstats(self, ctx: discord.Interaction, user: discord.User=discord.SlashOption(name="user", description="See someone else´s profile.", required=False, default=None)):
        # The base LobbyCog has a showstats method. You can override it if you need
        # custom display logic beyond the base implementation which shows player.statistics.
        # Your current showstats uses player.stats, which should be player.statistics in the new Player class.
        # Adapt the embed creation if necessary.
        # await super().showstats(ctx, user) # Call the base method if you just need the default display

        # @fishy.subcommand(name="help", description="Shows the help manual to this game and the bot.")
        # async def showhelp(self, ctx: discord.Interaction):
        # The base LobbyCog has a help system. You can integrate your help text
        # and categories with the base system.
        # Assign your help text to self.rules, self.credits, and potentially add
        # custom HelpCategory instances using self.add_help_category().

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

        # The command help text can be added as a HelpCategory or rely on automatic docstring inclusion
        # self.add_help_category(lobby.HelpCategory(label="Commands", description="Gives help about the game commands.", emoji=emoji.emojize(":paperclip:"), helptext=f"""..."""))


        # The nested View classes are now top-level classes
        # class LobbyView(discord.ui.View): ... # Removed, now FishyLobbyView
        # class KickPlayerDropdown(discord.ui.Select): ... # Removed, now nested in FishyAdminView
        # class MngmntView(discord.ui.View): ... # Removed, now FishyAdminView

        # @fishy.subcommand(name="start", description="Makes a lobby for a Sounds Fishy game.")
        # async def makeLobby(self, ctx:discord.Interaction, private=discord.SlashOption(name="private", description="Do you wish to create a public lobby or a private one",required=False, default="Public", choices=("Public","Private"))):
        # This command is automatically created by LobbyCog. The logic for creating the lobby
        # is handled by the base LobbyCog's makeLobby method, which will instantiate
        # your custom FishyLobby. You don't need to override this unless you need
        # very specific pre-lobby creation logic.

        # @fishy.subcommand(name="join", description="Join an existing lobby.")
        # async def joinlobby(self, ctx: discord.Interaction, lobbyid:str =discord.SlashOption(name="lobbyid", description="A lobby´s identification e.g. ABCD", required=True)):
        # This command is automatically created by LobbyCog. The logic for joining a lobby
        # is handled by the base LobbyCog's joinlobby method, which calls the Lobby's addPlayer.

        # @fishy.subcommand(name="leave", description="Leave the lobby you are currently in.")
        # async def leavelobby(self, ctx: discord.Interaction):
        # This command is automatically created by LobbyCog. The logic for leaving a lobby
        # is handled by the base LobbyCog's leavelobby method, which calls the Lobby's removePlayer.

        # The getPlayer and savePlayers methods are provided by the base LobbyCog
        # def getPlayer(self, dcUser: int | discord.Member | "FishyCog.ClovecePlayer"): ... # Remove
        # def savePlayers(self): ... # Remove


# --- Setup Function ---
def setup(client):
    # Remove global client assignment here
    client.add_cog(FishyCog(client))