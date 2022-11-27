import random
from typing import List, Type
import nextcord as discord
from nextcord.ext import commands


class Wordlecog(commands.Cog):
    def __init__(self, client, baselogger):
        logger = baselogger.getChild(f"{__name__}Logger")
        self.client = client
        with open("./data/wordlewords.txt", "r") as file:
            self.words = file.readlines()
            logger.debug(f"{len(self.words)} wordle words loaded")

    class WordleGame(discord.ui.View):
        def __init__(self, correct: str, guess: str):
            self.word = correct
            super().__init__(timeout=1800)
            self.verifyGuess(guess)
            self.message = None
            self.embed = None

        def verifyGuess(self, guess: str):  # this hurts
            if guess.lower() == self.word:  # if the guess is correct
                self.embed = discord.Embed(title="Good job!", description=f"You guessed correctly, it was {self.word.upper()}", color=discord.Color.green())
                for child in self.children:
                    child.disabled = True
                return

            if len(self.children) == 25:  # if the guess is wrong and the game is over
                self.embed = discord.Embed(title="Too bad!", description=f"You guessed {guess.upper()}.\nThe word was {self.word.upper()}", color=discord.Color.red())
                for child in self.children:
                    child.disabled = True

            else: # if the guess is wrong and the game is not over
                # letters: List[Type[Wordlecog.WordleGame.Gomb] | None] = [None] * 5  # typehinting example hehe
                letters = [None] * 5
                rightletters = list(self.word)  # this is a list of the letters in the word, for yellow letter checking

                for i, (guessletter, rightletter) in enumerate(zip(guess.lower(), self.word)):
                    if guessletter == rightletter:  # if the guess is right, in the right place
                        color = discord.ButtonStyle.green
                        rightletters.remove(guessletter)  # remove the letter from the list of right letters
                        letters[i] = self.Gomb(guessletter.upper(), color, False, self)  # create a button with the letter and color green
                locked = False

                for i, guessletter in enumerate(guess):  # if the guess is in the word
                    if guessletter in rightletters:
                        color = discord.ButtonStyle.red
                        rightletters.remove(guessletter)  # remove the letter from the list of right letters
                    else:
                        color = discord.ButtonStyle.gray  # if the guess is wrong
                    letters[i] = letters[i] or self.Gomb(guessletter.upper(), color, locked, self)  # if the button is created (green) use that, if not created yet, create it

                [self.add_item(i) for i in letters]  # add the buttons to the view

        async def render(self):
            await self.message.edit(view=self, embed=self.embed)  # edit the message with the new view

        class Gomb(discord.ui.Button):  # this is a button that has a letter and a color
            def __init__(self, letter:str, color:discord.ButtonStyle, locked:bool, game):
                self.game = game
                super().__init__(style=color, label=letter, disabled=locked)

            async def callback(self, interaction: discord.Interaction):
                modal = self.game.WordGuessModal(self.game)
                await interaction.response.send_modal(modal)  # send the modal to the user

        class WordGuessModal(discord.ui.Modal):
            def __init__(self, game):
                self.game = game
                super().__init__(title="Guess a word", auto_defer=True)

                self.guess = discord.ui.TextInput(max_length=5, min_length=5, label="Guess a word")
                self.add_item(self.guess)

            async def callback(self, ctx):
                guess = self.guess.value
                self.game.verifyGuess(guess)
                await self.game.render()

    @discord.slash_command(name="wordle", description="Start a game of wordle. Input a word to start guessing.")
    async def wordle(self, ctx, guess: str = discord.SlashOption(name="first_guess", required=True)):
        if len(guess) != 5:
            await ctx.send("Guess must be a 5 letter word.", delete_after=5)
            return
        game = Wordlecog.WordleGame(random.choice(self.words).strip(), guess)
        game.message = await ctx.send("Click on any of the letters to continue guessing.", view=game)


def setup(client, baselogger):
    client.add_cog(Wordlecog(client, baselogger))
