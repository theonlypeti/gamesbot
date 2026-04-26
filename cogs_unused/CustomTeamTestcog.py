from utils.lobbyutil import lobbycog as lobby
from utils.lobbyutil.Colored import Colored
from utils.lobbyutil.teamutil import TeamLobby, TeamPlayer, Team

class CustomTeamTestCog(lobby.LobbyCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, GAME_NAME="Animals",
                         lobbyclass=MyTeamLobby,
                         playerclass=MyTeamPlayer,
                         TESTSERVER_ID = 860527626100015154 , **kwargs)

class MyTeamLobby(TeamLobby):
    def __init__(self, *args, **kwargs):
        self.teamcolors = ["purple"] # change or remove if you dont want default colorteams
        self.maxteams = 2
        super().__init__(*args, **kwargs)

    def init_teams(self, teamcolors: list[str]):
        teams = super().init_teams(teamcolors) #remove if you dont want default colorteams

        teams += [
            Team("Team Cats", emoji="🐱", color=Colored.yellow),
            Team("Team Dogs", emoji="🐶", color=Colored.brown)
            # Horde/Alliance/Forsaken
            # America/Europe/Asia
            # Defenders / Attackers
            # Seekers / Hiders
        ]

        return teams

class MyTeamPlayer(TeamPlayer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"{self.team_emoji} {self.name} ({self.team_name})"


def setup(client):
    client.add_cog(CustomTeamTestCog(client))
