from typing import Coroutine, Callable
import emoji
import nextcord as discord
from utils import embedutil
from utils.antimakkcen import antimakkcen
from utils.paginator import Paginator


class Inventory(Paginator):
    # default values need to exist at class-level so the Select constructor (created
    # during Paginator.__init__) can access them via the instance before __init__ runs
    EMPTY_INV = "Looks like you don't have any words yet! Add some with the button below!"
    SEL_PLACEHOLDER = "Select words to remove" #TODO fixxx
    MODAL_LABEL = "Enter words separated by comma (,)"
    MODAL_PLACEHOLDER = "word1, word2, word3, ..."
    MODAL_TITLE = "Add a word"
    DUPLICATE = "This word is already submitted by someone! ({})"

    def __init__(self, items: list = None, on_update: Callable[[], Coroutine] = None, **kwargs):
        super().__init__(
            func=lambda pagi:
            discord.Embed(
                title=f"Words (Page {max(1,pagi.page+1)}/{max(1,pagi.maxpages)})",
                description=("\n".join(pagi.slice_inventory()) or self.EMPTY_INV),
            ),
            select=RemoveWordSelect,
            inv=items,
            itemsOnPage=25)

        self.mergeview(AddWordView(self))
        self.on_update = on_update
        self._inv_to_check = None
        for k, v in kwargs.items():
            setattr(self, k, v)

        self.EMPTY_INV = "Looks like you don't have any words yet! Add some with the button below!"
        self.SEL_PLACEHOLDER = "Select words to remove"
        self.MODAL_LABEL = "Enter words separated by comma (,)"
        self.MODAL_PLACEHOLDER = "word1, word2, word3, ..."
        self.MODAL_TITLE = "Add a word"
        self.DUPLICATE = "This word is already submitted by someone! ({})"

class AddWordView(discord.ui.View):
    def __init__(self, pagi):
        super().__init__(timeout=pagi.timeout)
        self.pagi: Inventory = pagi

    @discord.ui.button(label="Add", style=discord.ButtonStyle.primary, emoji=emoji.emojize(":plus:"))
    async def add_word(self, button: discord.ui.Button, interaction: discord.Interaction):
        # await interaction.response.defer()
        await interaction.response.send_modal(AddWordModal(self.pagi))

    @discord.ui.button(label="Clear list", style=discord.ButtonStyle.primary, emoji=emoji.emojize(":cross_mark:", language="alias"))
    async def clear_words(self, button: discord.ui.Button, interaction: discord.Interaction):
        # await interaction.response.defer()
        self.pagi.inv.clear()
        await self.pagi.render(interaction)
        if self.pagi.on_update:
            await self.pagi.on_update()

class AddWordModal(discord.ui.Modal):
    def __init__(self, pagi):

        super().__init__(title=pagi.MODAL_TITLE)
        self.pagi: Inventory = pagi

        self.input = discord.ui.TextInput(label=pagi.MODAL_LABEL,
                                          min_length=2,
                                          style=discord.TextInputStyle.paragraph,
                                          placeholder=pagi.MODAL_PLACEHOLDER)
        self.add_item(self.input)

    async def callback(self, interaction: discord.Interaction):
        for w in self.input.value.split(","):
            if await self.can_add(interaction, w):
                self.pagi.inv.append(w.strip())
            else:
                return

        await self.pagi.render(interaction)
        if self.pagi.on_update:
            await self.pagi.on_update()

    async def can_add(self, interaction, w):
        return await self.is_duplicate(interaction, w, self.pagi._inv_to_check) and await self.is_appropriate(interaction, w)

    async def is_duplicate(self, interaction, w, inv_to_check=None):
        if not inv_to_check:
            inv_to_check = self.pagi.inv
        if antimakkcen(w.strip().lower()) not in map(str.lower, map(antimakkcen, inv_to_check)): #TODO cache?
            return True
        else:
            await embedutil.error(interaction, self.pagi.DUPLICATE.format(w))
            return False

    async def is_appropriate(self, interaction, w):
        return True

class RemoveWordSelect(discord.ui.Select):
    def __init__(self, pagi: Inventory):
        super().__init__(min_values=1, max_values=max(1, len(pagi.slice_inventory())),
                         placeholder=pagi.SEL_PLACEHOLDER,
                         options=([discord.SelectOption(label=word, emoji=emoji.emojize(":cross_mark:")) for word in pagi.slice_inventory()] or [discord.SelectOption(label="None")]),
                         disabled=not pagi.inv)
            # discord.SelectOption(label="Close", value="touil.removeword.exit", emoji=emoji.emojize(":cross_mark:"))
        # ])
        self.pagi: Inventory = pagi

    async def callback(self, interaction: discord.Interaction):
        # if self.values[0] != "touil.removeword.exit":
        for word in self.values:
            self.pagi.inv.remove(word)
        await self.pagi.render(interaction)
        if self.pagi.on_update:
            await self.pagi.on_update()
        # else:
            # msg = await self.pagi.msg.delete()