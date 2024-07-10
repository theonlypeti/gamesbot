from __future__ import annotations
import logging
import os
import random
import string
from abc import ABC, abstractmethod
from datetime import datetime, date
from functools import partial
from textwrap import TextWrapper
from nextcord import Object
from typing import Optional, Callable, Coroutine, Literal, Protocol
import nextcord as discord
import nextcord.errors
from nextcord.ext import commands
import json
import emoji
from collections import defaultdict
from utils.antimakkcen import antimakkcen
from utils import embedutil


root = os.getcwd()

# TODO localisations?
# TODO on_message_delete if it was a lobby message, remove the lobby, or game message disband it etc


class LobbyCog(commands.Cog):
    def __init__(self, client1: discord.Client,
                 GAME_NAME: str,
                 BASE_CMD_NAME: str = None,
                 playerclass: type = None,
                 lobbyclass: type = None,
                 gameclass: type[Game] = None,
                 minplayers: int = None,
                 maxplayers: int = None,
                 TESTSERVER_ID: int = None):
        global client

        client = client1  # cant be both param and global
        try:
            self.logger = client.logger.getChild(f"{self.__module__}")
        except AttributeError:
            self.logger = logging.getLogger(f"{self.__module__}")
            self.logger.setLevel(logging.DEBUG)
            self.logger.addHandler(logging.StreamHandler())
            self.logger.warning(f"{self.__module__}: No bot.logger found, using root logger. Consider creating a logger using utils.mylogger.py and passing it into the bot/client as bot.logger = yourlogger")

        self.GAME_NAME = GAME_NAME
        self.BASE_CMD_NAME = BASE_CMD_NAME or antimakkcen(GAME_NAME.lower().replace(" ", "")).translate(str.maketrans("", "", string.punctuation))
        BASE_CMD_NAME = self.BASE_CMD_NAME

        self.playerclass = playerclass or Player
        self.lobbyclass = lobbyclass or Lobby
        self.gameclass = gameclass or Game
        self.minplayers = minplayers
        self.maxplayers = maxplayers
        self.TESTSERVER_ID = TESTSERVER_ID
        self.TESTSERVER = Object(self.TESTSERVER_ID) if self.TESTSERVER_ID else None

        self.users: dict[int, Player] = {}
        self.lobbies: dict[str, Lobby] = {}

        os.makedirs(r"./data", exist_ok=True)
        self.readUsers()
        self.basecmd = discord.SlashApplicationCommand(description=f"Commands for {self.GAME_NAME} game.", name=BASE_CMD_NAME, guild_ids=(self.TESTSERVER_ID,), force_global=not self.TESTSERVER_ID, callback=self.basegamecmd)
        self.helpcmd = discord.SlashApplicationSubcommand(description=f"Shows the help manual to the {self.GAME_NAME} game.", name="help", parent_cmd=self.basecmd, cmd_type=discord.ApplicationCommandOptionType.sub_command, callback=self.showhelp)
        self.statscmd = discord.SlashApplicationSubcommand(description=f"Shows your stats across all the {self.GAME_NAME} games you´ve played.", name="stats", parent_cmd=self.basecmd, cmd_type=discord.ApplicationCommandOptionType.sub_command, callback=self.showstats)
        self.joincmd = discord.SlashApplicationSubcommand(description=f"Join an existing {self.GAME_NAME} lobby.", name="join", parent_cmd=self.basecmd, cmd_type=discord.ApplicationCommandOptionType.sub_command, callback=self.joinlobby)
        self.leavecmd = discord.SlashApplicationSubcommand(description="Leave the lobby you are currently in.", name="leave", parent_cmd=self.basecmd, cmd_type=discord.ApplicationCommandOptionType.sub_command, callback=self.leavelobby)
        self.startcmd = discord.SlashApplicationSubcommand(description=f"Creates a {self.GAME_NAME} lobby for users to join and to start the game.", name="start", parent_cmd=self.basecmd, cmd_type=discord.ApplicationCommandOptionType.sub_command, callback=self.makeLobby)

        for child in [self.helpcmd, self.statscmd, self.joincmd, self.leavecmd, self.startcmd]:
            self.basecmd.children[child.name] = child

        self.application_commands.append(self.basecmd)
        self.other_commands = {}
        self.process_app_cmds()

        self.help_categories = {}

        categories = [
            HelpCategory("Commands", "Gives help about the game commands.", emoji.emojize(":paperclip:"), None),
            HelpCategory("Rules", "Explains the rules of this game.", emoji.emojize(":ledger:"), "Rules"),
            HelpCategory("Credits", "Links and about.", emoji.emojize(":globe_with_meridians:"), "Credits")
        ]
        self.help_categories = {c.label: c for c in categories}

    def add_subcommand(self, name: str, callback: Callable[[discord.Interaction], Coroutine[..., ..., None]], description: str = None):
        """Adds a subcommand to the base command of the game. The callback function's docstring will appear in the help command's description."""
        cmd = discord.SlashApplicationSubcommand(name=name, description=description,
                                                 parent_cmd=self.basecmd, cmd_type=discord.ApplicationCommandOptionType.sub_command,
                                                 callback=callback)
        self.basecmd.children[cmd.name] = cmd
        self.process_app_cmds()

    @property
    def credits(self):
        return self.help_categories["Credits"].helptext

    @credits.setter
    def credits(self, value):
        self.help_categories["Credits"].helptext = value

    @property
    def rules(self):
        return self.help_categories["Rules"].helptext

    @rules.setter
    def rules(self, value):
        self.help_categories["Rules"].helptext = value

    @property
    def commands_helptext(self):
        cmd_sign = (client.get_application_command_from_signature(self.BASE_CMD_NAME, discord.ApplicationCommandType.chat_input, self.TESTSERVER_ID))
        cmds: dict[str, discord.SlashApplicationSubcommand] = cmd_sign.children
        cmds.update(self.other_commands)
        return "\n\n".join([f"{v.get_mention(self.TESTSERVER)} = {v.callback.__doc__}" for k, v in cmds.items()])

    def readUsers(self):  # TODO yes it is 100x more favourable to use actual databases but thats extra hassle to set up for beginngers and for little servers and friend group/communities this shall be enough. plug and play >>>
        try:
            with open(root + fr"/data/{self.BASE_CMD_NAME}Users.txt", "r", encoding="UTF-8") as f:
                tempusers = json.load(f)
                self.logger.debug(f"{len(tempusers)} player profiles loaded")
                for k in tempusers:
                    self.users[int(k["userid"])] = self.playerclass(k)
        except OSError as e:
            self.logger.warning(e)
            with open(root + fr"/data/{self.BASE_CMD_NAME}Users.txt", "w", encoding="UTF-8") as f:
                json.dump({}, f)
                self.logger.info(f"{f} created")
        except json.decoder.JSONDecodeError as e:
            self.logger.error(f"Error reading users: {e}")
            self.users = {}
            pass

    def getLobby(self, lobbyid: str) -> Optional[Lobby]:
        return self.lobbies.get(lobbyid.upper(), None) if lobbyid else None

    def getPlayer(self, dc_user: int | discord.Member | discord.User):
        if isinstance(dc_user, int):
            lookingfor = dc_user
        elif isinstance(dc_user, str):
            lookingfor = int(dc_user)
        elif isinstance(dc_user, (discord.Member, discord.User)):
            lookingfor = dc_user.id
        elif isinstance(dc_user, MockPlayer):  # just keep it
            lookingfor = dc_user.userid
            self.users.update({dc_user.userid: dc_user})
        else:
            raise NotImplementedError(type(dc_user))
        if lookingfor in self.users:  # idk how to do this with defaultdict
            return self.users.get(lookingfor)
        else:
            lookingfor = client.get_user(lookingfor) or client.fetch_user(lookingfor)
            if lookingfor:
                user = self.playerclass(lookingfor)
                self.users.update({user.userid: user})
                self.savePlayers()
                return user
            else:
                raise ValueError(f"User {lookingfor} not found")

    def savePlayers(self):
        with open(root + fr"/data/{self.BASE_CMD_NAME}Users.txt", "w", encoding="UTF-8") as file:
            json.dump(obj=[v.toDict() for k, v in self.users.items()],
                      fp=file,
                      default=lambda o: o.__dict__ if hasattr(o, "__dict__") else str(o),
                      indent=4)
        self.logger.info("saved users")

    # @discord.slash_command(description="Commands for the games", name="placeholder", guild_ids=(self.TESTSERVER, 409081549645152256), force_global=not self.TESTSERVER)
    async def basegamecmd(self, interaction):
        pass

    # @basegamecmd.subcommand(name="stats", description="Shows your stats across all the games you´ve played.")
    async def showstats(self, interaction: discord.Interaction,
                        user: discord.User = discord.SlashOption(name="user", description="See someone else´s profile.", required=False, default=None)):
        """Shows your or someone else's statistics across all games."""  # this will be the helptext for /help
        if user is None:
            user = interaction.user
        player = self.getPlayer(user)
        embedVar = discord.Embed(title=f"__{user.display_name}'s statistics__")
        embedutil.setuser(embedVar, user)
        if len(player.statistics) == 0:
            embedVar.add_field(name="Empty", value=f"Looks like this user has not played **{self.GAME_NAME}** before. Encourage them by inviting them to a game!")
        for k, v in sorted(player.statistics.items(), key=lambda k: k[0]):
            embedVar.add_field(name=k, value=v)
        await interaction.send(embed=embedVar)

    def add_help_category(self, cat: HelpCategory):
        self.help_categories[cat.label] = cat

    # @basegamecmd.subcommand(name="help", description="Shows the help manual to this game and the bot.")
    async def showhelp(self, interaction: discord.Interaction): #TODO pagi?
        """Well you somehow managed to find this command, so good job!"""  # this will be the helpt ext for /help

        class HelpTopicSelector(discord.ui.Select):
            def __init__(self, categories):
                self.categories: dict[str, HelpCategory] = categories
                opts = [discord.SelectOption(label=c.label, description=c.description, emoji=c.emoji) for c in self.categories.values()] + [discord.SelectOption(label="Close", value="0", emoji=emoji.emojize(":cross_mark:"))]
                super().__init__(options=opts)

            async def callback(self, interaction: discord.Interaction):  # TODO maybe sort commands or subcommands by abc?
                if self.values[0] == "0":
                    await interaction.response.edit_message(content="Closed. Have fun playing!", view=None, embed=None, delete_after=5.0)
                else:
                    c = self.categories.get(self.values[0], None)
                    if c:
                        embed = discord.Embed(title=f"About {c.label}", description=c.helptext)
                        embedutil.setuser(embed, interaction.user)
                        await interaction.edit(embed=embed)

        embedVar = discord.Embed(title="What do you wish to learn about?", description="Pick a topic below:")  #add page indicator to the title if mult pages
        embedutil.setuser(embedVar, interaction.user)
        viewObj = discord.ui.View(timeout=3600)

        categories = self.help_categories
        if categories["Commands"].helptext is None:
            categories["Commands"].helptext = self.commands_helptext

        if categories["Rules"].helptext == "Rules":
            self.logger.warning("No rules defined for this game. Do so with yourcog.rules = \"Your rules\"")
        if categories["Credits"].helptext == "Credits":
            self.logger.warning("No credits defined for this game. Do so with yourcog.credits = \"Your credits\"")

        viewObj.add_item(HelpTopicSelector(categories))
        await interaction.send(embed=embedVar, view=viewObj)

    # @basegamecmd.subcommand(name="join", description="Join an existing lobby.")
    async def joinlobby(self, interaction: discord.Interaction, lobbyid: str = discord.SlashOption(name="lobbyid",
                                                                                                   description="A lobby´s identification e.g. ABCD",
                                                                                                   required=True)):
        """Use this command to enter a lobby using its unique lobby code identifier."""
        # this will be the helptext for /help
        user = self.getPlayer(interaction.user)
        lobby = self.getLobby(lobbyid.upper())
        if lobby:
            await lobby.addPlayer(interaction, user)
        else:
            await embedutil.error(interaction, f"Lobby {lobbyid.upper()} not found.")

    # @basegamecmd.subcommand(name="leave", description="Leave the lobby you are currently in.")
    async def leavelobby(self, interaction: discord.Interaction):
        """Leave the lobby you are currently in."""
        user = self.getPlayer(interaction.user)
        lobby = self.getLobby(user.inLobby)
        if lobby:
            await lobby.on_leave(user, "left")
            if await lobby.removePlayer(interaction.channel, user):
                embed = discord.Embed(title=f"Left {lobby.lobbyleader.name}'s lobby.")
                embedutil.setuser(embed, interaction.user)
                await interaction.send(
                    embed=embed,
                    ephemeral=True)
                try:
                    await lobby.managemsg.edit(view=AdminView(lobby))  # removing the player from the kick dropdown
                except nextcord.errors.NotFound:
                    pass
            else:
                await embedutil.error(interaction, "Unable to leave.")  # TODO somehow allow them to leave an ongoing game xd
        else:
            await embedutil.error(interaction, "You are not currently in a lobby.")

    # @basegamecmd.subcommand(name="start", description=f"Creates a lobby for users to join and to start the game.")
    async def makeLobby(self, interaction: discord.Interaction, private=discord.SlashOption(name="private",
                                                                                            description="Do you wish to create a public lobby or a private one?",
                                                                                            required=False,
                                                                                            default="Public",
                                                                                            choices=("Public", "Private")
                                                                                            )):
        """Makes a lobby for the game. You can set the lobby to private to only allow people with an invite code."""

        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await embedutil.error(interaction, "Games cannot be started if the bot is not invited to the server.", delete=20)
        user = self.getPlayer(interaction.user)
        if user.inLobby:
            await interaction.send(embed=discord.Embed(
                title=f"You are already in a lobby. Try {self.leavecmd.get_mention(self.TESTSERVER)}",
                color=discord.Color.red()), ephemeral=True)
            return
        else:
            # lobbymessage = await interaction.channel.send(embed=discord.Embed(title="Generating lobby..."))
            newLobby: Lobby = self.lobbyclass(
                interaction=interaction,
                messageid=None,
                cog=self,
                private=(private == "Private"),
                game=self.gameclass,
                minplayers=self.minplayers,
                maxplayers=self.maxplayers)

            self.lobbies.update({newLobby.code: newLobby})
            await newLobby.addPlayer(interaction, user)
            await newLobby.send_lobby(interaction)

    class KickPlayerDropdown(discord.ui.Select):
        def __init__(self, lobby: Lobby, cog: LobbyCog):
            self.lobby = lobby
            self.cog = cog
            # self.players = self.lobby.players[1:]  # first player later doesn't have to be the lobbyleader
            self.players = [player for player in self.lobby.players if player.userid != self.lobby.lobbyleader.id]
            optionslist = [discord.SelectOption(label=i.name, value=f"{i.userid}") for i in self.players]
            optionslist.append(discord.SelectOption(label="Cancel", value="-1", emoji=emoji.emojize(":cross_mark:")))
            super().__init__(options=optionslist, placeholder="Pick a player to kick")

        async def callback(self, inter):
            result = self.values[0]
            if result != "-1":
                self.cog.logger.debug(f"kicking player number {result}")
                tokick = self.cog.getPlayer(int(self.values[0]))
                await self.lobby.on_leave(tokick, "kicked")
                await self.lobby.removePlayer(inter, tokick)
                await self.lobby.messageid.edit(embed=self.lobby.show())
            await inter.edit(view=self.lobby.adminView(self.lobby))


