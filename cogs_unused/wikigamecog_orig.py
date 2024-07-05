from __future__ import annotations
import os
import string

from utils.antimakkcen import antimakkcen
from typing import Optional
import nextcord as discord
import nextcord.errors
from nextcord.ext import commands
import json
import emoji
from random import randint, choice
from collections import defaultdict
from utils.mentionCommand import mentionCommand
from utils.paginator import Paginator
from utils import embedutil

root = os.getcwd()


class WikiGameCog(commands.Cog):
    def __init__(self, client1: discord.Client):
        global logger
        global client
        client = client1  # cant be both param and global
        logger = client.logger.getChild(f"{self.__module__}")
        self.users: dict[int, WikiGameCog.Player] = {}
        self.lobbies: dict[str, WikiGameCog.Lobby] = {}
        os.makedirs(r"./data", exist_ok=True)
        try:
            with open(root + r"/data/touilUsers.txt", "r") as f:
                tempusers = json.load(f)
                logger.debug(f"{len(tempusers)} player profiles loaded")
                for k in tempusers:
                    self.users[int(k["userid"])] = self.Player(k)
        except OSError as e:
            logger.warning(e)
            with open(root + r"/data/touilUsers.txt", "w") as f:
                json.dump([], f)
                logger.info(f"{f} created")
        except json.decoder.JSONDecodeError as e:
            logger.error(f"Error reading users: {e}")
            pass

    @discord.slash_command(description="Commands for the games")
    async def wikigame(self, interaction):
        pass

    @wikigame.subcommand(name="stats", description="Shows your stats across all the games you´ve played.")
    async def showstats(self, ctx, user: discord.User=discord.SlashOption(name="user", description="See someone else´s profile.", required=False, default=None)):
        if user is None:
            user = ctx.user
        player = self.getPlayer(user)
        embedVar = discord.Embed(title=f"__{user.display_name}'s stats__", color=user.color)
        if len(player.stats.keys()) == 0:
            embedVar.add_field(name="Empty", value="Looks like this user has not played Wikigame before. Encourage them by inviting them to a game!")
        for k,v in player.stats.items():
            embedVar.add_field(name=k, value=v)
        await ctx.send(embed=embedVar)

    async def manage_words(self, ctx: discord.Interaction, player, lobby):
        player: WikiGameCog.Player = player
        pagi = Paginator(  # TODO replace with Inventory
            func=lambda pagi:
            discord.Embed(
                title=f"{player.name}'s words (Page {max(1,pagi.page+1)}/{max(1,pagi.maxpages)})",
                description=("\n".join(pagi.slice_inventory()) or "Looks like you don't have any words yet! Add some with the button below!"),
            ),
            select=self.RemoveWordSelect,
            inv=player.words,
            itemsOnPage=25)

        pagi.mergeview(self.AddWordView(pagi))
        pagi.lobby = lobby
        await pagi.render(ctx, ephemeral=True, edit=False)

    class AddWordView(discord.ui.View):
        def __init__(self, pagi):
            super().__init__(timeout=pagi.timeout)
            self.pagi: Paginator = pagi

        @discord.ui.button(label="Add word", style=discord.ButtonStyle.primary, emoji=emoji.emojize(":plus:"))
        async def add_word(self, button: discord.ui.Button, interaction: discord.Interaction):
            # await interaction.response.defer()
            await interaction.response.send_modal(self.AddWordModal(self.pagi))

        class AddWordModal(discord.ui.Modal):
            def __init__(self, pagi):
                super().__init__(title="Add a word")
                self.pagi: Paginator = pagi
                self.input = discord.ui.TextInput(label="Enter a word", min_length=1, max_length=50)
                self.add_item(self.input)

            async def callback(self, interaction: discord.Interaction):
                if antimakkcen(self.input.value) not in map(antimakkcen, self.pagi.lobby.allwords):
                    self.pagi.inv.append(self.input.value)
                    await self.pagi.render(interaction)
                    await self.pagi.lobby.messageid.edit(embed=self.pagi.lobby.show())
                else:
                    await embedutil.error(interaction, "Word already submitted by someone")

    class RemoveWordSelect(discord.ui.Select):
        def __init__(self, pagi: Paginator):
            super().__init__(min_values=1, max_values=max(1, len(pagi.slice_inventory())),
                             placeholder="Select words to remove",
                             options=([discord.SelectOption(label=word, emoji=emoji.emojize(":cross_mark:")) for word in pagi.slice_inventory()] or [discord.SelectOption(label="None")]),
                             disabled=not pagi.inv)
                # discord.SelectOption(label="Close", value="touil.removeword.exit", emoji=emoji.emojize(":cross_mark:"))
            # ])
            self.pagi: Paginator = pagi

        async def callback(self, interaction: discord.Interaction):
            # if self.values[0] != "touil.removeword.exit":
            for word in self.values:
                self.pagi.inv.remove(word)
            await self.pagi.render(interaction)
            await self.pagi.lobby.messageid.edit(embed=self.pagi.lobby.show())
            # else:
                # msg = await self.pagi.msg.delete()

    @wikigame.subcommand(name="help", description="Shows the help manual to this game and the bot.")
    async def showhelp(self, ctx: discord.Interaction):
        helptext = {
            "commands": f"""{mentionCommand(client,'wikigame start')} makes a lobby for a game. You can set the lobby
            to private to only allow people with an invite code.
            
            {mentionCommand(client,'wikigame join')} <CODE> joins an existing lobby.
            
            Use {mentionCommand(client,'wikigame leave')} to leave the lobby you are currently in.
            
            {mentionCommand(client,'wikigame stats')} shows your or someone else's statistics across all games.  
            """,

            "rules": """Before starting the game, everyone picks a few interesting wikipedia articles that are less known.
            The wikipedia's [__Random article__](https://en.wikipedia.org/wiki/Special:Random) button may be used but the articles may be less interesting.
             
            Each turn a guesser is chosen, whose job will be to find the one player telling the truth.   
            Also each turn an article is picked, from the pool of everyone's submitted articles.
             
            Only the person who submitted the article will be able to tell the truth about the chosen article, as they
            have chosen it and (hopefully) read about it so they can describe it to the guesser.
            The other players however do not know anything about the article and will have to convince the guesser
            that they do, by coming up with plausible sounding explanations, stories and facts about the chosen word.
            
            After the guesser has listened to everyone's attempts at convincing them of their truth, the guesser has
            to pick a player who they think is telling the truth and is the owner of the article.
            If they guess correctly, they are awarded a point. Otherwise the person who fooled the guesser gets a point.""",

            "credits": """The game is based on the web game show **Two of these people are lying** presented on YouTube by
                     The Technical Difficulties
                     https://www.techdif.co.uk/
                     https://www.youtube.com/playlist?list=PLfx61sxf1Yz2I-c7eMRk9wBUUDCJkU7H07
                     Bot and game adaptation created by @theonlypeti
                     https://github.com/theonlypeti"""
        }

        class HelpTopicSelector(discord.ui.Select):
            def __init__(self):
                opts = [discord.SelectOption(label="Commands", description="Gives help about the game commands.", value="commands",emoji=emoji.emojize(":paperclip:")),
                        discord.SelectOption(label="Rules", description="Explains the rules of this game.", value="rules", emoji=emoji.emojize(":ledger:")),
                        discord.SelectOption(label="Credits", description="Links and about.", value="credits", emoji=emoji.emojize(":globe_with_meridians:")),
                        discord.SelectOption(label="Close", value="0", emoji=emoji.emojize(":cross_mark:"))]
                super().__init__(options=opts)

            async def callback(self, interaction: discord.Interaction):
                if self.values[0] == "0":
                    await interaction.response.edit_message(content="Cancelled", view=None, embed=None, delete_after=5.0)
                else:
                    await interaction.edit(embed=discord.Embed(title=f"About {self.values[0]}", description=helptext[self.values[0]], color=interaction.user.color))

        embedVar = discord.Embed(title="What do you wish to learn about?", description="Pick a topic below:", color=ctx.user.color)
        viewObj = discord.ui.View()
        viewObj.add_item(HelpTopicSelector())
        await ctx.send(embed=embedVar, view=viewObj)

    class LobbyView(discord.ui.View):
        def __init__(self, cog, lobby):
            self.cog = cog
            self.lobby = lobby
            super().__init__(timeout=600)

        @discord.ui.button(style=discord.ButtonStyle.green,emoji=emoji.emojize(":inbox_tray:"))
        async def joinbutton(self, button, ctx):
            player = self.cog.getPlayer(ctx.user)
            await self.lobby.addPlayer(ctx, player)
            logger.debug(f"{ctx.user.name} joined")

        @discord.ui.button(style=discord.ButtonStyle.red, emoji=emoji.emojize(":outbox_tray:"))
        async def leavebutton(self, button, ctx):
            player = self.cog.getPlayer(ctx.user)
            await self.lobby.removePlayer(ctx, player)
            logger.debug(f"{ctx.user.name} left")

        @discord.ui.button(style=discord.ButtonStyle.grey, emoji=emoji.emojize(":memo:"), disabled=False)
        async def wordsbutton(self, button, ctx):
            player = self.cog.getPlayer(ctx.user)
            if player.ready:
                await embedutil.error(ctx, "You may not change your words while marked ready")
                return
            if not player.inLobby:
                await embedutil.error(ctx, "You are not in a lobby!")
                return
            await self.cog.manage_words(ctx, player, self.lobby)
            logger.debug(f"{ctx.user.name} clicked addwords")

        @discord.ui.button(style=discord.ButtonStyle.green,emoji=emoji.emojize(":check_mark_button:"))
        async def readybutton(self, button, ctx: discord.Interaction):
            player = self.cog.getPlayer(ctx.user)
            if player.inLobby:
                logger.debug(f"{ctx.user.name} requested ready/unready")
                if player.words:
                    player.ready = not player.ready
                    await self.lobby.readyCheck()
                else:
                    await ctx.send(embed=discord.Embed(title="You do not have any words",color=discord.Color.red()), ephemeral=True, delete_after=5.0)
            else:
                await ctx.send(embed=discord.Embed(title="You are not in this lobby.",color=discord.Color.red()),ephemeral=True,delete_after=5.0)
                logger.debug(f"{ctx.user.name} clicked ready on not joined lobby")

        @discord.ui.button(style=discord.ButtonStyle.blurple,emoji=emoji.emojize(":right_arrow:"), disabled=True)
        async def startbutton(self, button, ctx):
            await ctx.response.defer()
            if self.lobby.lobbyleader == ctx.user:
                try:
                    await self.lobby.managemsg.edit(embed=None,view=None,content="Game started.", delete_after=5.0)
                except nextcord.errors.NotFound:
                    pass
                await self.lobby.start(ctx)
            else:
                await ctx.send(embed=discord.Embed(title="You are not the leader of this lobby.", color=discord.Color.red()), ephemeral=True)
                logger.info(f"{ctx.user.name} wanted to start game when not lobbyleader")

        async def on_timeout(self) -> None:
            await self.lobby.disband()
            del self.cog.lobbies[self.lobby.code]
            del self

    class KickPlayerDropdown(discord.ui.Select):
        def __init__(self, lobby, cog):
            self.lobby: WikiGameCog.Lobby = lobby
            self.cog: WikiGameCog = cog
            # self.players = self.lobby.players[1:]
            self.players = [player for player in self.lobby.players if player.userid != self.lobby.lobbyleader.id] #first player later doesnt have to be the lobbyleader
            optionslist=list([discord.SelectOption(label=i.name, value=i.userid) for i in self.players])
            optionslist.append(discord.SelectOption(label="Cancel", value="-1", emoji=emoji.emojize(":cross_mark:")))
            super().__init__(options=optionslist,placeholder="Pick a player to kick")

        async def callback(self, inter):
            result = self.values[0]
            if result != "-1":
                logger.debug(f"kicking player number {result}")
                tokick = self.cog.getPlayer(int(self.values[0]))
                await self.lobby.removePlayer(inter, tokick)
                await self.lobby.messageid.edit(embed=self.lobby.show())
            await inter.edit(view=self.cog.MngmntView(self.lobby, self.cog))

    class MngmntView(discord.ui.View):
        def __init__(self, lobby, cog):
            self.lobby = lobby
            self.cog = cog
            super().__init__(timeout=None)

        @discord.ui.button(label="Kick Player",style=discord.ButtonStyle.red, emoji=emoji.emojize(":boot:", language="alias"))
        async def kickbutton(self, button, inter):
            viewObj = discord.ui.View()
            viewObj.add_item(self.cog.KickPlayerDropdown(self.lobby,self.cog))
            await inter.edit(view=viewObj)

        @discord.ui.button(label="Resend lobby message",style=discord.ButtonStyle.grey,emoji=emoji.emojize(":right_arrow_curving_left:"))
        async def resendbutton(self, button, inter):
            await self.lobby.messageid.edit(embed=discord.Embed(title="The lobby you are looking for has moved",description="see below"),view=None,delete_after=30.0)
            lobbymessage = await inter.channel.send(embed=discord.Embed(title="Generating lobby..."))
            self.lobby.messageid = lobbymessage
            await self.lobby.messageid.edit(embed=self.lobby.show(), view=self.cog.LobbyView(self.cog,self.lobby))

    @wikigame.subcommand(name="start", description="Makes a lobby for a Two of us is lying game.")
    async def makeLobby(self, ctx:discord.Interaction, private=discord.SlashOption(name="private", description="Do you wish to create a public lobby or a private one",required=False,default="Public",choices=("Public","Private"))):
        user = self.getPlayer(ctx.user)
        if user.inLobby:
            await ctx.send(embed=discord.Embed(title=f"You are already in a lobby. Try {mentionCommand(client,'wikigame leave')}", color=discord.Color.red()),ephemeral=True)
            return
        else:
            lobbymessage = await ctx.channel.send(embed=discord.Embed(title="Generating lobby..."))
            newLobby: WikiGameCog.Lobby = self.Lobby(ctx, lobbymessage, self, private=(private == "Private"))
            # newLobby.players.append(user)

            self.lobbies.update({newLobby.code:newLobby})
            await ctx.send(embed=discord.Embed(title=f"You are now the lobby leader of ||{newLobby.code}||",
                                               description="You can remove players from the lobby with the **Kick player** button\n\nIf the channel is spammed over, you can resend the lobby message with the **Resend lobbymsg** button\n\nWhen everybody is ready, a start game ({}) button will appear under the lobby message.".format(emoji.emojize(":right_arrow:"))),ephemeral=True,view=self.MngmntView(newLobby,self))
            newLobby.managemsg = await ctx.original_message()

            await newLobby.addPlayer(ctx, user)
            user.inLobby = newLobby.code
            viewObj = self.LobbyView(self, newLobby)
            if private == "Private":
                viewObj.children[0].disabled=True

            await lobbymessage.edit(embed=newLobby.show(), view=viewObj)

    class Lobby(object):
        def __init__(self, ctx: discord.Interaction, messageid: discord.Message, cog, private=False):
            self.cog = cog
            self.maxplayers: int = 25
            self.minplayers: int = 3
            self.players: list[WikiGameCog.Player] = []
            self.private: bool = private
            while (code := "".join([choice(string.ascii_uppercase) for _ in range(4)])) in self.cog.lobbies:
                logger.info(f"generating lobbycode {code}")
                continue
            self.code: int = code
            self.ongoing: bool = False
            self.managemsg: discord.Message = None
            self.messageid = messageid
            self.lobbyleader = ctx.user
            self.cog.lobbies[self.code] = self

        def __str__(self):
            return self.code+"+".join(map(str, self.players))

        @property
        def allwords(self):
            return sum([p.words for p in self.players], [])

        def show(self) -> discord.Embed:
            name = self.lobbyleader.display_name
            EmbedVar = discord.Embed(
                title=f"{name}'s {('Public' if not self.private else 'Private')} Lobby" + (f" ({len(self.players)}/{self.maxplayers})" if self.maxplayers else ""),
                description=("Game already running." if self.ongoing else f"use **{mentionCommand(client,'wikigame join')} {self.code}** or click the join icon") if not self.private else f"ask the lobby leader for the code, \nthen use {mentionCommand(client,'wikigame join')} *CODE*, don't worry noone will see that.") #extra space deliberate, otherwise looks stupid
            EmbedVar.set_footer(text="{} join, {} leave, {} add words, {} ready".format(emoji.emojize(":inbox_tray:"), emoji.emojize(":outbox_tray:"), emoji.emojize(":memo:"),emoji.emojize(":check_mark_button:")))
            i = 1
            for i,player in enumerate(self.players, start=1):
                EmbedVar.add_field(name=f"{i}. {player}", value="Ready?"+(emoji.emojize(":cross_mark:"), emoji.emojize(":check_mark_button:"))[bool(player.ready)],inline=False)
            while i<self.minplayers and i<=25:
                EmbedVar.add_field(name="[Empty]", value="Ready? "+emoji.emojize(":cross_mark:"), inline=False)
                i+=1
            return EmbedVar

        async def readyCheck(self):
            readys = [i.isReady() for i in self.players]
            # uniqueIcons = len({i.icon for i in self.players}) == len(self.players)
            viewObj = self.cog.LobbyView(self.cog, self)
            viewObj.children[0].disabled = bool(self.private)
            if not self.ongoing:
                # if all(readys) and len(readys)>1 and uniqueIcons:
                if all(readys) and len(readys)>=self.minplayers:
                    viewObj.children[-1].disabled = False
                    logger.debug("all players ready to go")
                    await self.messageid.edit(embed=self.show(), view=viewObj) #KEEP THIS HERE!!! NOT DUPLICATE
                    return True
                else:
                    viewObj.children[-1].disabled = True
                    logger.debug("not all players ready to go")
            else:
                for child in viewObj.children:
                    child.disabled = True
            await self.messageid.edit(embed=self.show(), view=viewObj)
            return False

        async def start(self, ctx) -> None:
            #if await self.readyCheck(): #hold on why is it like this #looks like this is working as intended
            if True:
                if not self.ongoing:
                    self.ongoing = True
                    await self.readyCheck() #this is needed to update the view
                    game = WikiGame(self) #create game
                    await game.start(ctx.channel) #start game #if i do ctx.send it breaks after 15mins cuz interactions.
                    self.cog.savePlayers()
                else:  #should not be achievable as the start button should be disabled when game is ongoing, maybe delete
                    await ctx.send(embed=discord.Embed(title="A game is already running.", color=discord.Color.red()), ephemeral=True)
                    logger.warning("ongoing game")

        async def addPlayer(self, ctx: discord.Interaction, player: WikiGameCog.Player) -> None:
            if not self.maxplayers or len(self.players) < self.maxplayers:
                if not self.ongoing:
                    if not player.inLobby:
                        player.inLobby = self.code
                        # player.words = deepcopy(list(string.ascii_lowercase))
                        await embedutil.success(ctx, "Joined")
                    else:
                        await embedutil.error(ctx, f"You are already in a lobby. Try {mentionCommand(client,'wikigame leave')}", delete=10)
                        logger.debug("already in lobby")
                        return
                    #await self.messageid.edit(embed=self.show()) #redundant: gets updated in readyCheck again too so
                    self.players.append(player)
                    await self.readyCheck()
                else:
                    logger.error("ongoing game") #shouldnt be a possibility, remove buttons from lobbymsg after start
            else:
                await embedutil.error(ctx, "Lobby is already full!")

        async def removePlayer(self, ctx: discord.Interaction, player: WikiGameCog.Player) -> None:
            if not self.ongoing:
                if player in self.players:
                    self.players.remove(player)
                    player.inLobby = False
                    player.ready = False
                    leader = self.cog.getPlayer(self.lobbyleader)
                    if player == leader:
                        await self.disband()
                        return
                    else:
                        # await self.messageid.edit(embed=self.show()) #readycheck should also rerender
                        await self.readyCheck()
                else:
                    await ctx.send(embed=discord.Embed(title="You are not in this lobby.", color=discord.Color.red()), ephemeral=True)
            else:
                print("game ongoing")

        async def disband(self):
            for player in self.players:
                player.inLobby = False
                player.ready = False
            try:
                await self.managemsg.delete()
            except Exception:
                try:
                    await self.managemsg.edit(embed=discord.Embed(title="Lobby disbanded."), view=None, delete_after=5.0)
                except Exception:
                    pass
            try:
                await self.messageid.edit(embed=discord.Embed(title="Lobby disbanded.", description=f"Make a new one with {mentionCommand(client,'wikigame start')}"), view=None, delete_after=30.0)
            except AttributeError: #disbanding after a game cannot edit message as it doesnt exist anymore
                pass
            try:
                del self.cog.lobbies[self.code]
            except KeyError:
                logger.warning(f"{self.code} already deleted, why is still wanting to timeout and disband?")

    async def findLobby(self, lobbyid: str) -> Optional[Lobby]:
        if not lobbyid:
            return None
        else:
            if lobbyid in self.lobbies:
                return self.lobbies[lobbyid]
            else:
                logger.info("lobby not found inside findlobby") #NO need to print. it is done a few lines lower, line 678 if nothing moved
                return None

    @wikigame.subcommand(name="join", description="Join an existing lobby.")
    async def joinlobby(self, ctx: discord.Interaction, lobbyid:str =discord.SlashOption(name="lobbyid", description="A lobby´s identification e.g. ABCD", required=True)):
        user = self.getPlayer(ctx.user)
        lobby = await self.findLobby(lobbyid.upper())
        if lobby:
            await lobby.addPlayer(ctx, user)
        else:
            await ctx.send(embed=discord.Embed(title=f"Lobby \"**{lobbyid}**\" not found", color=ctx.user.color), ephemeral=True)

    @wikigame.subcommand(name="leave", description="Leave the lobby you are currently in.")
    async def leavelobby(self, ctx: discord.Interaction):
        user = self.getPlayer(ctx.user)
        lobby = await self.findLobby(user.inLobby)
        if lobby:
            await ctx.send(embed=discord.Embed(title=f"Left {lobby.lobbyleader.name}'s lobby.", color=ctx.user.color), ephemeral=True)
            await lobby.removePlayer(ctx.channel, user)
            await lobby.managemsg.edit(view=self.MngmntView(lobby, self)) #removing the player from the kick dropdown
        else:
            await embedutil.error(ctx, "You are not currently in a lobby.")

    def getPlayer(self, dcUser: int | discord.Member | "WikiGameCog.ClovecePlayer"):
        if isinstance(dcUser, int):
            lookingfor = dcUser
        elif isinstance(dcUser, discord.Member):
            lookingfor = dcUser.id
        elif isinstance(dcUser, WikiGameCog.Player): #just keep it
            lookingfor = dcUser.userid
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
        with open(root + r"/data/touilUsers.txt", "w") as file:
            json.dump([v.toDict() for k, v in self.users.items()], file, indent=4)
        logger.info("saved")

    class Player(object):
        def __init__(self, discorduser: discord.Member):
            if isinstance(discorduser, dict):
                for k, v in discorduser.items():
                    if k == "stats":
                        setattr(self,k, defaultdict(int))
                        self.stats.update(v)
                    else:
                        setattr(self, k, v)
            else:
                self.stats: dict[str, int] = defaultdict(int)
                self.userid = discorduser.id
            self.ready = False
            self.words: list[str] = []
            self.inLobby = False

        @property
        def name(self):
            return client.get_user(self.userid).display_name

        def isReady(self):
            return self.words and self.ready

        def __hash__(self):
            return hash(self.userid)

        def __repr__(self):
            return f"{self.__dict__}"

        def __eq__(self, other):
            logger.debug(other)
            if isinstance(other, self.__class__):
                return self.userid == other.userid
            else:
                raise NotImplementedError(f"Comparison between {type(self)} and {type(other)}")

        def __str__(self):
            return f"{self.name} ({len(self.words)} words)"

        def toDict(self):
            return {k: v for k, v in self.__dict__.items() if k not in ("words", "inLobby", "ready")}

