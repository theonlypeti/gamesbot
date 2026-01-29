from math import ceil
from typing import Callable, MutableSequence
import emoji
import nextcord as discord
import nextcord.errors

#TODO add on_update callback to be called after each render?
class Paginator(discord.ui.View):
    """A paginator for embeds, with a back and forward button, and a definable select.
    :ivar page: The current page.
    :ivar maxpages: The maximum number of pages.
    :ivar inv: The inventory of items to paginate.
    :ivar itemsOnPage: The number of items to display on a page.
    :ivar mykwargs: The kwargs to pass to the embed and select factory function.
    :ivar msg: The message that the paginator is displayed in.

    :param func: The function that returns the embed to be displayed. It must take the paginator object as a parameter, which contains all the above attributes.
    :param select: The function that returns the select to be displayed. It must take the paginator object as a parameter, which contains all the above attributes.
    :param timeout: The timeout for the paginator. Seconds until it is automatically disabled.
    :param inv: See above.
    :param itemsOnPage: See above.
    :param kwargs: See above.

    Add a back button manually with View.add_item, appropriate to the situation you are in."""
    def __init__(self, func: Callable[..., discord.Embed] | None, select: Callable[..., discord.ui.Select] | None, inv: MutableSequence, itemsOnPage: int = 25, timeout: int|None = None, kwargs=None):
        self.mykwargs = kwargs or set()
        self.page: int = 0
        self.maxpages: int = 0  # to be rewritten on update
        self.func = func
        self.select = select
        if self.select:
            self.select.custom_id = "pagiselect"
        self.itemsOnPage: int = itemsOnPage
        assert self.itemsOnPage
        self.inv: MutableSequence = inv
        self.msg: discord.Message | None = None
        super().__init__(timeout=timeout)
        self.update()
        # if self.select:
        #     self.add_item(self.select(pagi=self))

    @discord.ui.button(emoji=emoji.emojize(':last_track_button:'), row=1, custom_id=f"leftbutton")
    async def back(self, button, interaction: discord.Interaction):
        """The previous page button."""
        self.page = (self.page - 1) % self.maxpages
        await self.render(interaction)

    @discord.ui.button(emoji=emoji.emojize(':next_track_button:'), row=1, custom_id=f"rightbutton")
    async def forw(self, button, interaction: discord.Interaction):
        """The next page button."""
        self.page = (self.page + 1) % self.maxpages
        await self.render(interaction)

    async def on_timeout(self) -> None:
        """Called when the paginator times out."""
        for ch in self.children:
            ch.disabled = True
        try:
            await self.msg.edit(view=self)
        except discord.errors.NotFound:
            pass

    def mergeview(self, view: discord.ui.View, row=2):
        """Merges a discord.ui.View into this one.
        It is intended to be used with buttons no more than 5
        :param view: the view whose children to put into the paginator
        :param row: which row to put the items into."""
        for item in view.children:
            item.row = row
            self.add_item(item)

    def update(self) -> None:
        """Updates the paginator.
        This is called automatically when the buttons are pressed and the paginator is rendered.
        Disables the paginator buttons if there is only one page."""
        self.maxpages = ceil(len(self.inv) / self.itemsOnPage)  # in case the inventory changes
        self.page = max(min(self.page, self.maxpages-1), 0)

        if len(self.inv) <= self.itemsOnPage:
            for ch in self.children:
                if ch.custom_id in ("leftbutton", "rightbutton"):
                    ch.disabled = True
        else:
            for ch in self.children:
                if ch.custom_id in ("leftbutton", "rightbutton"):
                    ch.disabled = False
        if self.select:
            select = list(filter(lambda i: i.custom_id == "pagiselect", self.children))
            if select:
                self.remove_item(select[0])
            self.add_item(self.select(pagi=self))

    # Add a back button manually with View.add_item, appropriate to the situation you are in

    def slice_inventory(self):
        """Slices the inventory into the current page."""
        return self.inv[self.page*self.itemsOnPage:(self.page+1)*self.itemsOnPage]

    async def render(self, interaction: discord.Interaction | discord.TextChannel, edit: bool = True, **kwargs) -> None:
        """Renders the paginator.
        :param interaction: The interaction that triggered the paginator. Can be an interaction or a channel to send the message to.
        :param edit: Whether to edit the message whose view called the render. If False, it will send a new message. Can be paired with ephemeral."""
        self.update()
        if self.select:
            for n, child in enumerate(self.children):
                if child.custom_id == "select":
                    self.children[n] = self.select(self)
                    break

        if not isinstance(interaction, discord.TextChannel) and edit:  # if it's a interaction or message and it is to be edited
            msg: discord.Interaction = interaction  # for clarity
            try:
                if self.func:
                    self.msg = await msg.edit(embed=self.func(self), view=self, **kwargs)
                else:
                    self.msg = await msg.edit(view=self, **kwargs)
            except (discord.errors.InvalidArgument, TypeError, nextcord.errors.NotFound): pass
            else: return

        # else:  # if it's an interaction or a text channel, ergo it is sent for the first time
        if self.func:
            self.msg = await interaction.send(embed=self.func(self), view=self, **kwargs)
        else:
            self.msg = await interaction.send(view=self, **kwargs)


# Example usage:
# @discord.slash_command()
# async def command(self, interaction: discord.Interaction):
#     embeds = [discord.Embed(title=f"Page {i+1}", description=f"Page {i+1} of 5", color=discord.Color.random()) for i in range(5)]
#     pagi = Paginator(func=lambda pagin: pagin.inv[pagin.page], select=None, inv=embeds, itemsOnPage=1)
#     await pagi.render(interaction, ephemeral=True)