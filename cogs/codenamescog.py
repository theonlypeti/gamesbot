import random
from datetime import timedelta, datetime
from tabulate import tabulate
import utils.embedutil
import nextcord as discord
import json
import emoji
from utils.Inventory import Inventory
from utils.lobbyutil.lobbycog import LobbyCog, HelpCategory, Game, AdminView
from utils.lobbyutil.teamutil import TeamLobby, TeamPlayer, Team, MockPlayer
from utils import Colored


class CodenamesCog(LobbyCog):
    def __init__(self, client: discord.Client):

        super().__init__(client, "Codenames", minplayers=4, gameclass=CodenamesGame, playerclass=CodenamesPlayer, lobbyclass=CodenamesLobby)
        self.client = client
        self.teams = sorted([Team(col) for col in Colored.Colored.list().values()], key=lambda t: t.color.emoji_square)

        self.credits = """The game is based on the tabletop board game **Codenames** by Czech Games Edition
                https://czechgames.com/en/codenames/
                https://czechgames.com/en/home/
                Bot and game adaptation created by @theonlypeti
                https://github.com/theonlypeti"""

        self.rules = """Each turn, one player from a team will be the __spymaster__ and the rest will be __guessers__.

                The spymaster will give a **one-word** clue and a number. The clue relates to the words on the board and the number indicates how many words the clue relates to.
                
                The guessers then together try to guess the words for their team on the board based on the clue. They must avoid words that belong to the opposing team, neutral words, and the __assassin word__.
                
                You may guess more words at a time. If a spy guesses a word that belongs to their team, they score a point. If they guess a word that belongs to the opposing team or a neutral word, their turn ends immediately.
                
                If they guess the assassin word, their team loses the game immediately.
                
                The game continues until one team has guessed all their words correctly, or until one team has guessed the assassin word."""

        self.add_help_category(HelpCategory(label="Clues",
                                            description="Clarifies what constitutes as a valid clue for the game.",
                                            emoji=emoji.emojize(":mag:", language="alias"),
                                            helptext="""The clue must be a single word. It must not be a word on the board.
             
            It may not be a word that is a prefix or a part of any of the words on the board.
             
            It may not be for example the letter "s" to denote all the words that begin with "s" on the board.
             
            The clue may be for example (Apple, 2) for the words: "pie" and "tree". """))


class CodenamesMngmntView(AdminView):
    def __init__(self, lobby: "CodenamesLobby"):
        super().__init__(lobby)
        for i in self.children:  # type: discord.ui.Button
            if i.custom_id == "mobilebutton":
                i.style = discord.ButtonStyle.green if self.lobby.mobile else discord.ButtonStyle.red
                i.emoji = emoji.emojize(":no_mobile_phones:", language="alias") if not self.lobby.mobile else emoji.emojize(":mobile_phone:", language="alias")
                break

    @discord.ui.button(label="Mobile UI", style=discord.ButtonStyle.green, emoji=emoji.emojize(":mobile_phone:", language="alias"), custom_id="mobilebutton")
    async def mobilebutton(self, button: discord.ui.Button, inter: discord.Interaction):
        """ANSII color codes do not render colored text on mobile,
        will use colorful emojis instead (this may break table formatting though)"""
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

    @discord.ui.button(label="Testing", style=discord.ButtonStyle.grey) # remove
    async def addmockplayers(self, button, inter):
        self.lobby.players.extend([MockPlayer(f"Player {i}", cog=self.lobby.cog) for i in range(1, 4)])
        for player in self.lobby.players[-3:]:
            self.lobby.teams[1].join(player)    
        await self.lobby.readyCheck()
        await utils.embedutil.success(inter, "Added 3 mock players")


