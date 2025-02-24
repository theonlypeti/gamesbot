from datetime import datetime
from nextcord import Embed, Interaction, TextChannel, Color, Message, Member


async def error(interaction: Interaction|TextChannel, txt: str, delete = 5.0, ephemeral=True) -> Message:
    if isinstance(interaction, Interaction):
        return await interaction.send(embed=Embed(description=txt, color=Color.red()), ephemeral=ephemeral, delete_after=delete)
    else:
        return await interaction.send(embed=Embed(description=txt, color=Color.red()), delete_after=delete)


async def success(interaction: Interaction | TextChannel, txt: str, delete=5.0, ephemeral=True) -> Message:
    if isinstance(interaction, Interaction):
        return await interaction.send(embed=Embed(description=txt, color=Color.green()), ephemeral=ephemeral, delete_after=delete)
    else:
        return await interaction.send(embed=Embed(description=txt, color=Color.green()), delete_after=delete)


def setuser(embed: Embed, user: Member) -> Embed:
    """Set the footer text to the username, user avatar and set the color to user color"""
    embed.set_footer(text=f"{user.name}", icon_url=user.display_avatar.url)
    embed.timestamp = datetime.now()
    try:
        embed.colour = user.color
    except AttributeError:  # if user is not a member, so like DMchannel or user app in unknown guild
        pass
    return embed

