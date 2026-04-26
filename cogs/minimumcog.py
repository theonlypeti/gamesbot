import utils.lobbyutil.lobbycog as lobby

class MinimumCog(lobby.LobbyCog): # a minimal viable cog example, showing how few lines are required to create a fully fledged game lobby cog.
    def __init__(self, client):
        super().__init__(client, "Minimum Viable Product")

def setup(client):
    client.add_cog(MinimumCog(client))