class WikiGame():
    def __init__(self, lobby: WikiGameCog.Lobby):
        self.lobby = lobby
        for player in self.lobby.players:
            player.stats["Games played"] += 1
        self.players: list[WikiGameCog.Player] = None
        self.initplayers()
        # self.allwords = sum([p.words for p in self.players],[])
        self.guesser: WikiGameCog.Player = None
        self.points = {p.userid:0 for p in self.players}


    @property
    def allwords(self):
        return sum([p.words for p in self.players], [])

    @property
    def words(self):
        # return self.allwords - self.guesser.words //no operand - for list
        # return filter(lambda word: word not in self.guesser.words, self.allwords) //filter has no len
        # return set(allwords).difference(set(self.guesser.words)) //set cant be subscripted
        return [word for word in self.allwords if word not in self.guesser.words]
    @property
    def explainers(self) -> list[WikiGameCog.Player]:
        return [player for player in self.players if player != self.guesser]

    def initplayers(self):
        if not self.players:
            self.players = self.lobby.players
            # self.players.insert(0, WikiGameCog.Player(client.user))
            # self.players[0].words = ["dummy"]

    async def returnToLobby(self):
        await self.lobby.messageid.edit(
            embed=discord.Embed(title="The lobby you are looking for has moved", description="see below"),
            view=None, delete_after=30.0)
        lobbymessage = await self.channel.send(embed=discord.Embed(title="Generating lobby..."))
        self.lobby.messageid = lobbymessage
        self.lobby.ongoing = False
        self.lobby.players = self.players
        for player in self.lobby.players:
            player.ready = False
        await self.lobby.readyCheck()
        # await self.lobby.messageid.edit(embed=self.lobby.show(), view=self.lobby.cog.LobbyView(self.lobby.cog, self.lobby))

    async def start(self, channel: discord.TextChannel):
        await self.round(channel)
        ...

    async def round(self, channel: discord.TextChannel):
        self.channel = channel
        # self.initplayers()
        if not all(player.words for player in self.players):
            await embedutil.error(self.channel, "Someone has ran out of words. Find and submit new articles to continue the game.", delete=10)
            await self.returnToLobby()
            return
        self.guesser = self.players.pop()
        self.players.insert(0, self.guesser)  #TODO this is stupid tbh
        self.truth = choice(self.explainers)
        self.word = choice(self.truth.words)
        self.truth.words.remove(self.word)
        # for player in self.explainers:
        #     player // for dming them or showing an ephemeral ws to them
        viewObj = discord.ui.View(timeout=None)
        viewObj.add_item(GuesserDropdown(self))
        await self.channel.send(embed=discord.Embed(title=f"{self.guesser.name} is guessing", description=f"The word is ||{self.word}||"), view=viewObj)


