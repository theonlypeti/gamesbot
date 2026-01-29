import nextcord as discord
import utils.lobbyutil.lobbycog as lobby

class MinimumCog(lobby.LobbyCog): # a minimal viable cog example
    def __init__(self, client: discord.Client):
        super().__init__(client, "Minimum Viable Product")

def setup(client):
    client.add_cog(MinimumCog(client))
