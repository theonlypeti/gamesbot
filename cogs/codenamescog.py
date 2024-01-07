from __future__ import annotations
import os
import random
import string
from copy import deepcopy
from tabulate import tabulate
import utils.embedutil
from typing import Optional
import nextcord as discord
import nextcord.errors
from nextcord.ext import commands
import json
import emoji
from collections import defaultdict

from utils.Inventory import Inventory
from utils.mentionCommand import mentionCommand
from utils import embedutil, Colored

root = os.getcwd()
GAME_NAME = "Codenames"
BASE_CMD_NAME = "codenames"
ROUND_TIMER = 300


class Team:
    def __init__(self, color: Colored.ColorGroup):
        self.players: list[CodenamesCog.Player] = []
        self.guesser: CodenamesCog.Player | None = None
        self.spymaster: CodenamesCog.Player | None = None
        self.words: list[str] = []
        self.color: Colored.ColorGroup = color
        self.minplayers: int = 2
        self.eliminated = False

    @property
    def name(self):
        return self.color.name

    def join(self, player: CodenamesCog.Player):
        if player.team:
            player.team.remove(player)
        self.players.append(player)
        player.team = self

    def remove(self, player: CodenamesCog.Player):
        self.players.remove(player)
        player.team = None

    def __bool__(self):
        return bool(self.players)


