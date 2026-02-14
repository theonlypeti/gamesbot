from __future__ import annotations
import random
import emoji
import nextcord as discord
from nextcord import Object
import utils.embedutil
from utils import Colored
from utils.lobbyutil.lobbycog import LobbyCog, Player, Lobby, Game, LobbyView, PlayerProt


class Team:
    def __init__(self, color: Colored.ColorGroup):
        self.players: list[PlayerProt] = []
        self.color: Colored.ColorGroup = color
        self.minplayers: int = 2
        self.eliminated = False
        #self.points = 0
        #self.words = []

    @property
    def name(self):
        return self.color.name

    def join(self, player: PlayerProt):
        if player.team:
            player.team.remove(player)
        self.players.append(player)
        player.team = self

    def remove(self, player: PlayerProt):
        self.players.remove(player)
        player.team = None

    def __bool__(self):
        return bool(self.players)


class TeamsButton(discord.ui.Button):
    teams_info_text = "Pick a team below"

    def __init__(self, lobby: TeamLobby):
        self.cog = lobby.cog
        self.lobby = lobby
        super().__init__(style=discord.ButtonStyle.grey, emoji=emoji.emojize(":running_shirt:", language="alias"), disabled=False, custom_id=__file__ + "lobbymiddle")

    async def callback(self, interaction: discord.Interaction):
        """Select team"""
        player = self.cog.getPlayer(interaction.user)
        if player not in self.lobby.players:
            await utils.embedutil.error(interaction, "You are not in this lobby.")
            return
        if player.ready:
            await utils.embedutil.error(interaction, "You cannot change teams while ready.")
            return

        viewObj = discord.ui.View()
        viewObj.add_item(TeamSelector(self.lobby))
        await interaction.send(
            content=self.teams_info_text,
            view=viewObj, ephemeral=True)
        await self.lobby.readyCheck() # is this needed? nothing changes on this button press


class TeamSelector(discord.ui.Select):
    def __init__(self, lobby: TeamLobby):
        self.lobby = lobby
        self.cog = lobby.cog
        self.teams = self.lobby.teams
        self.opts = [discord.SelectOption(label=team.name, value=str(n), emoji=team.color.emoji_square) for n, team in enumerate(self.teams)]
        super().__init__(placeholder="Pick a team", options=self.opts)

    async def callback(self, inter: discord.Interaction):
        team = self.teams[int(self.values[0])]
        player = self.cog.getPlayer(inter.user)
        team.join(player)
        await self.lobby.readyCheck()
        embedVar = discord.Embed(description=f"You have joined team {team.name}", color=team.color.dccolor)
        await inter.edit(view=None, content=None, embed=embedVar, delete_after=5.0)


class TeamLobby(Lobby): #TODO add randomize teams button //but i dont know how many teams to randomize into, only if i have minplayers and maxplayers for teams
    """Lobby with extended team support. Players must join a team to ready up. Be aware empty teams are not removed on game start!

    New notable attributes:
    :ivar teamclass: The class used to create teams, defaults to Team
    :ivar teamcolors: list[str]: List of color strings, corresponding to Colored class colors, used to create teams, defaults to ["red", "blue", "green", "yellow"]
    :ivar teams: List of teams in the lobby, created from teamcolors and teamclass using self.init_teams()
    """
    teams_info_text = "Pick a team"

    def __init__(self, interaction: discord.Interaction, cog: LobbyCog, private=False, adminView: discord.ui.View = None, game: type[Game] = None, minplayers: int = None, maxplayers: int = None, teamclass: type[Team] = None):
        self.cog = cog
        self.teamclass = teamclass or Team
        self.teamcolors = ["red", "blue", "green", "yellow"] #Colored.Colored.list() to get all available color names
        self.teams: list[Team] = self.init_teams(self.teamcolors)

        TeamView = type('TeamView', (LobbyView,), {'middlebutton': TeamsButton})  # type: type[LobbyView] #this is so hacky
        TeamView.middlebutton.teams_info_text = self.teams_info_text  # needed cuz it would overwrite for other games as well #TODO this should be better

        super().__init__(interaction, cog, private, lobbyView=TeamView, adminView=adminView, game=game, minplayers=minplayers, maxplayers=maxplayers)

    def init_teams(self, teamcolors: list[str]) -> list[Team]:
        """Limit teams to the 4 main colors and remove the rest."""
        teams = []
        for c in teamcolors:
            col = Colored.Colored.get_color(c)
            team = self.teamclass(col)
            teams.append(team)
        return teams
        #TODO document this how to manage Teams

    def readyCondition(self):
        """Teams specific check. Check if all players are ready, there are enough players, and each team has enough players."""
        readys = [i.is_ready() for i in self.players]
        teams = [t for t in self.teams if t]  # remove empty teams
        return (all(readys)  # everyone is ready
                and len(self.players) >= self.minplayers  # enough players
                and all([len(t.players) >= t.minplayers for t in teams])  # enough players in each team
                and len(teams) >= 2)  # enough teams #TODO add minteams?

    def show_players(self, embedVar: discord.Embed) -> discord.Embed:
        i = 1
        for team in self.teams:
            if team:
                for n, player in enumerate(team.players, start=1):
                    embedVar.add_field(name=f"{i}. {player}", value="Ready? " + (
                        emoji.emojize(":cross_mark:"), emoji.emojize(":check_mark_button:"))[bool(player.ready)],
                                       inline=False)
                    i += 1

        for n, player in enumerate(filter(lambda p: not p.team, self.players), start=1):
            embedVar.add_field(name=f"{i}. {player}", value="Ready? " + (
            emoji.emojize(":cross_mark:"), emoji.emojize(":check_mark_button:"))[bool(player.ready)], inline=False)
            i += 1

        while i - 1 < self.minplayers:
            embedVar.add_field(name="[Empty]", value=f"Ready? {emoji.emojize(':cross_mark:')}", inline=False)
            i += 1
        return embedVar


class TeamPlayer(Player):
    """
    Notable new attributes:
    :ivar team: The team the player is in
    """
    def __init__(self, discorduser):
        super().__init__(discorduser)
        self.team: Team | None = None

    def is_ready(self) -> bool:
        """for internal use, for ux with feedback use can_ready()"""
        return self.ready and self.team

    async def can_ready(self, interaction: discord.Interaction, lobby: Lobby) -> bool:  # TODO why is can_ready in Player?
        """Check if the player can ready up, e.g. has enough words, has a team, etc.
        :param interaction:
        :param lobby:
        """
        if self.team or self.ready:  # if has a team, or wants to unready even without a team (should not be possible)
            return True
        else:
            await utils.embedutil.error(interaction, "You may not ready without a team assigned")
            return False

    def __str__(self):
        return f"{self.team.color.emoji_square if self.team else emoji.emojize(':question_mark:', language='alias')} {self.name} {'(no team)' if not self.team else ''}"


class MockPlayer(TeamPlayer):
    def __init__(self, name: str, cog):
        super().__init__(Object(id=random.randrange(100_000_000, 999_999_999))) #todo this will not work. why?
        self._name = name
        self.cog = cog
        cog.users.update({self.userid: self})
        self.ready = True

    @property
    def name(self):
        return self._name

    def __eq__(self, other):
        return other.userid == self.userid

    def tojson(self):
        self.cog.logger.warning("MockPlayer.toJson() accessed, returning empty json!")
        return "{}"

    @property
    def user(self):
        self.cog.logger.warning("MockPlayer.user accessed, returning bot client's profile! (please don't DM haha)")
        return self.cog.client.user