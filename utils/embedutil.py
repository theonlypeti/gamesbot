import discord
from nextcord import Embed, Interaction, TextChannel, Color, Message


async def error(interaction: Interaction|TextChannel, txt: str, delete = 5.0) -> Message:
    if isinstance(interaction, Interaction):
        return await interaction.send(embed=Embed(description=txt,color=Color.red()),ephemeral=True,delete_after=delete)
    else:
        return await interaction.send(embed=Embed(description=txt,color=Color.red()),delete_after=delete)


async def success(interaction: Interaction | TextChannel, txt: str, delete = 5.0) -> Message:
    if isinstance(interaction, Interaction):
        return await interaction.send(embed=Embed(description=txt, color=Color.green()), ephemeral=True,delete_after=delete)
    else:
        return await interaction.send(embed=Embed(description=txt, color=Color.green()),delete_after=delete)

