import nextcord as discord
from nextcord.ext import commands

# lol abandoned project

amounts = {
  0: "Absent",
  10: "Negligible",
  20: "Scarce",
  30: "Limited",
  40: "Below average",
  50: "Moderate",
  60: "Common",
  70: "Substantial",
  80: "Plentiful",
  90: "Abundant"
}

disrepair = {100: 'Fully operational',
             90: 'Very minor issues',
             80: 'Minor issues',
             70: 'Noticeable issues affecting performance',
             60: 'Significant problems impacting functionality',
             50: 'Moderately impaired, partially operational',
             40: 'Major issues, barely functional',
             30: 'Critical damage, barely operational',
             20: 'Severe damage, close to failure',
             10: 'Failure imminent',
             0: 'Irreparable damage (offline)'
            }



class SpaceshipCog(commands.Cog):
    def __init__(self, client):
        self.logger = client.logger.getChild(f"{self.__module__}")
        self.client = client

    # @discord.slash_command()
    # async def spaceshipcmd(self, interaction: discord.Interaction):
    #     await interaction.send("Hi")


def setup(client):
    client.add_cog(SpaceshipCog(client))
