from __future__ import annotations
import os
import nextcord as discord
import utils.lobbyutil.lobbycog as lobby
import utils.lobbyutil.teamutil as teams

root = os.getcwd()


class TeamGameCog(lobby.LobbyCog):
    def __init__(self, client: discord.Client):
        super().__init__(client, "Team up!",
                         BASE_CMD_NAME="teamup",
                         playerclass=teams.TeamPlayer,
                         lobbyclass=teams.TeamLobby,
                         TESTSERVER_ID=860527626100015154)
        self.logger = client.logger.getChild(f"{self.__module__}")
        self.client = client


def setup(client):
    client.add_cog(TeamGameCog(client))