class AdminView(discord.ui.View):
    def __init__(self, lobby: Lobby, *args, **kwargs):
        self.lobby = lobby
        self.cog: LobbyCog = lobby.cog
        super().__init__(timeout=None, *args, **kwargs)

    @discord.ui.button(label="Kick Player", style=discord.ButtonStyle.red, emoji=emoji.emojize(":boot:", language="alias"))
    async def kickbutton(self, button, inter):
        viewObj = discord.ui.View()
        viewObj.add_item(self.cog.KickPlayerDropdown(self.lobby, self.cog))
        await inter.edit(view=viewObj)

    @discord.ui.button(label="Resend lobby message", style=discord.ButtonStyle.grey, emoji=emoji.emojize(":right_arrow_curving_left:"))
    async def resendbutton(self, button, inter):
        if inter.user.id == self.lobby.lobbyleader.id:
            await self.lobby.send_lobby(inter)
        else:
            await embedutil.error(inter, "You are not the leader of this lobby.")

    # @discord.ui.button(label="Testing", style=discord.ButtonStyle.grey) # remove
    # async def addmockplayers(self, button, inter):
    #     self.lobby.players.extend([MockPlayer(f"Player {i}") for i in range(1, 4)])
    #     for player in self.lobby.players[-3:]:
    #         self.lobby.teams[1].join(player)
    #     await self.lobby.readyCheck()
    #     await embedutil.success(inter, "Added 3 mock players")


