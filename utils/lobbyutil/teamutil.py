from __future__ import annotations
import random
from copy import deepcopy
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
        await self.lobby.readyCheck()


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
        await inter.edit(view=None, content="Joined team " + team.name, delete_after=5.0)  # TODO make this a proper embed


class TeamLobby(Lobby):
    teams_info_text = "Pick a team"

    def __init__(self, interaction: discord.Interaction, messageid: discord.Message, cog: LobbyCog, private=False, adminView: discord.ui.View = None, game: type[Game] = None, minplayers: int = None, maxplayers: int = None, teamclass: type[Team] = None):
        self.cog = cog
        self.teamclass = teamclass or Team
        TeamView = type('TeamView', (LobbyView,), {'middlebutton': TeamsButton})  # type: type[LobbyView] #this is so hacky

        TeamView.middlebutton.teams_info_text = self.teams_info_text  # needed cuz it would overwrite for other games as well #TODO this should be better

        self.init_teams()
        super().__init__(interaction, messageid, cog, private, lobbyView=TeamView, adminView=adminView, game=game, minplayers=minplayers, maxplayers=maxplayers)

    def init_teams(self):
        """Limit teams to the 4 main colors and remove the rest."""
        self.teams = sorted([self.teamclass(col) for col in Colored.Colored.list().values()], key=lambda t: t.color.emoji_square)
        self.teams = deepcopy(self.teams[2:4] + self.teams[5:7])  #TODO just call/init them by colors, also somehow option to create more and or custom teams

    def readyCondition(self):
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

                # if len(team.players) > 1:
                #     EmbedVar.set_field_at(i-n-1, name=EmbedVar.fields[i-n-1].name + " (guesser)", value=EmbedVar.fields[i-n-1].value, inline=False)
                #     EmbedVar.set_field_at(len(EmbedVar.fields)-1, name=EmbedVar.fields[-1].name + " (spymaster)", value=EmbedVar.fields[-1].value, inline=False)

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
        super().__init__(Object(id=random.randrange(100_000_000, 999_999_999))) #todo this will not work
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