class CodenamesLobby(TeamLobby):
    def __init__(self, interaction, cog, private, game, minplayers, maxplayers):

        self.teams_info_text = \
            f"""{emoji.emojize(':information_source:', language='alias')} The first person in the team will be responsible for casting the guesses.
They should discuss these choices with their teammates (except spymaster) before picking the words.\n
{emoji.emojize(':information_source:', language='alias')} The last person in the team will be the spymaster. They will be responsible for giving the clue.
If you wish to be the spymaster, repick your own team to be placed at the end."""

        super().__init__(interaction, cog, private, adminView=CodenamesMngmntView, game=game, minplayers=minplayers, maxplayers=maxplayers)

        self.players: list[CodenamesPlayer] = self.players  # this is just to override the typehint of the attr

        with open(self.cog.client.root + r"/data/codenamesWords.json", "r", encoding="UTF-8") as json_file:
            self.words = json.load(json_file)

        self.mobile = True

    def show_players(self, EmbedVar: discord.Embed) -> discord.Embed:

        i = 1
        for team in self.teams:
            if team:
                for n, player in enumerate(team.players, start=1):
                    EmbedVar.add_field(name=f"{i}. {player}", value="Ready? " + (
                        emoji.emojize(":cross_mark:"), emoji.emojize(":check_mark_button:"))[bool(player.ready)], inline=False)
                    i += 1

                if len(team.players) > 1:
                    EmbedVar.set_field_at(i - n - 1, name=EmbedVar.fields[i - n - 1].name + " (guesser)",
                                          value=EmbedVar.fields[i - n - 1].value, inline=False)
                    EmbedVar.set_field_at(len(EmbedVar.fields) - 1, name=EmbedVar.fields[-1].name + " (spymaster)",
                                          value=EmbedVar.fields[-1].value, inline=False)

        for n, player in enumerate(filter(lambda p: not p.team, self.players), start=1):
            EmbedVar.add_field(name=f"{i}. {player}", value="Ready? " + (
            emoji.emojize(":cross_mark:"), emoji.emojize(":check_mark_button:"))[bool(player.ready)], inline=False)
            i += 1

        while i - 1 < self.minplayers:
            EmbedVar.add_field(name="[Empty]", value=f"Ready? {emoji.emojize(':cross_mark:')}", inline=False)
            i += 1

        return EmbedVar

    def readyCondition(self):
        readys = [i.is_ready() for i in self.players]
        teams = [t for t in self.teams if t]  # remove empty teams
        if (all(readys)  # everyone is ready
                and len(self.players) >= self.minplayers  # enough players
                and all([len(t.players) >= t.minplayers for t in teams])  # enough players in each team
                and len(teams) >= 2):  # enough teams
            return True
        return False


class CodenamesPlayer(TeamPlayer):
    def __init__(self, discorduser: discord.Member):
        super().__init__(discorduser)

    def __eq__(self, other):
        # logger.debug(other.__class__)
        # logger.debug(other.__class__ == MockPlayer("a").__class__)
        # logger.debug(isinstance(other, MockPlayer))
        # logger.debug(MockPlayer("a").__class__)
        if isinstance(other, self.__class__):
            return self.userid == other.userid
        elif isinstance(other, MockPlayer):
            return self.userid == other.userid
        else:
            raise NotImplementedError(f"Comparison between {self.__class__} and {other.__class__}")


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


