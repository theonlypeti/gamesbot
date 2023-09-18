import nextcord as discord
from nextcord.ext import commands
from utils.mentionCommand import mentionCommand
import asyncio
from functools import wraps
from typing import Optional, Iterable, Callable

TESTSERVER = (860527626100015154,)


class Testing(commands.Cog):
    def __init__(self, client):
        global logger
        logger = client.logger.getChild(f"{__name__}Logger")
        self.client: discord.Client = client

    @discord.slash_command(name="testing", guild_ids=TESTSERVER)
    async def testinggrp(self, interaction: discord.Interaction):
        pass

    @testinggrp.subcommand(name="one")
    async def onetest(self, interaction: discord.Interaction):
        # await interaction.send("hi")
        pass

    @testinggrp.subcommand(name="two")
    async def onetesttwo(self, interaction: discord.Interaction):
        await interaction.send("hi")

    @onetest.subcommand(name="three")
    async def threetest(self, interaction: discord.Interaction):
        await interaction.send("hi")

    @discord.slash_command(name="run", description="For running python code", guild_ids=TESTSERVER)
    async def run(self, ctx: discord.Interaction, command):
        if "@" in command and ctx.user.id != 617840759466360842:
            await ctx.send("oi oi oi we pinging or what?")
            return
        if any((word in command for word in ("open(", "os.", "eval(", "exec("))) and ctx.user.id != 617840759466360842:
            await ctx.send("oi oi oi we hackin or what?")
            return
        elif "redditapi" in command and ctx.user.id != 617840759466360842:
            await ctx.send("Lol no sorry not risking anyone else doing stuff with MY reddit account xDDD")
            return
        try:
            await ctx.response.defer()
            a = eval(command)
            await ctx.send(a)
        except Exception as a:
            await ctx.send(f"{a}")



    def lobby(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        *,
        name_localizations = None,
        description_localizations= None,
        guild_ids: Optional[Iterable[int]] = None,
        dm_permission: Optional[bool] = None,
        default_member_permissions = None,
        force_global: bool = False,
    ):

        @wraps(func)
        def decorator(func: Callable):
            result = discord.slash_command(
                name=name,
                name_localizations=name_localizations,
                description=description or "Sanyi",
                description_localizations=description_localizations,
                guild_ids=guild_ids,
                dm_permission=dm_permission,
                default_member_permissions=default_member_permissions,
                force_global=force_global,
            )(func)
            self.client._application_commands_to_add.add(result)
            return result

        return decorator

# @lobby(name="sanyi")
# async def makelobby(interaction: discord.Interaction):
#     await interaction.send("hi")


def setup(client):
    client.add_cog(Testing(client))

