import os
import nextcord as discord
import utils.lobbyutil.lobbycog as lobby
import utils.lobbyutil.teamutil as teams

root = os.getcwd()


class TeamGameCog(lobby.LobbyCog):
    """A demonstrative cog showing how to easily create a team-based game.
    This is not meant to be a usable game, just an example of how to use the team-based lobby and player classes."""
    def __init__(self, client: discord.Client):
        super().__init__(client, "Team up!",
                         BASE_CMD_NAME="teamup",
                         playerclass=teams.TeamPlayer,
                         lobbyclass=teams.TeamLobby,
                         TESTSERVER_ID=860527626100015154)


def setup(client):
    client.add_cog(TeamGameCog(client))