class CodenamesGame(Game):
    def __init__(self, lobby: CodenamesLobby):
        self.logger = lobby.cog.client.logger
        allwords = random.sample(lobby.words, k=25)  # TIL choices can return duplicates
        self.lobby = lobby
        self.words = []
        self.teams = [t for t in self.lobby.teams if t]
        words_count = len(allwords) // max(len(self.teams), 3)
        for team in self.teams:
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

    async def send_table(self, chann: discord.TextChannel = None, guesser: CodenamesPlayer = None):
        if guesser:
            viewObj = discord.ui.View(timeout=300)
            viewObj.add_item(self.WordPicker(self, guesser))
            embedVar = discord.Embed(title=f"It's team {guesser.team.name}'s turn. ",
                                     description=f"{guesser.name} is guessing. You have {discord.utils.format_dt(datetime.now() + timedelta(minutes=5), style='R')}",
                                     color=guesser.team.color.dccolor)
        else:
            viewObj = None
            embedVar = None


        if not self.msg:
            self.msg = await chann.send(self.hiddenstr, embed=embedVar, view=viewObj)
        else:
            await self.msg.edit(content=self.hiddenstr, embed=embedVar, view=viewObj)
        if guesser:
            if await viewObj.wait():
                self.logger.debug(f"{guesser.name} didn't guess in time")
            else:
                self.logger.debug(f"{guesser.name} did guess in time")
            self.lobby.cog.savePlayers()

    class ReturnToLobby(discord.ui.View):
        def __init__(self, game: "CodenamesGame", msg: discord.Message = None):
            self.game = game
            self.msg = msg
            super().__init__(timeout=360)

        @discord.ui.button(label="Return to lobby", style=discord.ButtonStyle.grey, emoji=emoji.emojize(":right_arrow_curving_left:", language="alias"))
        async def returnlobby(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.game.lobby.ongoing = False
            for player in self.game.lobby.players:
                player.ready = False
            for team in self.game.lobby.teams:
                team.words = []
                team.eliminated = False
            await self.game.lobby.send_lobby(interaction)

        @discord.ui.button(label="Reveal board", style=discord.ButtonStyle.grey, emoji=emoji.emojize(":world_map:", language="alias"))
        async def reveal(self, button: discord.ui.Button, interaction: discord.Interaction):
            button.disabled = True
            await self.msg.edit(content=self.game.coloredstr, view=self)

        async def on_timeout(self) -> None:
            await self.msg.edit(view=None)

    class WordPicker(discord.ui.StringSelect):
        def __init__(self, game: "CodenamesGame", guesser: CodenamesPlayer):
            super().__init__(min_values=1, max_values=25)
            self.logger = game.lobby.cog.client.logger
            self.game = game
            self.guesser = guesser
            self.options = [discord.SelectOption(label=str(w), value=str(n)) if not w.revealed else discord.SelectOption(label="Revealed", value=str(n), emoji=emoji.emojize(":cross_mark:", language="alias")) for n, w in enumerate(self.game.words)]

        async def callback(self, interaction: discord.Interaction) -> None:
            if not self.guesser.userid == interaction.user.id:
                await utils.embedutil.error(interaction, "You are not the guesser.", delete=5.0)
                return
            # print(self.guesser.__dict__)

            nums = map(int, self.values)
            n = 0
            for num in nums:
                card = self.game.words[num]
                card.revealed = True
                if card == self.game.assasin:
                    self.guesser.statistics["Times assasinated"] += 1
                    self.guesser.team.eliminated = True
                    self.logger.debug("assasinated")
                    break
                elif card in self.game.neutrals:
                    self.guesser.statistics["Civilians assassinated"] += 1
                    self.logger.debug("neutral")
                    break
                elif card.team == self.guesser.team:
                    self.guesser.statistics["Correct guesses"] += 1
                    self.logger.debug("correct guess")
                    n += 1
                else:
                    self.guesser.statistics["Wrong team guesses"] += 1
                    self.logger.debug("wrong guess")
                    break
            stat = "Most words guessed in one turn"
            self.guesser.statistics[stat] = max(self.guesser.statistics[stat], n)

            self.view.stop()

    async def start(self, channel: discord.TextChannel):
        for team in self.teams:
            if not isinstance(team.spymaster, MockPlayer):
                await self.lobby.cog.client.get_user(team.spymaster.userid).send(self.coloredstr)

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
        else:  # if the other team(s) have simply been eliminated before all the words have been found
            winner = teams[0]
            desc = "The other team(s) have been assassinated."

        for p in winner.players:
            p.statistics["Games won"] += 1
        for p in self.lobby.players:
            p.statistics["Games played"] += 1

        self.lobby.cog.savePlayers()

        viewObj = self.ReturnToLobby(self, self.msg)
        await self.msg.edit(embed=discord.Embed(title=f"Team {winner.name} won!",
                                               description=desc,
                                               color=winner.color.dccolor),
                                 view=viewObj)

    async def round(self, channel: discord.TextChannel, guesser: CodenamesPlayer):
        self.channel = channel

        await self.send_table(channel, guesser)


def setup(client2):
    global client
    client = client2
    client.add_cog(CodenamesCog(client2))