class GuesserDropdown(discord.ui.Select):
    def __init__(self, game):
        super().__init__()
        self.game: WikiGame = game
        self.placeholder = "Who tells the truth?"
        self.options = [discord.SelectOption(label=player.name, value=f"{player.userid}") for player in self.game.explainers]

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id == self.game.guesser.userid:
            chosen: WikiGameCog.Player = self.game.lobby.cog.getPlayer(int(self.values[0]))
            if chosen == self.game.truth:
                embedVar = discord.Embed(title="Correct!", description=f"{self.game.truth.name} was telling the truth",
                                         color=discord.Color.green())
                self.game.points[self.game.guesser.userid] += 1
                self.game.lobby.cog.getPlayer(self.game.guesser).statistics["Correct guesses"] += 1
            else:
                embedVar = discord.Embed(title=f"{chosen.name} is incorrect!",
                                         description=f"||{self.game.truth.name} was telling the truth||",
                                         color=discord.Color.red())
                self.game.points[chosen.userid] += 1
                self.game.lobby.cog.getPlayer(self.game.guesser).statistics["Incorrect guesses"] += 1
                self.game.lobby.cog.getPlayer(chosen).statistics["Fooled someone"] += 1
            for k, v in self.game.points.items():
                embedVar.add_field(name=self.game.lobby.cog.getPlayer(k).name, value=v)
            await interaction.edit(embed=embedVar, view=self.NextButton(self.game))
        else:
            await embedutil.error(interaction, "It is not your turn to guess!")
        self.game.lobby.cog.savePlayers()

    class NextButton(discord.ui.View):
        def __init__(self, game: WikiGame):
            super().__init__(timeout=None)
            self.game = game

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            return interaction.user.id == self.game.guesser.userid

        @discord.ui.button(label="Next round", emoji=emoji.emojize(":right_arrow:"), style=discord.ButtonStyle.green)
        async def nextbutton(self, button, interaction: discord.Interaction):
            await interaction.message.delete()
            await self.game.round(interaction.channel)

        @discord.ui.button(label="Back to Lobby")
        async def lobby(self, button, interaction: discord.Interaction):
            await interaction.message.delete()
            await self.game.returnToLobby()


def setup(client):
    client.add_cog(WikiGameCog(client))