class LobbyView(discord.ui.View):
    middlebutton: Callable[[Lobby], discord.ui.Button] | None = None

    def __init__(self, lobby: Lobby, *args, **kwargs):
        self.cog: LobbyCog = lobby.cog
        self.lobby = lobby
        super().__init__(timeout=3600, *args, **kwargs)
        if self.middlebutton:
            self.customize_middle_button(self.middlebutton)
        b = discord.utils.find(lambda c: c.custom_id == __file__ + "lobbyjoin", self.children)
        b.disabled = self.lobby.private

    @discord.ui.button(style=discord.ButtonStyle.green, emoji=emoji.emojize(":inbox_tray:"), custom_id=__file__ + "lobbyjoin")
    async def joinbutton(self, button, interaction):
        """Join lobby"""
        self.cog.logger.debug(f"{interaction.user} clicked join")
        player = self.cog.getPlayer(interaction.user)
        if await player.can_join(interaction, self.lobby):
            await self.lobby.addPlayer(interaction, player)

    @discord.ui.button(style=discord.ButtonStyle.red, emoji=emoji.emojize(":outbox_tray:"))
    async def leavebutton(self, button, interaction):
        """Leave lobby"""
        player = self.cog.getPlayer(interaction.user)
        await self.lobby.on_leave(player, "left")
        await self.lobby.removePlayer(interaction, player)
        self.cog.logger.debug(f"{interaction.user.name} clicked leave")

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji=emoji.emojize(":no_entry_sign:", language="alias"), disabled=True, custom_id=__file__ + "lobbymiddle")
    async def middlebuttoncb(self, button, inter):
        """Unused"""
        ...

    @discord.ui.button(style=discord.ButtonStyle.green, emoji=emoji.emojize(":check_mark_button:"))
    async def readybutton(self, button, interaction: discord.Interaction):
        """Ready / Unready"""
        player: PlayerProt = self.cog.getPlayer(interaction.user)
        if player.inLobby:
            await self.lobby.on_ready(player, interaction)
            self.cog.logger.debug(f"{interaction.user.name} requested ready/unready")
            if await player.can_ready(interaction, self.lobby):
                player.ready = not player.ready
                await self.lobby.readyCheck()
        else:
            await embedutil.error(interaction, "You are not in this lobby.")
            self.cog.logger.debug(f"{interaction.user.name} clicked ready on not joined lobby")

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=emoji.emojize(":right_arrow:"), disabled=True, custom_id=__file__ + "lobbystart")
    async def startbutton(self, button, interaction):
        """Start game"""
        await interaction.response.defer()
        if self.lobby.lobbyleader == interaction.user:
            if await self.canStart(interaction):
                await self.on_start(interaction)
                try:
                    await self.lobby.managemsg.edit(embed=None, view=None, content="Game started.", delete_after=5.0)
                except nextcord.errors.NotFound:
                    pass
                finally:
                    try:
                        await self.lobby.start(interaction)
                    except TypeError as e:
                        await embedutil.error(interaction, "Game class has no custom init or start method defined. You need to create your own Game class with these methods to start a game. For testing purposes:\n", delete=None)
                        txt = self.lobby.tojson()
                        self.cog.logger.debug(f"{len(txt)=}")
                        for text in TextWrapper(width=1800, break_long_words=False, replace_whitespace=False).wrap(txt):
                            await interaction.send(f"""```json\n + {text} + ```""", ephemeral=True)

                        raise e
        else:
            await embedutil.error(interaction, "You are not the leader of this lobby.")
            self.cog.logger.debug(f"{interaction.user.name} wanted to start game when not lobbyleader")

    async def on_timeout(self) -> None:
        await self.lobby.disband()
        # del self.cog.lobbies[self.lobby.code]
        del self

    def customize_middle_button(self, button: Callable[[Lobby], discord.ui.Button]):
        but = discord.utils.find(lambda b: b.custom_id == __file__ + "lobbymiddle", self.children)
        which = self.children.index(but)  # usually 3rd (index 2) lol, but I don't want to hardcode it
        self.children[which] = button(self.lobby)

    async def canStart(self, interaction: discord.Interaction):
        return True
        # to be overwritten in subclasses, something like not enough words loaded in or not everyone has unique icon or teams not balanced
        # use interaction to signal to the user what is wrong

    async def on_start(self, interaction):
        # to be overwritten in subclasses, something like sending an ephemeral admin view
        pass


