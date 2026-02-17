#linecount: \utils\lobbyutil\
from __future__ import annotations
import os
from utils.lobbyutil.Inventory import Inventory
import nextcord as discord
import emoji
from random import choice
from utils.lobbyutil.lobbycog import LobbyCog, Game, Lobby, Player, LobbyView, PlayerProt, HelpCategory
from utils import embedutil

root = os.getcwd()


class WikiGameCog(LobbyCog):
    def __init__(self, client: discord.Client):
        super().__init__(client, "Two of these people are lying", BASE_CMD_NAME="wikigame", minplayers=3, playerclass=WordsPlayer, lobbyclass=WordsLobby, gameclass=WikiGame)
        self.client = client

        self.rules = """Before starting the game, everyone picks a few interesting wikipedia articles that are less known.
        The wikipedia's [__Random article__](https://en.wikipedia.org/wiki/Special:Random) button may be used but the articles may be less interesting.
         
        Each turn an article is picked, from the pool of everyone's submitted articles.
        Also each turn a guesser is chosen, whose job will be to find the one player telling the truth.   
         
        Only the person who submitted the article will be able to tell the truth about the chosen article, as they
        have chosen it, and read about it, so they can describe it to the guesser.
        The other players however do *not* know anything about the article and will have to convince the guesser
        that they do, by coming up with plausible sounding explanations, stories and facts about the chosen word/article.
        
        After the guesser has listened to everyone's attempts at convincing them of their truth, the guesser has
        to pick a player who they think is telling the truth and is the owner of the article.
        If they guess correctly, they are awarded a point. Otherwise the person who fooled the guesser gets a point."""

        self.add_help_category(HelpCategory(
            label="House rules", emoji=emoji.emojize(":house:"),
            description="Additional guidelines for the game",
            helptext="""
        Try to pick an article whose title is ambiguous. The wikipedia's random button will often pick very specific articles, eg. train stations, which are obvious from the name alone.
        Try to pick interesting articles, rather than stubs, or some throwaway filler articles. **Historical events; obscure people/inventions/locations/technical terms are all good article topics**.
            
        Optimally the players may **not re-read their article**'s wiki pages when telling about it, or between rounds, so they don't just recite
        the whole article word for word, providing too much information to the guesser.
        
        The guesser should **leave the explainers some time to read the current round's word**, think about it, and come up with a possible explanation. 
        Interrogating them right away will leave them stuttering, coming up with bad answers, depending on one's deception skill level.
        
        The guesser could set up a clock timer or better yet **do only two rounds (without the time pressure) of questioning** towards the players. 
        This levels the playing field for the explainers, not having to come up with infinitely many details and explanations."""
        ))

        self.credits = """The game is based on the web game show **Two of these people are lying** presented on YouTube by
                 The Technical Difficulties
                 https://www.techdif.co.uk/
                 https://www.youtube.com/playlist?list=PLrkYtXgEpu5QXFgFJO8SxTMa24wv7b40X
                 Bot and game adaptation created by @theonlypeti
                 https://github.com/theonlypeti"""


class WordsPlayer(Player):
    def __init__(self, user: discord.User):
        super().__init__(user)
        self.words = []

    def __str__(self):
        return f"{self.name} ({len(self.words)} words)"

    async def can_ready(self, interaction: discord.Interaction, lobby: WordsLobby) -> bool:
        if len(self.words) >= lobby.minwords or self.ready:
            return True
        else:
            await embedutil.error(interaction, f"You need to submit at least {lobby.minwords} words to be ready.")
            return False


class WordsLobby(Lobby):
    def __init__(self, interaction, cog, private, game, minplayers, maxplayers):
        super().__init__(interaction, cog, private,
                         lobbyView=WikiLobbyButtons,
                         game=game,
                         minplayers=minplayers,
                         maxplayers=maxplayers)
        self.players: list[WordsPlayer] = self.players  # this is just to override the typehint of the attr
        self.words = []
        self.minwords = 2

    @property
    def allwords(self):
        return sum([p.words for p in self.players], [])


class WikiLobbyButtons(LobbyView):
    def __init__(self, lobby):
        self.middlebutton = Addwordsbutton
        super().__init__(lobby)


class Addwordsbutton(discord.ui.Button):
    def __init__(self, lobby: WordsLobby):
        self.lobby = lobby
        super().__init__(style=discord.ButtonStyle.primary, emoji=emoji.emojize(":plus:"))

    async def callback(self, interaction: discord.Interaction):
        """Add words"""
        user: WordsPlayer = self.lobby.getPlayer(interaction.user)
        inv = Inventory(user.words, on_update=self.lobby.readyCheck, inv_to_check=self.lobby.allwords)
        inv.lobby = self.lobby
        await inv.render(interaction, ephemeral=True)