class CodenamesCog(commands.Cog):
    def __init__(self, client1: discord.Client):
        global logger
        global client
        client = client1  # cant be both param and global
        logger = client.logger.getChild(f"{__name__}cog")
        self.users: dict[int, CodenamesCog.Player] = {}
        self.lobbies: dict[str, CodenamesCog.Lobby] = {}
        self.teams = sorted([Team(col) for col in Colored.Colored.list().values()], key=lambda t: t.color.emoji_square)
        logger.info([team.name for team in self.teams])
        os.makedirs(r"./data", exist_ok=True)
        try:
            with open(root + r"/data/codenamesUsers.txt", "r", encoding="UTF-8") as f:
                tempusers = json.load(f)
                logger.debug(f"{len(tempusers)} player profiles loaded")
                for k in tempusers:
                    self.users[int(k["userid"])] = self.Player(k)
        except OSError as e:
            logger.warning(e)
            with open(root + r"/data/codenamesUsers.txt", "w", encoding="UTF-8") as f:
                json.dump({}, f)
                logger.info(f"{f} created")
        except json.decoder.JSONDecodeError as e:
            logger.error(f"Error reading users: {e}")
            self.users = {}
            pass

    @discord.slash_command(description="Commands for the games", name=BASE_CMD_NAME)
    async def basegamecmd(self, interaction):
        pass

    @basegamecmd.subcommand(name="stats", description="Shows your stats across all the games you´ve played.")
    async def showstats(self, ctx: discord.Interaction, user: discord.User = discord.SlashOption(name="user", description="See someone else´s profile.", required=False, default=None)):
        if user is None:
            user = ctx.user
        player = self.getUserFromDC(user)
        embedVar = discord.Embed(title=f"__{user.display_name}'s stats__", color=user.color)
        if len(player.stats) == 0:
            embedVar.add_field(name="Empty", value=f"Looks like this user has not played **{GAME_NAME}** before. Encourage them by inviting them to a game!")
        for k, v in player.stats.items():
            embedVar.add_field(name=k, value=v)
        await ctx.send(embed=embedVar)

    @basegamecmd.subcommand(name="help", description="Shows the help manual to this game and the bot.")
    async def showhelp(self, ctx: discord.Interaction):
        helptext = {
            "commands": f"""{mentionCommand(client, BASE_CMD_NAME.strip() + ' start')} makes a lobby for a game. You can set the lobby
            to private to only allow people with an invite code.
            
            {mentionCommand(client, BASE_CMD_NAME.strip() + ' join')} <CODE> joins an existing lobby.
            
            Use {mentionCommand(client, BASE_CMD_NAME.strip() + ' leave')} to leave the lobby you are currently in.
            
            {mentionCommand(client, BASE_CMD_NAME.strip() + ' stats')} shows your or someone else's statistics across all games.  
            """,

            "rules": """Each turn, one player from a team will be the __spymaster__ and the rest will be __guessers__.

                The spymaster will give a **one-word** clue and a number. The clue relates to the words on the board and the number indicates how many words the clue relates to.
                
                The guessers then together try to guess the words for their team on the board based on the clue. They must avoid words that belong to the opposing team, neutral words, and the __assassin word__.
                
                You may guess more words at a time. If a spy guesses a word that belongs to their team, they score a point. If they guess a word that belongs to the opposing team or a neutral word, their turn ends immediately.
                
                If they guess the assassin word, their team loses the game immediately.
                
                The game continues until one team has guessed all their words correctly, or until one team has guessed the assassin word.""",

            "clues": """The clue must be a single word. It must not be a word on the board.
             
            It may not be a word that is a prefix or a part of any of the words on the board.
             
            It may not be for example the letter "s" to denote all the words that begin with "s" on the board.
             
            The clue may be for example (Apple, 2) for the words: "pie" and "tree". """,

            "credits": """The game is based on the tabletop board game **Codenames** by Czech Games Edition
                https://czechgames.com/en/codenames/
                https://czechgames.com/en/home/
                Bot and game adaptation created by @theonlypeti
                https://github.com/theonlypeti"""
        }

        class HelpTopicSelector(discord.ui.Select):
            def __init__(self):
                opts = [discord.SelectOption(label="Commands", description="Gives help about the game commands.", value="commands", emoji=emoji.emojize(":paperclip:")),
                        discord.SelectOption(label="Rules", description="Explains the rules of this game.", value="rules", emoji=emoji.emojize(":ledger:")),
                        discord.SelectOption(label="Clues", description="Clarifies what constitutes as a valid clue for the game.", value="clues", emoji=emoji.emojize(":mag:", language="alias")),
                        discord.SelectOption(label="Credits", description="Links and about.", value="credits", emoji=emoji.emojize(":globe_with_meridians:")),
                        discord.SelectOption(label="Close", value="0", emoji=emoji.emojize(":cross_mark:"))]
                super().__init__(options=opts)

            async def callback(self, interaction: discord.Interaction):
                if self.values[0] == "0":
                    await interaction.response.edit_message(content="Closed. Have fun playing!", view=None, embed=None, delete_after=5.0)
                else:
                    await interaction.edit(embed=discord.Embed(title=f"About {self.values[0]}", description=helptext[self.values[0]], color=interaction.user.color))

        embedVar = discord.Embed(title="What do you wish to learn about?", description="Pick a topic below:", color=ctx.user.color)
        viewObj = discord.ui.View(timeout=3600)
        viewObj.add_item(HelpTopicSelector())
        await ctx.send(embed=embedVar, view=viewObj)

    class LobbyView(discord.ui.View):
        def __init__(self, cog, lobby):
            self.cog: CodenamesCog = cog
            self.lobby = lobby
            super().__init__(timeout=3600)
            # super().__init__(timeout=10)

        @discord.ui.button(style=discord.ButtonStyle.green, emoji=emoji.emojize(":inbox_tray:"))
        async def joinbutton(self, button, ctx):
            player = self.cog.getUserFromDC(ctx.user)
            await self.lobby.addPlayer(ctx, player)
            logger.debug(f"{ctx.user.name} clicked join")

        @discord.ui.button(style=discord.ButtonStyle.red, emoji=emoji.emojize(":outbox_tray:"))
        async def leavebutton(self, button, ctx):
            player = self.cog.getUserFromDC(ctx.user)
            await self.lobby.removePlayer(ctx, player)
            logger.debug(f"{ctx.user.name} clicked leave")

        @discord.ui.button(style=discord.ButtonStyle.grey, emoji=emoji.emojize(":running_shirt:", language="alias"), disabled=False)
        async def teamsbutton(self, button, ctx):
            player = self.cog.getUserFromDC(ctx.user)
            if player not in self.lobby.players:
                await utils.embedutil.error(ctx, "You are not in this lobby.")
                return
            if player.ready:
                await utils.embedutil.error(ctx, "You cannot change teams while ready.")
                return

            viewObj = discord.ui.View()
            viewObj.add_item(self.cog.TeamSelector(self.lobby, self.cog))
            await ctx.send(
                content=
                f"{emoji.emojize(':information_source:', language='alias')} The first person in the team will be responsible for casting the guesses. " +
                "They should discuss these choices with their teammates before picking the words.\n\n" +
                f"{emoji.emojize(':information_source:', language='alias')} The last person in the team will be the spymaster. They will be responsible for giving the clues. " +
                "If you wish to be the spymaster, repick your own team to be placed at the end.",
                view=viewObj, ephemeral=True)
            await self.lobby.readyCheck()

        @discord.ui.button(style=discord.ButtonStyle.green, emoji=emoji.emojize(":check_mark_button:"))
        async def readybutton(self, button, ctx: discord.Interaction):
            player = self.cog.getUserFromDC(ctx.user)
            if player.inLobby:
                logger.debug(f"{ctx.user.name} requested ready/unready")
                if player.team:
                    player.ready = not player.ready
                    await self.lobby.readyCheck()
                else:
                    await utils.embedutil.error(ctx, "You may not ready without a team assigned")
            else:
                await utils.embedutil.error(ctx, "You are not in this lobby.")
                logger.debug(f"{ctx.user.name} clicked ready on not joined lobby")

        @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=emoji.emojize(":right_arrow:"), disabled=True)
        async def startbutton(self, button, ctx):
            await ctx.response.defer()
            if self.lobby.lobbyleader == ctx.user:
                if not len(self.lobby.words) >= 25:
                    await utils.embedutil.error(ctx, "You need at least 25 words to start the game.")
                    return
                try:
                    await self.lobby.managemsg.edit(embed=None, view=None, content="Game started.", delete_after=5.0)
                except nextcord.errors.NotFound:
                    pass
                await self.lobby.start(ctx)
            else:
                await utils.embedutil.error(ctx, "You are not the leader of this lobby.")
                logger.info(f"{ctx.user.name} wanted to start game when not lobbyleader")

        async def on_timeout(self) -> None:
            await self.lobby.disband()
            del self.cog.lobbies[self.lobby.code]
            del self

    class KickPlayerDropdown(discord.ui.Select):
        def __init__(self, lobby, cog):
            self.lobby: CodenamesCog.Lobby = lobby
            self.cog: CodenamesCog = cog
            # self.players = self.lobby.players[1:]
            self.players = [player for player in self.lobby.players if player.userid != self.lobby.lobbyleader.id]  # first player later doesnt have to be the lobbyleader
            optionslist=list([discord.SelectOption(label=i.name, value=f"{i.userid}") for i in self.players])
            optionslist.append(discord.SelectOption(label="Cancel", value="-1", emoji=emoji.emojize(":cross_mark:")))
            super().__init__(options=optionslist, placeholder="Pick a player to kick")

        async def callback(self, inter):
            result = self.values[0]
            if result != "-1":
                logger.debug(f"kicking player number {result}")
                tokick = self.cog.getUserFromDC(int(self.values[0]))
                await self.lobby.removePlayer(inter, tokick)
                await self.lobby.messageid.edit(embed=self.lobby.show())
            await inter.edit(view=self.cog.MngmntView(self.lobby, self.cog))

    class MngmntView(discord.ui.View): #TODO add randomize teams button //but i dont know how many teams to randomize into
        def __init__(self, lobby, cog):
            self.lobby: CodenamesCog.Lobby = lobby
            self.cog: CodenamesCog = cog
            super().__init__(timeout=None)
            for i in self.children: # type: discord.ui.Button
                if i.custom_id == "mobilebutton":
                    i.style = discord.ButtonStyle.green if self.lobby.mobile else discord.ButtonStyle.red
                    i.emoji = emoji.emojize(":no_mobile_phones:", language="alias") if not self.lobby.mobile else emoji.emojize(":mobile_phone:", language="alias")
                    break

        @discord.ui.button(label="Kick Player", style=discord.ButtonStyle.red, emoji=emoji.emojize(":boot:", language="alias"))
        async def kickbutton(self, button, inter):
            viewObj = discord.ui.View()
            viewObj.add_item(self.cog.KickPlayerDropdown(self.lobby, self.cog))
            await inter.edit(view=viewObj)

        @discord.ui.button(label="Resend lobby message", style=discord.ButtonStyle.grey, emoji=emoji.emojize(":right_arrow_curving_left:"))
        async def resendbutton(self, button, inter):
            await self.lobby.messageid.edit(embed=discord.Embed(title="The lobby you are looking for has moved", description="see below"), view=None, delete_after=30.0)
            lobbymessage = await inter.channel.send(embed=discord.Embed(title="Generating lobby..."))
            self.lobby.messageid = lobbymessage
            await self.lobby.messageid.edit(embed=self.lobby.show(), view=self.cog.LobbyView(self.cog, self.lobby))

        @discord.ui.button(label="Mobile UI", style=discord.ButtonStyle.green, emoji=emoji.emojize(":mobile_phone:", language="alias"), custom_id="mobilebutton")
        async def mobilebutton(self, button: discord.ui.Button, inter: discord.Interaction):
            self.lobby.mobile = not self.lobby.mobile
            button.style = discord.ButtonStyle.red if not self.lobby.mobile else discord.ButtonStyle.green
            button.emoji = emoji.emojize(":no_mobile_phones:", language="alias") if not self.lobby.mobile else emoji.emojize(":mobile_phone:", language="alias")
            await inter.edit(view=self)
            txt = f"Mobile UI {'enabled' if self.lobby.mobile else 'disabled'}"
            warn = ""
            if not self.lobby.mobile:
                users = [inter.guild.get_member(i.userid) for i in self.lobby.players]
                on_mobile = [user for user in users if user and user.is_on_mobile()]
                mobileusers = '\n-'.join([user.display_name for user in on_mobile])
                warn = f"\nBeware! Some people might be on mobile:\n {mobileusers}" if on_mobile else ""
            await utils.embedutil.success(inter, txt + (warn if not self.lobby.mobile else ""))

        @discord.ui.button(label="Manage words", style=discord.ButtonStyle.grey, emoji=emoji.emojize(":ledger:"))
        async def mngwords(self, button, inter):
            inv: Inventory = Inventory(self.lobby.words)
            await inv.render(inter, ephemeral=True)

        # @discord.ui.button(label="Testing", style=discord.ButtonStyle.grey) #TODO remove
        # async def addmockplayers(self, button, inter):
        #     self.lobby.players.extend([MockPlayer(f"Player {i}") for i in range(1, 4)])
        #     for player in self.lobby.players[-3:]:
        #         self.lobby.teams[1].join(player)
        #     await self.lobby.readyCheck()
        #     await utils.embedutil.success(inter, "Added 3 mock players")

    @basegamecmd.subcommand(name="start", description=f"Makes a lobby for a {GAME_NAME} game.")
    async def makeLobby(self, ctx: discord.Interaction, private=discord.SlashOption(name="private", description="Do you wish to create a public lobby or a private one", required=False, default="Public", choices=("Public", "Private"))):
        await ctx.response.defer(ephemeral=True)
        user = self.getUserFromDC(ctx.user)
        if user.inLobby:
            await ctx.send(embed=discord.Embed(title=f"You are already in a lobby. Try {mentionCommand(client, BASE_CMD_NAME.strip() + ' leave')}", color=discord.Color.red()), ephemeral=True)
            return
        else:
            lobbymessage = await ctx.channel.send(embed=discord.Embed(title="Generating lobby..."))
            newLobby: CodenamesCog.Lobby = self.Lobby(ctx, lobbymessage, self, private=(private == "Private"))
            # newLobby.players.append(user)

            self.lobbies.update({newLobby.code: newLobby})
            await ctx.send(embed=discord.Embed(title=f"You are now the lobby leader of ||{newLobby.code}||",
                                               description=f"You can remove players from the lobby with the **Kick player** button\n\n" +
                                                           f"If the channel is spammed over, you can resend the lobby message with the **Resend lobbymsg** button\n\n" +
                                                           f"Mobile cannot render colored text, but PC has screwed up mobile emojis. If anyone is on mobile, i recommend keeping Mobile UI on.\n\n" +
                                                           f"When everybody is ready, a start game ({emoji.emojize(':right_arrow:')}) button will appear under the lobby message."),
                           ephemeral=True, view=self.MngmntView(newLobby, self))
            newLobby.managemsg = await ctx.original_message()

            await newLobby.addPlayer(ctx, user)
            user.inLobby = newLobby.code
            viewObj = self.LobbyView(self, newLobby)
            if private == "Private":
                viewObj.children[0].disabled = True

            await lobbymessage.edit(embed=newLobby.show(), view=viewObj)

    class Lobby(object):
        def __init__(self, ctx: discord.Interaction, messageid: discord.Message, cog, private=False):
            self.cog: CodenamesCog = cog
            with open(root + r"/data/codenamesWords.json", "r", encoding="UTF-8") as json_file:
                self.words = json.load(json_file)
            self.maxplayers: int = 25
            self.minplayers: int = 4
            assert self.minplayers <= 25 and self.maxplayers <= 25, "Minimum and maximum players must not exceed 25"
            assert self.minplayers <= self.maxplayers, "Minimum players must be <= Maximum players"

            self.players: list[CodenamesCog.Player] = []
            self.private: bool = private
            while (code := "".join([random.choice(string.ascii_uppercase) for _ in range(4)])) in [lobby.code for lobby in self.cog.lobbies.values()]:
                logger.info(f"generating lobbycode {code}")
                continue
            self.code: str = code
            self.ongoing: bool = False
            self.managemsg: discord.Message | None = None
            self.messageid = messageid
            self.lobbyleader = ctx.user
            self.init_teams()
            logger.debug(self.teams)
            self.cog.lobbies[self.code] = self
            self.mobile = True

        def init_teams(self):
            self.teams = deepcopy(self.cog.teams[2:4] + self.cog.teams[5:7])

        def __str__(self):
            return self.code+"+".join(map(str, self.players))

        def show(self) -> discord.Embed:
            name = self.lobbyleader.display_name
            EmbedVar = discord.Embed(
                title=f"{name}'s {('Public' if not self.private else 'Private')} **{GAME_NAME}** Lobby" + (f" ({len(self.players)}/{self.maxplayers})" if self.maxplayers else ""),
                description=("Game already running." if self.ongoing else f"use **{mentionCommand(client, BASE_CMD_NAME.strip() + ' join')} {self.code}** or click the join icon") if not self.private else f"ask the lobby leader for the code, \nthen use {mentionCommand(client, BASE_CMD_NAME.strip() + ' join')} *CODE*, don't worry noone will see that.") #extra space deliberate, otherwise looks stupid
            EmbedVar.set_footer(text="{} join, {} leave, {} teams, {} ready".format(emoji.emojize(":inbox_tray:"), emoji.emojize(":outbox_tray:"), emoji.emojize(":running_shirt:", language="alias"), emoji.emojize(":check_mark_button:")))
            i = 1

            for team in self.teams:
                if team:
                    for n, player in enumerate(team.players, start=1):
                        EmbedVar.add_field(name=f"{i}. {player}", value="Ready? " + (
                        emoji.emojize(":cross_mark:"), emoji.emojize(":check_mark_button:"))[bool(player.ready)], inline=False)
                        i += 1

                    if len(team.players) > 1:
                        EmbedVar.set_field_at(i-n-1, name=EmbedVar.fields[i-n-1].name + " (guesser)", value=EmbedVar.fields[i-n-1].value, inline=False)
                        EmbedVar.set_field_at(len(EmbedVar.fields)-1, name=EmbedVar.fields[-1].name + " (spymaster)", value=EmbedVar.fields[-1].value, inline=False)

            for n, player in enumerate(filter(lambda p: not p.team, self.players), start=1):
                EmbedVar.add_field(name=f"{i}. {player}", value="Ready? "+(emoji.emojize(":cross_mark:"), emoji.emojize(":check_mark_button:"))[bool(player.ready)], inline=False)
                i += 1

            while i-1 < self.minplayers:
                EmbedVar.add_field(name="[Empty]", value=f"Ready? {emoji.emojize(':cross_mark:')}", inline=False)
                i += 1

            # for field in EmbedVar.fields:
            #     logger.warning(f"{field.name}, {field.inline}")
            return EmbedVar

        async def readyCheck(self):
            readys = [i.isReady() for i in self.players]
            # uniqueIcons = len({i.icon for i in self.players}) == len(self.players)
            viewObj = self.cog.LobbyView(self.cog, self)
            viewObj.children[0].disabled = bool(self.private)
            teams = [t for t in self.teams if t]  # remove empty teams
            if not self.ongoing:
                if (all(readys)  # everyone is ready
                        and len(self.players) >= self.minplayers  # enough players
                        and all([len(t.players) >= t.minplayers for t in teams])  # enough players in each team
                        and len(teams) >= 2):  # enough teams
                    viewObj.children[-1].disabled = False
                    logger.debug("all players ready to go")
                    await self.messageid.edit(embed=self.show(), view=viewObj)
                    return True
                else:
                    viewObj.children[-1].disabled = True
                    logger.debug("not all players ready to go")
            else:
                for child in viewObj.children:
                    child.disabled = True
            await self.messageid.edit(embed=self.show(), view=viewObj)
            return False

        async def start(self, ctx: discord.Interaction) -> None:
            #if await self.readyCheck(): #hold on why is it like this #looks like this is working as intended
            if True:
                if not self.ongoing:
                    self.ongoing = True
                    await self.readyCheck()  # this is needed to update the view
                    # self.players = [FishyCog.Player(i) for i in ctx.guild.members if i.id != self.lobbyleader.id and i not in ctx.guild.bots] + self.players
                    # self.players = [FishyCog.Player(client.get_user(936709668317823078))] + self.players
                    game = CodenamesGame(self)  # create game

                    await game.start(ctx.channel)  # start game #if i do ctx.send it breaks after 15mins cuz interactions.
                    self.cog.savePlayers()
                else:  # should not be achievable as the start button should be disabled when game is ongoing, maybe delete
                    await utils.embedutil.error(ctx, "A game is already running.")
                    logger.warning("ongoing game")

        async def addPlayer(self, ctx: discord.Interaction, player: CodenamesCog.Player) -> None:
            if not self.maxplayers or len(self.players) < self.maxplayers:
                if not self.ongoing:
                    if not player.inLobby:
                        player.inLobby = self.code
                        # player.words = deepcopy(list(string.ascii_lowercase))
                        await embedutil.success(ctx, "Joined")
                    else:
                        await embedutil.error(ctx, f"You are already in a lobby. Try {mentionCommand(client, BASE_CMD_NAME.strip() + ' leave')}", delete=10)
                        logger.debug("already in lobby")
                        return
                    #await self.messageid.edit(embed=self.show()) #redundant: gets updated in readyCheck again too so
                    self.players.append(player)
                    await self.readyCheck()
                else:
                    logger.error("ongoing game")  # shouldnt be a possibility, remove buttons from lobbymsg after start
            else:
                await embedutil.error(ctx, "Lobby is already full!")

        async def removePlayer(self, ctx: discord.Interaction | discord.TextChannel, player: CodenamesCog.Player) -> bool:
            if not self.ongoing:
                if player in self.players:
                    self.players.remove(player)
                    if player.team:
                        player.team.remove(player)
                    player.inLobby = None
                    player.ready = False
                    leader = self.cog.getUserFromDC(self.lobbyleader)
                    if player == leader:
                        await self.disband()
                    else:
                        # await self.messageid.edit(embed=self.show()) #readycheck should also rerender
                        await self.readyCheck()
                    return True

                else:
                    await ctx.send(embed=discord.Embed(title="You are not in this lobby.", color=discord.Color.red()), ephemeral=True)
                    return False
            else:
                logger.info("game ongoing")
                #TODO allow leaving xd
                return False

        async def disband(self):
            for player in self.players:
                player.inLobby = None
                player.ready = False
                if player.team:
                    player.team.remove(player)
            try:
                await self.managemsg.delete()
            except Exception:
                try:
                    await self.managemsg.edit(embed=discord.Embed(title="Lobby disbanded."), view=None, delete_after=5.0)
                except Exception:  # what the f is this try except hell xddddddddddd
                    pass
            try:
                await self.messageid.edit(embed=discord.Embed(title="Lobby disbanded.", description=f"Make a new one with {mentionCommand(client, BASE_CMD_NAME.strip() + ' start')}"), view=None, delete_after=30.0)
            except AttributeError: #disbanding after a game cannot edit message as it doesnt exist anymore
                pass
            try:
                del self.cog.lobbies[self.code]
            except KeyError:
                logger.debug(f"{self.code} already deleted, why is still wanting to timeout and disband?")

    def findLobby(self, lobbyid: str) -> Optional[Lobby]:
        return self.lobbies.get(lobbyid.upper(), None)

    @basegamecmd.subcommand(name="join", description="Join an existing lobby.")
    async def joinlobby(self, ctx: discord.Interaction, lobbyid: str =discord.SlashOption(name="lobbyid", description="A lobby´s identification e.g. ABCD", required=True)):
        user = self.getUserFromDC(ctx.user)
        lobby = self.findLobby(lobbyid.upper())
        if lobby:
            await lobby.addPlayer(ctx, user)
        else:
            await ctx.send(embed=discord.Embed(title=f"Lobby \"**{lobbyid}**\" not found", color=ctx.user.color), ephemeral=True)

    @basegamecmd.subcommand(name="leave", description="Leave the lobby you are currently in.")
    async def leavelobby(self, ctx: discord.Interaction):
        user = self.getUserFromDC(ctx.user)
        lobby = self.findLobby(user.inLobby)
        if lobby:
            if await lobby.removePlayer(ctx.channel, user):
                await ctx.send(embed=discord.Embed(title=f"Left {lobby.lobbyleader.name}'s lobby.", color=ctx.user.color), ephemeral=True)
                await lobby.managemsg.edit(view=self.MngmntView(lobby, self))  # removing the player from the kick dropdown
            else:
                await embedutil.error(ctx, "Unable to leave.") #TODO somehow allow them to leave an ongoing game xd
        else:
            await embedutil.error(ctx, "You are not currently in a lobby.")

    def getUserFromDC(self, dcUser: int | discord.Member | "CodenamesCog.Player"):
        if isinstance(dcUser, int):
            lookingfor = dcUser
        elif isinstance(dcUser, discord.Member):
            lookingfor = dcUser.id
        elif isinstance(dcUser, CodenamesCog.Player): #just keep it
            lookingfor = dcUser.userid
        elif isinstance(dcUser, MockPlayer):  # just keep it
            lookingfor = dcUser.userid
            self.users.update({dcUser.userid: dcUser})
        else:
            raise NotImplementedError(type(dcUser))
        if lookingfor in self.users: #idk how to do this with defaultdict
            return self.users.get(lookingfor)
        else:
            lookingfor = client.get_user(lookingfor)
            user = self.Player(lookingfor)
            self.users.update({user.userid: user})
            self.savePlayers()
            return user

    def savePlayers(self):
        with open(root + r"/data/codenamesUsers.txt", "w", encoding="UTF-8") as file:
            json.dump([v.toDict() for k, v in self.users.items()], file, indent=4)
        logger.info("saved codenamesusers")

    class Player(object):
        def __init__(self, discorduser: discord.Member):
            if isinstance(discorduser, dict):
                for k, v in discorduser.items():
                    if k == "stats":
                        setattr(self, k, defaultdict(int))
                        self.stats.update(v)
                    else:
                        setattr(self, k, v)
            else:
                self.stats: dict[str, int] = defaultdict(int)
                self.userid = discorduser.id
            self.ready = False
            self.team: Team | None = None
            self.inLobby: str|None = None

        @property
        def name(self):
            return client.get_user(self.userid).display_name

        def isReady(self):
            return self.ready and self.team

        def __hash__(self):
            return hash(self.userid)

        def __repr__(self):
            return f"{self.__dict__}"

        def __eq__(self, other):
            logger.debug(other.__class__)
            logger.debug(other.__class__ == MockPlayer("a").__class__)
            logger.debug(isinstance(other, MockPlayer))
            logger.debug(MockPlayer("a").__class__)
            if isinstance(other, self.__class__):
                return self.userid == other.userid
            elif isinstance(other, MockPlayer):
                return self.userid == other.userid
            else:
                raise NotImplementedError(f"Comparison between {self.__class__} and {other.__class__}")

        def __str__(self):
            return (f"{self.team.color.emoji_square if self.team else emoji.emojize(':question_mark:', language='alias')} {self.name} {'(no team)' if not self.team else ''}")

        def toDict(self):
            return {k: v for k, v in self.__dict__.items() if k not in ("words", "inLobby", "ready", "team")}

    class TeamSelector(discord.ui.Select):
        def __init__(self, lobby: CodenamesCog.Lobby, cog):
            logger.debug(lobby.teams)
            self.lobby = lobby
            self.cog = cog
            self.teams = self.lobby.teams
            self.opts = [discord.SelectOption(label=team.name, value=str(n), emoji=team.color.emoji_square) for n, team in enumerate(self.teams)]
            super().__init__(placeholder="Pick a team", options=self.opts)

        async def callback(self, inter: discord.Interaction):
            team = self.teams[int(self.values[0])]
            player = self.cog.getUserFromDC(inter.user)
            team.join(player)
            await self.lobby.readyCheck()
            await inter.edit(view=None, content="Joined team " + team.name, delete_after=5.0)