class Lobby(object):
    def __init__(self, interaction: discord.Interaction, messageid: discord.Message, cog: LobbyCog, private=False, lobbyView: Callable[[Lobby], LobbyView] = None, adminView: Callable[[Lobby], AdminView] = None, game: type[Game] = None, minplayers: int = None, maxplayers: int = None):
        self.cog: LobbyCog = cog
        self.maxplayers: int = maxplayers or 25  # there is 25 slots in the kick dropdown, can populate 24 because cancel option, but fits perfectly because cant kick yourself. Also embeds can have only 25 fields
        self.minplayers: int = minplayers or 2  # mega lobby could be done, players printed in description, kick using pagi
        self.GAME_NAME = cog.GAME_NAME
        self.BASE_CMD_NAME = cog.BASE_CMD_NAME
        assert self.minplayers <= 25 and self.maxplayers <= 25, "Minimum and maximum players must not exceed 25"
        assert self.minplayers <= self.maxplayers, "Minimum players must be <= Maximum players"

        self.GameClass: type[Game] = game or Game
        self.players: list[PlayerProt] = []
        self.private: bool = private
        while (code := "".join([random.choice(string.ascii_uppercase) for _ in range(4)])) in self.cog.lobbies:
            self.cog.logger.info(f"generating lobbycode {code}")
            continue
        self.code: str = code
        self.ongoing: bool = False
        self.managemsg: discord.Message | None = None
        self.messageid = messageid
        self.lobbyleader = interaction.user
        self.cog.lobbies[self.code] = self
        self.lobbyView: Callable[[Lobby], discord.ui.View] = lobbyView or LobbyView
        self.adminView: Callable[[Lobby], discord.ui.View] = adminView or AdminView

    async def on_disband(self):
        """To be overwritten in subclasses
        Can be used to clean up things that need to be done when the lobby is disbanded."""
        pass

    async def on_join(self, player: PlayerProt, interaction: discord.Interaction):
        """
        This method is called when a player joins the lobby.
        Can be overridden in subclasses to provide custom behavior.
        """
        await embedutil.success(interaction, "Joined")

    async def on_ready(self, player: PlayerProt, interaction: discord.Interaction):
        """
        This method is called when a player joins the lobby.
        Can be overridden in subclasses to provide custom behavior.
        """
        pass  # default implementation does nothing

    async def on_leave(self, player: PlayerProt, reason: Literal["kicked", "left", "disbanded"]):
        """
        This method is called when a player leaves the lobby.
        Can be overridden in subclasses to provide custom behavior.
        """
        pass  # default implementation does nothing

    def readyCondition(self):
        """To be overwritten in subclasses"""

        readys = [i.is_ready() for i in self.players]
        return all(readys) and len(readys) >= self.minplayers

    def show_players(self, embedVar: discord.Embed) -> discord.Embed:
        i = 1
        for i, player in enumerate(self.players, start=1):
            embedVar.add_field(name=f"{i}. {player}", value="Ready? " + (
            emoji.emojize(":cross_mark:"), emoji.emojize(":check_mark_button:"))[bool(player.ready)], inline=False)
        while i < self.minplayers:
            embedVar.add_field(name="[Empty]", value="Ready? " + emoji.emojize(":cross_mark:"), inline=False)
            i += 1
        return embedVar

    @property
    def playercount(self) -> str:
        return f" ({len(self.players)}/{self.maxplayers})" if self.maxplayers else ""

    def add_footer(self, embedVar: discord.Embed):
        footertext = ""
        for b in filter(lambda i: isinstance(i, discord.ui.Button), self.lobbyView(self).children):
            if isinstance(b.callback, partial):
                footertext += f"{b.emoji} = {b.callback.func.__doc__ or 'Missing docstring'}" + ", "
            else:
                footertext += f"{b.emoji} = {b.callback.__doc__ or 'Missing docstring'}" + ", "
        embedVar.set_footer(text=footertext[:-2])
        return embedVar

    async def send_lobby(self, interaction: discord.Interaction):
        self.managemsg = await interaction.send(embed=discord.Embed(title=f"You are now the lobby leader of ||{self.code}||",
                                                   description=f"You can remove players from the lobby with the **Kick player** button\n\n" +
                                                               f"If the channel is spammed over, you can resend the lobby message with the **Resend lobbymsg** button\n\n" +
                                                               f"When everybody is ready, the start game ({emoji.emojize(':right_arrow:')}) button will enable under the lobby message."),
                                                ephemeral=True,
                                                view=self.adminView(self))
        # self.managemsg = await interaction.original_message()
        if self.messageid:
            await self.messageid.edit(
                embed=discord.Embed(title="The lobby you are looking for has moved", description="see below"),
                view=None, delete_after=30.0)
        lobbymessage = await interaction.channel.send(embed=discord.Embed(title="Generating lobby..."))
        self.messageid = lobbymessage
        await self.messageid.edit(embed=self.show(), view=self.lobbyView(self))

    def show(self) -> discord.Embed:
        if self.ongoing:
            desc = "Game already running."
        elif self.private:
            desc = f"ask the lobby leader for the code, \nthen use {self.cog.joincmd.get_mention(self.cog.TESTSERVER)} *CODE*, don't worry noone will see that."
        else:
            desc = f"use **{self.cog.joincmd.get_mention(self.cog.TESTSERVER)} {self.code}** or click the join icon"

        embedVar = discord.Embed(
            title=f"{self.lobbyleader.display_name}'s {('Public' if not self.private else 'Private')} **{self.GAME_NAME}** Lobby {self.playercount}",
            description=desc)

        embedVar = self.add_footer(embedVar)
        embedVar = self.show_players(embedVar)
        return embedVar

    def getPlayer(self, user: int | discord.Member | discord.User) -> PlayerProt:
        return self.cog.getPlayer(user)

    def __str__(self):
        return self.code+"+".join(map(str, self.players))

    async def readyCheck(self):
        viewObj = self.lobbyView(self)
        discord.utils.find(lambda b: b.custom_id == __file__ + "lobbyjoin", viewObj.children).disabled = bool(self.private)  # I don't know when or why should this ever change but heck im leaving it here

        if not self.ongoing:
            if self.readyCondition():
                discord.utils.find(lambda b: b.custom_id == __file__ + "lobbystart", viewObj.children).disabled = False
                self.cog.logger.debug("all players ready to go")
                await self.messageid.edit(embed=self.show(), view=viewObj)
                return True
            else:
                discord.utils.find(lambda b: b.custom_id == __file__ + "lobbystart", viewObj.children).disabled = True
                self.cog.logger.debug("not all players ready to go")
        else:
            for child in viewObj.children:
                child.disabled = True
        try:
            await self.messageid.edit(embed=self.show(), view=viewObj)
        except AttributeError:
            pass
        return False

    async def start(self, interaction: discord.Interaction) -> None:
        # if await self.readyCheck(): #hold on why is it like this #looks like this is working as intended
        if not self.ongoing:
            self.ongoing = True
            await self.readyCheck()  # this is needed to update the view
            for p in self.players:  # unready players for potential next game
                # if isinstance(p, self.cog.playerclass):  # in case someone implements bots
                if type(p) is self.cog.playerclass:  # what if the bots are subclassing the player
                    p.ready = False
            game = self.GameClass(self)  # create game
            await game.start(interaction)  # if I do interaction.send it breaks after 15mins cuz interactions. gotta do interaction.channel.send
            self.cog.savePlayers()
        else:  # should not be achievable as the start button should be disabled when game is ongoing, maybe delete
            await embedutil.error(interaction, "A game is already running.")
            self.cog.logger.warning("ongoing game")

    async def addPlayer(self, interaction: discord.Interaction, player: PlayerProt) -> None:
        if not self.maxplayers or len(self.players) < self.maxplayers:
            if not self.ongoing:
                if not player.inLobby:
                    await self.on_join(player, interaction)
                    player.inLobby = self.code
                else:
                    await embedutil.error(interaction, f"You are already in a lobby. Try {self.cog.leavecmd.get_mention(self.cog.TESTSERVER)}", delete=10)
                    self.cog.logger.debug("already in lobby")
                    return
                # await self.messageid.edit(embed=self.show()) #redundant: gets updated in readyCheck again too so
                self.players.append(player)
                await self.readyCheck()
            else:
                self.cog.logger.error("ongoing game")  # shouldn't be a possibility, remove buttons from lobbymsg after start
        else:
            await embedutil.error(interaction, "Lobby is already full!")

    async def removePlayer(self, interaction: discord.Interaction | discord.TextChannel, player: PlayerProt) -> bool:  # TODO remove text channel??
        if not self.ongoing:
            if player in self.players:
                self.players.remove(player)
                if hasattr(player, "team") and player.team:
                    player.team.remove(player)
                player.inLobby = None
                player.ready = False
                leader = self.cog.getPlayer(self.lobbyleader)
                if player == leader:
                    await self.disband()
                else:
                    # await self.messageid.edit(embed=self.show()) #readycheck should also rerender
                    await self.readyCheck()
                return True

            else:
                await embedutil.error(interaction, "You are not in this lobby.", delete=10)
                return False
        else:
            self.cog.logger.info("game ongoing")
            # TODO allow leaving xd
            return False

    async def disband(self):
        await self.on_disband()
        for player in self.players:
            await self.on_leave(player,  "disbanded")
            player.inLobby = None
            player.ready = False
            if hasattr(player, "team") and player.team:
                player.team.remove(player)
        try:
            await self.managemsg.delete()
        except nextcord.errors.NotFound:
            try:
                await self.managemsg.edit(embed=discord.Embed(title="Lobby disbanded."), view=None, delete_after=5.0)
            except nextcord.errors.NotFound:  # what is this try except hell xdd
                pass
        try:
            await self.messageid.edit(embed=discord.Embed(title="Lobby disbanded.", description=f"Make a new one with {self.cog.startcmd.get_mention(self.cog.TESTSERVER)}"), view=None, delete_after=30.0)
        except discord.errors.NotFound:  # disbanding after a game cannot edit message as it doesn't exist anymore
            pass
        try:
            del self.cog.lobbies[self.code]
        except KeyError:
            self.cog.logger.debug(f"{self.code} already deleted, why is still wanting to timeout and disband?")

    def tojson(self):
        return json.dumps(self.toDict(), default=lambda o: o.__dict__ if hasattr(o, "__dict__") else str(o), indent=4)

    def toDict(self):  # filter stuff that should not be printed as these are long lol
        return {k: v for k, v in self.__dict__.items() if
                k not in ("cog", "adminView", "buttonsView")}


