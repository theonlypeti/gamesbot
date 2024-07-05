from nextcord import Interaction, Permissions


def can_i(interaction: Interaction) -> Permissions:
    return interaction.channel.permissions_for(interaction.guild.me)

