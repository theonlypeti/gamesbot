import asyncio
from datetime import timedelta, datetime
from typing import Callable, Optional
import nextcord as discord
from utils import embedutil
from utils.lobbyutil.lobbycog import Game


class Timer:
    """A countdown timer for lobby games.
    :param game: The game instance the timer is associated with.
    :param duration: The duration of the timer as a timedelta object.
    :param name: Optional name for the timer.
    :param stoppable: Whether the timer can be stopped by players.

    :description: Optional description for the built in embed.
    :ivar ended: Whether the timer has ended by running out.
    :ivar stopped: Whether the timer was stopped by a player. Returns the time that was on the clock when stopped.
    :ivar stopped_by: The user who stopped the timer.
    :ivar started_at: The datetime when the timer was started.
    :ivar started_by: The user who started the timer.
    :ivar timestamp: A human-readable timestamp of when the timer will end, or how much time was remaining when stopped.

    :ivar on_end: A callable that is called when the timer ends naturally. Should accept one argument: the Timer instance.
    :ivar on_stop: A callable that is called when the timer is stopped by a player. Should accept two arguments: the Timer instance and the Interaction that stopped it.

    Use the `render` method to send the timer embed to a channel or interaction.
    Use the `start` method to start the countdown automatically in code.
    Use the `can_start` method to check if a user can start the timer.
    Use the `stop` method to stop the timer manually.
    Use the `can_stop` method to check if a user can stop the timer.
    Use the `wait` method to await the timer's completion.
    """
    def __init__(self, game: Game, duration: timedelta, name:str =None, stoppable: bool=None):
        self.game = game
        self.name = name or "Timer"
        self.description = ""
        self.duration: timedelta = duration
        self.stoppable = stoppable or True
        self.on_end: Callable[[Timer], ...] = self.mock_end
        self.on_stop: Callable[[Timer, discord.Interaction], ...] = self.mock_stop
        self.on_start: Callable[[Timer, discord.Interaction], ...] = self.mock_start

        self.stopped = False
        self.started_at: datetime = None
        self.started_by: discord.User = None
        self.stopped_by: discord.User = None
        self._future = None
        self._stop_event = asyncio.Event()


    async def stop(self, interaction: discord.Interaction):
        """Stops the countdown. Include the interaction to check permissions."""
        if await self.can_stop(interaction):
            self.stopped = discord.utils.utcnow()
            self.stopped_by = interaction.user
            self._stop_event.set()
            if self.on_stop:
                await self.on_stop(self, interaction)
        return bool(self.stopped)

    async def start(self, interaction: Optional[discord.Interaction] = None):
        """Starts the countdown. Include the interaction if you want to check permissions."""
        if interaction:
            if not await self.can_start(interaction):
                return
        self.started_at = discord.utils.utcnow()
        self.started_by = interaction.user if interaction else None
        self._stop_event.clear()
        self._future = asyncio.create_task(self._run_timer())
        if self.on_start:
            await self.on_start(self, interaction)

    async def _run_timer(self):
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=self.duration.total_seconds())
        except asyncio.TimeoutError:
            pass # Timer finished naturally

        if not self.stopped:
            if self.on_end:
                await self.on_end(self)

    async def can_start(self, interaction: discord.Interaction) -> bool:
        """Checks if the timer can be started by the interaction user. You may overwrite this for custom games."""
        if self.started_at is not None:
            await embedutil.error(interaction, "Timer has already started.")
            return False
        elif interaction.user.id != self.game.lobby.lobbyleader.id:
            await embedutil.error(interaction, "Only the lobby leader can start the timer.")
            return False
        else:
            return True

    async def can_stop(self, interaction: discord.Interaction) -> bool:
        """Checks if the timer can be stopped by the interaction user. You may overwrite this for custom games."""
        if not self.stoppable:
            await embedutil.error(interaction, "This timer cannot be stopped.")
            return False
        elif interaction.user.id != self.game.lobby.lobbyleader.id:
            await embedutil.error(interaction, "Only the lobby leader can stop the timer.")
            return False
        else:
            return True

    @property
    def ended(self):
        """Returns whether the timer has ended."""
        return self.started_at is not None and (discord.utils.utcnow() - self.started_at).total_seconds() >= self.duration.total_seconds()

    @property
    def timestamp(self):
        """Returns a human readable timestamp of when the timer will end, or how much time is remaining.
        If the timer has been stopped, returns how much time was remaining when it was stopped.
        Put it in your own messages or embeds to show the remaining time."""
        if self.stopped:
            return f"Timer has been stopped with {self.started_at + self.duration - self.stopped} remaining."
        elif self.ended:
            return "Time has run out!"
        elif self.started_at:
            return discord.utils.format_dt(self.started_at + self.duration, style='R')
        else:
            return self.duration

    async def mock_end(self, timer: "Timer"):
        """Example function that runs when the timer has ran out. Supply your own end function"""
        game: Game = timer.game
        await game.channel.send(embed=self.get_embed(), delete_after=10)
        # await asyncio.sleep(2)
        # await game.next_turn()

    async def mock_stop(self, timer: "Timer", interaction: discord.Interaction):
        """Example function that runs when the timer was stopped by an user. Supply your own function to run on stop"""
        game: Game = timer.game
        await game.channel.send(f"Timer stopped by {self.stopped_by.mention}!", delete_after=5)
        # await game.next_turn()

    async def mock_start(self, timer: "Timer", interaction: discord.Interaction):
        """Example function that runs when the timer was started by an user. Supply your own function to run on start"""
        game: Game = timer.game
        await game.channel.send(f"Timer started by {self.started_by.mention}!", delete_after=5)
        # await game.next_turn()

    def get_embed(self):
        """Returns the built in embed for the timer."""
        embed = discord.Embed(title=f"{self.name}", color=discord.Color.blue())
        if self.description:
            embed.description = self.description
        embed.add_field(name="Remaining Time", value=f"{self.timestamp}")
        if self.started_by:
            embed.set_footer(text=f"Started by {self.started_by}", icon_url=self.started_by.display_avatar.url)
        return embed

    class TimerStartView(discord.ui.View):
        def __init__(self, timer: "Timer"):
            super().__init__(timeout=None)
            self.timer = timer

        @discord.ui.button(label="Start Timer", style=discord.ButtonStyle.green)
        async def start_button(self, button: discord.ui.Button, interaction: discord.Interaction):
            await self.timer.start(interaction)
            if self.timer.stoppable:
                await interaction.edit(embed=self.timer.get_embed(),
                                       view=Timer.TimerStopView(self.timer),
                                       delete_after=self.timer.duration.total_seconds())
            else:
                await interaction.edit(embed=self.timer.get_embed(),
                                       delete_after=self.timer.duration.total_seconds(),
                                       view=None)

    class TimerStopView(discord.ui.View):
        def __init__(self, timer: "Timer"):
            super().__init__(timeout=None)
            self.timer = timer

        @discord.ui.button(label="Stop Timer", style=discord.ButtonStyle.red)
        async def stop_button(self, button: discord.ui.Button, interaction: discord.Interaction):
            if await self.timer.stop(interaction):
                await interaction.edit(view=None, delete_after=10, embed=self.timer.get_embed())

    async def render(self, channel: discord.TextChannel|discord.Interaction):
        """Renders the timer embed, with start/stop button to a channel or interaction."""
        embed = self.get_embed()
        if not self.started_at:
            viewObj = self.TimerStartView(self)
        else:
            if self.stoppable:
                viewObj = self.TimerStopView(self)
            else:
                viewObj = None

        await channel.send(embed=embed, view=viewObj, delete_after=(self.duration.total_seconds() + 1 if self.started_at else None))

    async def wait(self):
        """Waits for the timer to complete. Returns True if the timer ended naturally, False if it was stopped."""
        if self._future:
            await self._future
        if self.stopped:
            return False
        return True