class PlayerProt(Protocol):
    inLobby: str | None
    userid: int
    ready: bool
    name: str
    statistics: dict[str, int]
    user: discord.User

    def __init__(self, discorduser: discord.Member | dict | discord.User):
        ...

    def is_ready(self) -> bool:
        ...

    async def can_ready(self, interaction: discord.Interaction, lobby: Lobby) -> bool:
        ...

    async def can_join(self, interaction: discord.Interaction, lobby: Lobby) -> bool:
        ...

    def toDict(self) -> dict:
        ...


class Player:
    """A player in a lobby
    :param discorduser: The discord User object or a dictionary resembling a Player's attributes

    Usage:

    player = Player(interaction.user)
    player.ready = True

    :ivar userid: The discord user id
    :ivar statistics: A dictionary of statistics over the games played like wins, losses, etc.
    :ivar ready: Whether the player is ready
    :ivar inLobby: The lobby code the player is in or None
    :ivar user: The discord user object
    :ivar name: The user's username in discord
    """
    def __init__(self, discorduser: discord.Member | dict | discord.User):
        if isinstance(discorduser, dict):
            for k, v in discorduser.items():
                if k in ("statistics", "stats"):
                    setattr(self, "statistics", defaultdict(int))
                    self.statistics.update(v)
                elif k.endswith("_dt"):    #TODO document this
                    setattr(self, k, datetime.fromisoformat(v))
                elif k in ("name",):
                    continue
                else:
                    setattr(self, k, v)
        else:
            self.statistics: dict[str, int] = defaultdict(int)
            self.userid = discorduser.id
        self.ready = False
        self.inLobby: str | None = None
        self._important = ["userid", "statistics"]  # only these attrs will be saved

    @property
    def user(self):
        return client.get_user(self.userid) or client.fetch_user(self.userid)

    @property
    def name(self):
        return self.user.name
    # implement something like which team they are on or how many points or words submitted

    def is_ready(self):
        return self.ready
    # implement something like has team

    async def can_ready(self, interaction: discord.Interaction, lobby: Lobby) -> bool:  # TODO why is can_ready in Player instead of Lobby?
        return True  # implement something like has enough words
    # use interaction to signal to the user why they cannot ready up

    async def can_join(self, interaction: discord.Interaction, lobby: Lobby) -> bool:  # TODO same
        return True  # implement something like has role, level, permission
    # use interaction to signal to the user why they cannot join

    def __hash__(self):
        return hash(self.userid)

    def __repr__(self):
        return f"{self.__dict__}"

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.userid == other.userid
        elif isinstance(other, MockPlayer):
            return self.userid == other.userid
        else:
            raise NotImplementedError(f"Comparison between {self.__class__} and {other.__class__}")

    def __str__(self):
        return f"{self.name}"  # some ideas
        # return f"{self.name} ({self.points} points)"
        # return f"{self.name} ({len(self.words)} words)"

    def toDict(self):  # filter stuff that should not persist between games and restarts
        return {k: v for k, v in self.__dict__.items() if k in self._important}

    def tojson(self):
        return json.dumps(self.toDict(), default=lambda o: o.isoformat() if isinstance(o, date) else o.__dict__ if hasattr(o, "__dict__") else str(o), indent=4)