class WikiGame(Game):
    def __init__(self, lobby: WordsLobby):
        self.lobby = lobby
        for player in self.lobby.players:
            player.statistics["Games played"] += 1
        self.players: list[WordsPlayer] = None
        self.initplayers()
        self.guesser: WordsPlayer = None
        self.points = {p.userid: 0 for p in self.players}

        self.truth = None
        self.guesser = None
        self.word = None


    @property
    def allwords(self):
        return sum([p.words for p in self.players], [])

    @property
    def words(self):
        # return self.allwords - self.guesser.words //no operand - for list
        # return filter(lambda word: word not in self.guesser.words, self.allwords) //filter has no len
        # return set(allwords).difference(set(self.guesser.words)) //set cant be subscripted
        return [word for word in self.allwords if word not in self.guesser.words]

    @property
    def explainers(self) -> list[WordsPlayer]:
        return [player for player in self.players if player != self.guesser]

    def initplayers(self):
        if not self.players:
            self.players = self.lobby.players
            # self.players.insert(0, WordsPlayer(self.lobby.cog.client.user)) #TODO remove
            # self.players[0].words = ["dummy", "dummy2"]

    async def returnToLobby(self, interaction: discord.Interaction):
        for player in self.lobby.players:
            player.ready = False
        await self.lobby.send_lobby(interaction=interaction)

    async def start(self, channel: discord.TextChannel):
        await self.round(channel)
        ...

    async def round(self, channel: discord.TextChannel):
        self.channel = channel
        # self.initplayers()
        if not all(player.words for player in self.players):
            await channel.send(content="Someone has ran out of words. Find and submit new articles to continue the game.", view=self.ReturnButtonView(self))
            return
        self.guesser = self.players.pop()
        self.players.insert(0, self.guesser)  #TODO this is stupid tbh
        self.truth = choice(self.explainers)
        self.word = choice(self.truth.words)
        self.truth.words.remove(self.word)
        # for player in self.explainers:
        #     player // for dming them or showing an ephemeral ws to them
        viewObj = discord.ui.View(timeout=None)
        viewObj.add_item(GuesserDropdown(self))
        await self.channel.send(embed=discord.Embed(title=f"{self.guesser.name} is guessing", description=f"The word is ||{self.word}||"), view=viewObj)


class GuesserDropdown(discord.ui.Select):
    def __init__(self, game):
        super().__init__()
        self.game: WikiGame = game
        self.placeholder = "Who tells the truth?"
        self.options = [discord.SelectOption(label=player.name, value=f"{player.userid}") for player in self.game.explainers]

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id == self.game.guesser.userid:
            chosen: PlayerProt = self.game.getPlayer(int(self.values[0]))
            if chosen == self.game.truth:
                embedVar = discord.Embed(title="Correct!", description=f"{self.game.truth.name} was telling the truth", color=discord.Color.green())
                self.game.points[self.game.guesser.userid] += 1
                self.game.guesser.statistics["Correct guesses"] += 1
            else:
                embedVar = discord.Embed(title=f"{chosen.name} is incorrect!",
                                         description=f"||{self.game.truth.name} was telling the truth||",
                                         color=discord.Color.red())
                self.game.points[chosen.userid] += 1
                self.game.guesser.statistics["Incorrect guesses"] += 1
                chosen.statistics["Fooled someone"] += 1
            for k, v in self.game.points.items():
                embedVar.add_field(name=self.game.getPlayer(k).name, value=str(v))
            await interaction.edit(embed=embedVar, view=self.NextButton(self.game))
        else:
            await embedutil.error(interaction, "It is not your turn to guess!")
        self.game.lobby.cog.savePlayers()

    class NextButton(discord.ui.View):
        def __init__(self, game: WikiGame):
            super().__init__(timeout=None)
            self.game = game

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            return interaction.user.id == self.game.guesser.userid

        @discord.ui.button(label="Next round", emoji=emoji.emojize(":right_arrow:"), style=discord.ButtonStyle.green)
        async def nextbutton(self, button, interaction: discord.Interaction):
            await interaction.message.delete()
            await self.game.round(interaction.channel)

        @discord.ui.button(label="Back to Lobby")
        async def lobby(self, button, interaction: discord.Interaction):
            await interaction.message.delete()
            await self.game.returnToLobby(interaction)


def setup(client):
    client.add_cog(WikiGameCog(client))
