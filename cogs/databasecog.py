import json
import os
from collections import defaultdict
import nextcord as discord
from nextcord.ext import commands


class DatabaseCog(commands.Cog): #how to load and write files with data in a bot
    def __init__(self, client, baselogger):
        global logger
        logger = baselogger.getChild(f"{__name__}Logger")
        self.client: discord.Client = client
        os.makedirs(r".\data", exist_ok=True)
        try:
            with open(r".\data\howmany.json", "r") as file:
                self.db = defaultdict(int) #olyan mint a dict csak amikor nem talal benne adatot akkor nem errorozik hanem letrehoz benne egy default valuet
                self.db.update(json.load(file, parse_int=int))
        except IOError:
            with open(r".\data\howmany.json", "w") as file:
                json.dump({}, file, indent=4)
                self.db = defaultdict(int)

    @discord.slash_command()
    async def howmany(self, interaction: discord.Interaction):
        self.db[str(interaction.user.id)] += 1  # add one use to the current user in the db
        ldb = sorted(self.db.items(), key=lambda x: x[1])[:5]  # sort the first 5 users with the highest values
        logger.debug(ldb)  # see for yourself, it is now a list of tuples (id, count)
        embedVar = discord.Embed(
            title="How many times have people used this command:"
        )
        for record in ldb:
            user_id = int(record[0])
            count = record[1]
            embedVar.add_field(
                name=self.client.get_user(user_id).name,
                value=count
            )

        await interaction.send(embed=embedVar) #send the msg
        with open(r".\data\howmany.json", "w") as file: #save the new data
            json.dump(self.db, file, indent=4)


def setup(client, baselogger):
    client.add_cog(DatabaseCog(client, baselogger))