class MockPlayer(Player):
    def __init__(self, name: str, cog):
        super().__init__(client.get_user(617840759466360842))

        self._name = name
        self.userid = random.randrange(100_000_000, 999_999_999)
        cog.users.update({self.userid: self})
        self.ready = True
        # self.userid = 617840759466360842
        # self.color = discord.Color.random()

    @property
    def name(self):
        return self._name

    def __eq__(self, other):
        return other.userid == self.userid


class TimerButton:
    ... #todo sends a timestamp, await sleep and sends a ping, says who started it, can set who can start it anyone or admin, can set how many to start??, and like an on_end event


class Game(ABC):

    @abstractmethod
    def __init__(self, lobby: Lobby):
        self.players = lobby.players
        self.lobby = lobby

    @abstractmethod
    async def start(self, interaction: discord.Interaction):  # i debated long whether i should have Message here in the signature or Interaction, as it is advised to send new messages to the channel directly instad of as an inter response but oh well
        await interaction.channel.send("Game started with players: " + ", ".join([p.name for p in self.players]))
        await interaction.send("Make sure to do interaction.channel.send instead of directly responding to the interaction as they cannot be edited nor used after 15 minutes of playing", ephemeral=True)

    def getPlayer(self, user:  int | discord.Member | discord.User) -> PlayerProt:
        return self.lobby.cog.getPlayer(user)

    def savePlayers(self):
        self.lobby.cog.savePlayers()

    class ReturnButton(discord.ui.View):
        def __init__(self, game: Game):
            super().__init__(timeout=None)
            self.game = game

        @discord.ui.button(label="Return to lobby")
        async def callback(self, button, inter):
            for p in self.game.lobby.players:
                p.ready = False
            await self.game.lobby.send_lobby(inter)


class HelpCategory:
    """A class for help categories
    These will show up when the game /help command is called
    Attributes:
        label (str): The name or label of the category
        description (str): The description that will show up beside the label in the select menu
        emoji (str): The emoji that will show up in the select menu
        helptext (str): The helptext that will be shown once the category is selected. This is the actual help text for the category
    """
    def __init__(self, label, description, emoji, helptext):
        self.label = label
        self.description = description
        self.emoji = emoji
        self.helptext = helptext