class Word:
    def __init__(self, word: str, team: Team, is_mobile: bool):
        self.word = word
        self.team = team
        self.revealed = False
        self.prefix = None
        self.is_mobile = is_mobile

    def __bool__(self):
        return not self.revealed

    def __str__(self):
        if self.is_mobile:
            return self.prefix + " " + (self.colored if self.revealed else self.word + " ❓")
        else:
            return self.prefix + " " + (self.colored if self.revealed else self.word)

    @property
    def colored(self):
        if self.is_mobile:
            return self.team.color.string(self.word) + " " + self.team.color.emoji_square
        else:
            return self.team.color.string(self.word)


class CodenamesGame:
    def __init__(self, lobby: CodenamesCog.Lobby):
        allwords = random.sample(lobby.words, k=25)  # TIL choices can return duplicates
        self.lobby = lobby
        self.words = []
        self.teams = [t for t in self.lobby.teams if t]
        words_count = len(allwords) // max(len(self.teams), 3)
        logger.debug(words_count)
        for team in self.teams:
            logger.debug(team.name)
            team.words = [Word(w, team, self.lobby.mobile) for w in allwords[:words_count]]
            allwords = allwords[words_count:]
            self.words.extend(team.words)
            team.guesser = team.players[0]
            team.spymaster = team.players[-1]

        self.assasin = Word(allwords.pop(), Team(Colored.Colored.black), self.lobby.mobile)
        self.words.append(self.assasin)

        self.neutrals = [Word(w, Team(Colored.Colored.white), self.lobby.mobile) for w in allwords]
        self.words.extend(self.neutrals)

        random.shuffle(self.words)
        for n, w in enumerate(self.words, start=1):
            w.prefix = f"{n}."

        clr = tabulate([[w.colored for w in self.words[i:i + 5]] for i in range(0, len(self.words), 5)], tablefmt=("grid" if self.lobby.mobile else "fancy_grid")) #until i find a solution to emojis breaking tables, i stick with grid instead of fancy_grid
        self.coloredstr = f"```ansi\n{clr}\n```"
        self.msg: discord.Message | None = None

    @property
    def hiddenstr(self):
        string = tabulate([self.words[i:i + 5] for i in range(0, len(self.words), 5)], tablefmt=("grid" if self.lobby.mobile else "fancy_grid"))
        return f"```ansi\n{string}\n```"

    #
    async def returnToLobby(self):
        await self.lobby.messageid.edit(
            embed=discord.Embed(title="The lobby you are looking for has moved", description="see below"),
            view=None, delete_after=30.0)
        lobbymessage = await self.channel.send(embed=discord.Embed(title="Generating lobby..."))
        self.lobby.messageid = lobbymessage
        self.lobby.ongoing = False
        for player in self.lobby.players:
            player.ready = False
        for team in self.lobby.teams:
            team.words = []
            team.eliminated = False
        # self.lobby.init_teams()
        await self.lobby.readyCheck()
        # await self.lobby.messageid.edit(embed=self.lobby.show(), view=self.lobby.cog.LobbyView(self.lobby.cog, self.lobby))

    async def send_table(self, chann: discord.TextChannel = None, guesser: CodenamesCog.Player = None):
        if guesser:
            viewObj = discord.ui.View(timeout=ROUND_TIMER)
            viewObj.add_item(self.WordPicker(self, guesser))
            embedVar = discord.Embed(title=f"It's team {guesser.team.name}'s turn. ",
                                     description=f"{guesser.name} is guessing.",
                                     color=guesser.team.color.dccolor)
        else:
            viewObj = None
            embedVar = None

        logger.debug(self.msg)
        if not self.msg:
            self.msg = await chann.send(self.hiddenstr, embed=embedVar, view=viewObj)
            logger.debug(self.msg)
        else:
            await self.msg.edit(content=self.hiddenstr, embed=embedVar, view=viewObj)
        logger.debug(guesser)
        if guesser:
            if await viewObj.wait():
                logger.debug(f"{guesser.name} didn't guess in time")
                guesser.stats["Times AFK'd"] += 1
            else:
                logger.debug(f"{guesser.name} did guess in time")
            self.lobby.cog.savePlayers()

    class ReturnToLobby(discord.ui.View):
        def __init__(self, game: CodenamesGame, msg: discord.Message = None):
            self.game = game
            self.msg = msg
            super().__init__(timeout=360)

        @discord.ui.button(label="Return to lobby", style=discord.ButtonStyle.grey, emoji=emoji.emojize(":right_arrow_curving_left:", language="alias"))
        async def returnlobby(self, button: discord.ui.Button, interaction: discord.Interaction):
            await self.game.returnToLobby()

        @discord.ui.button(label="Reveal board", style=discord.ButtonStyle.grey,
                           emoji=emoji.emojize(":world_map:", language="alias"))
        async def reveal(self, button: discord.ui.Button, interaction: discord.Interaction):
            button.disabled = True
            await self.msg.edit(content=self.game.coloredstr, view=self)

        async def on_timeout(self) -> None:
            await self.msg.edit(view=None)

    class WordPicker(discord.ui.StringSelect):
        def __init__(self, game: CodenamesGame, guesser: CodenamesCog.Player):
            super().__init__(min_values=1, max_values=25)
            self.game = game
            self.guesser = guesser
            self.options = [discord.SelectOption(label=str(w), value=str(n)) if not w.revealed else discord.SelectOption(label="Revealed", value=str(n), emoji=emoji.emojize(":cross_mark:", language="alias")) for n, w in enumerate(self.game.words)]

        async def callback(self, interaction: discord.Interaction) -> None:
            if not self.guesser.userid == interaction.user.id:
                await utils.embedutil.error(interaction, "You are not the guesser.", delete=5.0)
                return

            nums = map(int, self.values)
            n = 0
            for num in nums:
                card = self.game.words[num]
                card.revealed = True
                if card == self.game.assasin:
                    self.guesser.stats["Times assasinated"] += 1
                    self.guesser.team.eliminated = True
                    logger.debug("assasinated")
                    break
                elif card in self.game.neutrals:
                    self.guesser.stats["Civilians assassinated"] += 1
                    logger.debug("neutral")
                    break
                elif card.team == self.guesser.team:
                    self.guesser.stats["Correct guesses"] += 1
                    logger.debug("correct guess")
                    n += 1
                else:
                    self.guesser.stats["Wrong team guesses"] += 1
                    logger.debug("wrong guess")
                    break
            stat = "Most words guessed in one turn"
            self.guesser.stats[stat] = max(self.guesser.stats[stat], n)

            self.view.stop()

    async def start(self, channel: discord.TextChannel):
        for team in self.teams:
            if not isinstance(team.spymaster, MockPlayer):
                await client.get_user(team.spymaster.userid).send(self.coloredstr)

        while True:
            for team in self.teams:
                if all([any(t.words) for t in self.teams]) and len([t for t in self.teams if not t.eliminated]) > 1:
                    if not team.eliminated:
                        guesser = team.guesser
                        await self.round(channel, guesser)
                else:
                    break
            else:
                continue
            break

        await self.send_table(channel, None)
        teams = [t for t in self.teams if not t.eliminated]
        if len(teams) > 1:
            winner = [team for team in self.teams if not any(team.words)][0]
            desc = "All the words have been uncovered"
        else: # if the other team(s) have simply been eliminated before all the words have been found
            winner = teams[0]
            desc = "The other team(s) have been assassinated."

        for p in winner.players:
            p.stats["Games won"] += 1
        for p in self.lobby.players:
            p.stats["Games played"] += 1

        self.lobby.cog.savePlayers()

        viewObj = self.ReturnToLobby(self, self.msg)
        await self.msg.edit(embed=discord.Embed(title=f"Team {winner.name} won!",
                                               description=desc,
                                               color=winner.color.dccolor),
                                 view=viewObj)

    async def round(self, channel: discord.TextChannel, guesser: CodenamesCog.Player):
        self.channel = channel

        await self.send_table(channel, guesser)


class MockPlayer(CodenamesCog.Player):
    def __init__(self, name):
        super().__init__(client.get_user(617840759466360842))

        self._name = name
        self.userid = random.randrange(100_000_000, 999_999_999)
        client.cogs["CodenamesCog"].users.update({self.userid: self})
        self.ready = True
        # self.userid = 617840759466360842
        # self.color = discord.Color.random()

    @property
    def name(self):
        return self._name

    def __eq__(self, other):
        return other.userid == self.userid


def setup(client):
    client.add_cog(CodenamesCog(client))
