# Subclassing and Using LobbyCog

## Introduction

The `LobbyCog` class handles the creation and management of game lobbies for discord games. It also makes slash commands and help topics for your game. It is a subclass of `commands.Cog` from the `nextcord` library.

## Subclassing

To subclass `LobbyCog`, you need to create a new class that inherits from `LobbyCog`. In the `DiceWarriorsCog` file, this is done with the `DiceCog` class:

```python
class DiceCog(lobby.LobbyCog):
    def __init__(self, client: nextcord.Client):
        super().__init__(client,
                         GAME_NAME="Dice Warriors",
                         BASE_CMD_NAME="dice",
                         maxplayers=2,
                         gameclass=DiceGame,
                         playerclass=DicePlayer,
                         TESTSERVER_ID=None)
```

In the `__init__` method of your subclass, you need to call the `__init__` method of the superclass (`LobbyCog`) using the `super()` function. You need to provide several parameters:

- `client`: Your bot/client instance.
- `GAME_NAME`: The name of the game. This will be displayed in the help command and the Lobby.
- `BASE_CMD_NAME`: The base command name for the game. This will be the slash command for the game. If not provided, it will try to generate one from the `GAME_NAME`.
- `minplayers`: The minimum number of players to start a game. Defaults to 2.
- `maxplayers`: The maximum number of players allowed in a game. Defaults to 25.
- `lobbyclass`: The class (subclass of `Lobby`) to use for lobbies. If not provided, it will default to `Lobby`.
- `gameclass`: The class (subclass of `Game`) to use for games. If not provided, it will default to `Game`.
- `playerclass`: The class (subclass of `Player`) to use for players. If not provided, it will default to `Player`.
- `TESTSERVER_ID`: The ID of your discord guild. This guild will have the commands immediatelly deployed. Defaults to None.

## Using the Subclass

This subclassed `LobbyCog` class can be loaded as any other cog extension to your client.
Every cog should have a `setup` root level function that adds the cog to the client. 
This function is called by the `client/bot`'s `load_extension` method.

```python
def setup(client):
    client.add_cog(DiceCog(client))
```

This function is called when the cog is loaded, and it adds an instance of the `DiceCog` class to the client. 
This allows the client to use the commands and events defined in the `DiceCog` class.

Once you have created your subclass, you can use its commands to manage lobbies and players.
The base command name for these subcommands is the `BASE_CMD_NAME` parameter you provided when creating the subclass.
for example: `/dice help`

The `LobbyCog` creates the following subcommands:  
- `help`: This subcommand shows the help manual for the game and the bot.
- `stats`: This subcommand shows the user's statistics across all the games they've played.
- `join`: This subcommand allows a user to join an existing lobby.
- `leave`: This subcommand allows a user to leave the lobby they are currently in.
- `start`: This subcommand creates a lobby for users to join and to start the game.


## Adding other commands

You can add more subcommands like these to your cog by defining methods with the following signature:

```python
self.add_subcommand(name="leaderboard",
                    callback=self.leaderboard,
                    description="Displays the best player")

async def leaderboard(self, interaction: nextcord.Interaction):
    """Displays who the best player is (not really)"""
    await interaction.send("Leaderboard")
```

You can add more parameters to the callback command. You may use typehints or `nextcord.SlashOption` to specify their types.

Supplying a docstring to the method will make it appear in the help command as the command's explanation.

Adding other base commands can be done normally as you would in a nextcord bot, using a `slash_command` decorator.
However, to make them appear in the help command, you need to add them to the help subcommand's list of commands manually using `self.other_commands`.

```python
    @nextcord.slash_command(name="test")
    async def testcmd(self, interaction: nextcord.Interaction):
        """Test description"""
        await interaction.response.send_message("Testing")

    self.other_commands.update({self.testcmd.name: self.testcmd})
```
Subcommands of your new commands are not walked through by the help command and should be added to the `self.other_commands` dictionary manually.

To be mentionable they need to have the same guild_ids as the `LobbyCog` instance's `TESTSERVER_ID`, be it None or a guild id.

`nextcord.UserCommand` and `nextcord.MessageCommand` are not mentionable, therefore cannot appear in the help command.


# Player Class

## Introduction

The `Player` class represents a player in a game lobby. It keeps track of the player's statistics in a specific game, readiness status, and lobby membership.

## Initialization

The `Player` class takes a `nextcord.User` object or a dictionary of player-like attributes as a parameter when it is initialized. 
This class is however usually handled by the lobby and game classes and you will not need to initialize it yourself.
Instead use the getPlayer method of your `LobbyCog` subclass to get the player object for a specific Discord user.

```python
player = cog.getPlayer(interaction.user)
```

## Attributes

The `Player` class has the following attributes:

- `userid`: The Discord user id.
- `statistics`: A dictionary of statistics over the games played like wins, losses, etc.
- `ready`: Whether the player is ready.
- `inLobby`: The lobby code the player is in or None.
- `user`: The Discord user object.
- `name`: The user's username in Discord.

## Methods

The `Player` class has the following methods:

### is_ready

The `is_ready` method is used to check if the player is ready. Can be overridden in subclasses to implement custom ready conditions.

```python
def is_ready(self):
    return self.ready
```

### can_ready

The `can_ready` method is used to check if the player can ready up. This method can be overridden in subclasses to implement custom ready conditions.
For example if they have enough words submitted or have chosen a team. Use the interaction object to signal the player why they can't ready up.

```python
async def can_ready(self, interaction: nextcord.Interaction) -> bool:
    return True
```

### can_join

The `can_join` method is used to check if the player can join a lobby. This method can be overridden in subclasses to implement custom join conditions.
For example if the user has a certain role or is not banned.

```python
async def can_join(self, interaction: nextcord.Interaction) -> bool:
    return True
```

### \_\_str__

The `__str__` method is used to return a string representation of the player. By default, it returns the player's username.
This will be used to construct the player list embed in the lobby. You can override this to include more information about the player.
For example their chosen icon, amount of words submitted, chosen team, etc.

```python
def __str__(self) -> str:
    return self.name
```

## Subclassing

To subclass `Player`, you need to create a new class that inherits from `Player`. In the `DiceWarriorsCog` file, this is done with the `DicePlayer` class:

```python
class DicePlayer(lobby.ClovecePlayer):
    def __init__(self, user: nextcord.User):
        self.money = 1000
        super().__init__(user)
        self.health = 100
        self.points = 0
        self.words = []

    def __str__(self) -> str:
        return f"{self.name} ({len(self.words)} words)" 
```

In the `__init__` method of your subclass, you need to call the `__init__` method of the superclass (`Player`) using the `super()` function. You need to provide a `nextcord.User` object.

You can add additional attributes to your subclass, like `health` in the `DicePlayer` class.
All attributes after/below the `super()` call will be set on each lobby join, while the attributes above the `super()` call will be loaded from the savefile (freshly initialized only for brand new players.) 
This means returning players will have those attributes above populated from the database, 
ergo keep persistent attributes above the `super()` call, and volatile ones below.

## Using the Subclass

Once you have created your subclass, pass it to your `LobbyCog` subclass when creating the instance:

```python
class DiceCog(lobby.LobbyCog):
    def __init__(self, client: nextcord.Client):
        super().__init__(client,
                         GAME_NAME="Dice Warriors",
                         playerclass=DicePlayer)
```

This will allow you to use the additional attributes and methods you added to your subclass. Also this class's `__str__` method will be used to display the player in the lobby and other methods will be used to check their readiness.

Internally, attributes that will be saved to the savefile about the player are determined by the  `self._important` attribute in your subclass.

```python
self._important = ["userid", "statistics"] + ["your", "attrs"] # only these attrs will be saved
```
This is handled automatically, if you define the attributes above the `super()` call in your `__init__` method, as demonstrated above in the player subclassing section.

It is recommended to only save attributes that persist between games and are not too large. For example ready or team should be initialized with each new lobby creation and are not saved.

# Lobby Class

## Introduction

The `Lobby` class represents a game lobby. It keeps track of the players in the lobby, the game instance, the lobbyleader, and other attributes.
It manages joining and leaving, respecting the minimum and maximum player count, disbanding if the leader leaves.

The lobby automatically generates a lobbycode which can be used to join the lobby.
If the private attribute is set to `True`, the code will not be displayed and only the lobbyleader can share it with players they wish to invite.

The lobby will have 5 buttons by default. The join button is a quick way to join a public lobby, however it is disabled if the lobby is private.
In that case joining is only possible by using the code in the `join` command.

The next button is a self-explanatory leave button. Next to it by default is an unused button, which can be customized in your subclassed lobby class.

The last two buttons are the ready and start buttons. The start button is disabled until the start condition is met which can be customized in your subclassed lobby class. By default it is enabled when the minimum player count is reached and all players are ready.

## Subclassing

To subclass `Lobby`, you need to create a new class that inherits from `Lobby`.

```python
    class WordsLobby(lobby.Lobby):
        def __init__(self, inter, cog, private):
            super().__init__(inter, cog, private, lobbyView=TestGameCog.MyButtons)
    
        def readyCondition(self):
            return all([len(player.words) > 3 for player in self.players]) and super().readyCondition()
```

In the `__init__` method of your subclass, you need to call the `__init__` method of the superclass (`Lobby`) using the `super()` function. You need to provide the following parameters:
 - `inter`: The interaction object that created the lobby.
 - `cog`: The `LobbyCog` instance that created the lobby.
 - `private`: Whether the lobby is private or not. Defaults to False.
 - `lobbyView`: The view class to use for the lobby. If not provided, it will default to `LobbyView`.
 - `adminView`: The view class to use for the admin buttons. If not provided, it will default to `AdminView`.
 - `maxplayers`: The maximum number of players allowed in the lobby. Defaults to 25.
 - `minplayers`: The minimum number of players to start a game. Defaults to 2.
 - `game`: The game Class to use for starting a game.

In this example above we have overwritten the `readyCondition` method to check if all players have submitted at least 3 words. It is implied that we are using a subclassed `Player` class with a `words` attribute.

## Using the Subclass

Once you have created your subclass, pass it to your `LobbyCog` subclass when creating the instance:

```python
class WordsCog(lobby.LobbyCog):
    def __init__(self, client: nextcord.Client):
        super().__init__(client,
                         GAME_NAME="Words",
                         lobbyclass=WordsLobby,
                         playerclass=WordsPlayer
                            )
```

This will allow you to use the additional attributes and methods you added to your subclass. Also this class's `readyCondition` method will be used to check if the lobby can be started.

## Overriding methods

In the context of the Lobby class, there are several methods that are designed to be overridden in subclasses. This allows for custom behavior in different types of lobbies. Here are some examples:

### readyCondition

You can override the `readyCondition` method to check if the lobby can be started. By default it checks if the minimum player count is reached and all players are ready.

```python
def readyCondition(self):
    return (len(self.players) >= self.minplayers
            and all([player.is_ready() for player in self.players])
            and all([player.team for player in self.players]))
```

In this example we check if the minimum player count is reached, all players are ready and all players have chosen a team.

### on_create  (\_\_init__) 
<!-- TODO on_create is not an actual method in the Lobby class, so we clarify that __init__ is used instead. -->
The purpose of this method is fulfilled by the `__init__` method of the Lobby class. It is called when the lobby is created. You can override it to do something custom when the lobby is created.
Don't forget to call `super().__init__()` in your subclass's `__init__` method.

```python
def __init__(*args, **kwargs):
    super().__init__(*args, **kwargs)
    self.customattr = "custom"
    with open("words.txt", "r") as f:
        self.words = f.readlines()
```

### on_disband

Similarly, you can overwrite `on_disband` to do something when the lobby is disbanded.

```python
async def on_disband(self):
    for player in self.players:
        player.eliminated = False # assuming eliminated is something custom
        await player.user.send("The lobby has been disbanded")
```

### on_join
You can overwrite `on_join` to do something when a player joins the lobby. For example send a welcome message to the player.

```python
async def on_join(self, player: Player, interaction: nextcord.Interaction):
    await player.user.send("Welcome to the lobby")
```


### on_ready
You can overwrite `on_ready` to do something when a player clicks ready/unready. For example send an ephemeral message to the player with controls for the game.
The ready or join button is one that everyone will have to click before the game can start, so it is a good place to send instructions or game controls ui.

```python
async def on_ready(self, player: Player, interaction: nextcord.Interaction):
    await interaction.send("Here are the game controls", view=XY(), ephemeral=True)
```

### on_leave
You can overwrite `on_leave` to do something when a player leaves the lobby. For example send a goodbye message to the player.
The interaction is not provided, as disbanding the lobby or being kicked does not stem from a player interaction.

```python
async def on_leave(self, player: Player, reason: Literal["kicked", "left", "disbanded"]):
    await player.user.send("Goodbye")
```

  
### show_players

The `show_players` method is used to display the players in the lobby. In the base Lobby class, it enumerates the players, adding each one as a field in an embed. If the number of players is less than the minimum required, it adds "[Empty]" fields.  If you want to change how players are displayed in a specific type of lobby, you can override this method in your subclass.

### playercount

The `playercount` property returns a string representing the number of players in the lobby and the maximum number of players allowed. If you want to change how this information is represented, you can override this property in your subclass.

### add_footer

The `add_footer` method is used to add a footer to the lobby embed. In the base Lobby class, it adds a description of each button in the lobby view to the footer. If you want to change what information is included in the footer, you can override this method in your subclass. 

The button descriptions are taken from the button's `callback` method docstrings, so if you customize buttons, you may customize the description there, instead of overwriting this.

# Views

The lobby has a `lobbyView` which is a subclass of `nextcord.ui.View`. It is used to display the lobby buttons. The view is automatically updated when the lobby is updated.
The other view is a `adminView` which is also a subclass of `nextcord.ui.View`. It is used to display the admin buttons and is only displayed to the lobbyleader to kick players and add other functionalities.
Both of these views take the lobby as a parameter.

## lobbyView

The `LobbyView` class in the `lobbycog.py` file is used to display the main buttons for the lobby. This includes buttons for joining, leaving, readying up, and starting the game. 

If you want to customize the `LobbyView` for a specific type of lobby, you can create a subclass of `LobbyView`. This allows you to add additional buttons or change the behavior of existing buttons (like change ready or join conditions).

To create a subclass of `LobbyView`, you need to define a new class that inherits from `LobbyView`. In the `__init__` method of your subclass, you can add or modify buttons.


```python
class MyLobbyView(LobbyView):
    def __init__(self, lobby):
        self.middlebutton = AddWordsButton
        super().__init__(lobby)
        
```

The `LobbyView` class has a `middlebutton` attribute that can be customized in subclasses. This button is initially set to `None`, but you can assign a new button to this attribute in your subclass.

In this example, `AddWordsButton` is a class that inherits from `nextcord.ui.Button`. This class defines the behavior of the middle button and has to take the lobby as a paramter. You would need to define this class separately.

Here is an example of how you might define `AddWordsButton`:

```python
class Addwordsbutton(nextcord.ui.Button):
    def __init__(self, lobby: lobby.Lobby):
        self.lobby = lobby
        super().__init__(style=nextcord.ButtonStyle.primary, emoji=emoji.emojize(":plus:"))

    async def callback(self, interaction: nextcord.Interaction):
        """Add words to inventory"""
        user: TestGameCog.WordsPlayer = self.lobby.getPlayer(interaction.user)
        inv = utils.Inventory.Inventory(user.words, on_update=self.lobby.readyCheck)
        await inv.render(interaction, ephemeral=True)
```

In this example, `AddWordsButton` inherits from `nextcord.ui.Button`. 
The `callback` method defines what happens when the button is clicked. 
In this case, it creates an inventory as a paginator, and sends it to the user as an ephemeral message for them to manage and submit words to the game.
The callback's docstring will be used as the button's hint of what it does in the embed footer.

### Using the Subclass

Once you have created your subclass of `LobbyView`, you can use it in your subclass of `Lobby`. When creating a new `Lobby` instance, you would pass your `LobbyView` subclass as the `lobbyView` parameter.

Here is an example of how you might do this:

```python
class MyLobby(lobby.Lobby):
    def __init__(self, inter, cog, private):
        super().__init__(inter, cog, private, lobbyView=MyLobbyView)
```

In this example, `MyLobby` is a subclass of `Lobby`. When creating a new `MyLobby` instance, it uses `MyLobbyView` for the lobby view.

## adminView

The `AdminView` class in the `lobbycog.py` file is used to display the admin buttons for the lobby. This includes buttons for kicking players and sending the lobby message. This view can be subclassed to add additional admin buttons or change the behavior of existing buttons. You can use `self.add_item()` or nextcord's Item decorators in your class as this view has no strict structure.

```python
class MyAdminView(lobby.LobbyCog.AdminView):
    def __init__(self, lobby: TestGameCog.WordsLobby):
        super().__init__(lobby)

    @nextcord.ui.button(label="Manage words", style=nextcord.ButtonStyle.grey, emoji=emoji.emojize(":ledger:"))
    async def mngwords(self, button, inter):
        inv: Inventory = Inventory(self.lobby.words)
        await inv.render(inter, ephemeral=True)
```

In this example, `MyAdminView` is a subclass of `AdminView`. It adds a button to manage words to the admin view. This button is displayed to the lobbyleader and allows them to manage the words in the lobby. Note this list of words is different from the ones that players have submitted unless you code it so. 


# Starting the game

When the game is started using the lobby's start button, the lobby instantiates a subclassed `Game` class from the lobby's `self.game` attribute and calls its `start` method.
This Game object will have access to the lobby and all of its info. It is recommended to send the game message using `interaction.channel.send` instead of directly responding to the interaction,
as they cannot be edited after 15 minutes of playing.


From here on it is up to you how you implement your game and how you work with the lobby and player objects. However it is recommended to use some of the provided methods.

## Player management

Players love keeping track of statistics so i encourage saving interesting or wacky counters or high scores using `player.statistics["yourstat"] += 1` and then calling `game.savePlayers()` at the end of the game.

`savePlayers()` saves any changes to the players' statistics and other important attributes. You can change the `self._important` attribute in your subclassed `Player` class to include more attributes, or define these attributes before calling `super().__init__()` in the player's `__init__` method, as explained in the Player class section.


To get a Player object from a user id or `interaction.user` you can use `self.getPlayer(userid/userobj)`. 

## Ending the game

After the game ends you can call `lobby.send_lobby(channel)` to offer a rematch. Remember to set the lobby's `self.ongoing` attribute to False after the game ends, otherwise it will not be possible to start a new game in the lobby.
Otherwise, you can call `lobby.disband()` to delete the lobby and remove it from the `LobbyCog`'s lobbies list. This will also remove the players from the lobby and set their `inLobby` attribute to None, so they can join a new lobby.

# Team utils

Included is a file called `teamutils` which contains a `Team` class, a `TeamPlayer` class and a `TeamLobby` class. These are used to manage teams in a lobby and in a game where players are split into teams.
You can use these classes in your Cog to manage teams in your game.

```python
class TeamGameCog(lobby.LobbyCog):
    def __init__(self, client: nextcord.Client):
        super().__init__(client, "Team Game",
                         playerclass=teams.TeamPlayer,
                         lobbyclass=teams.TeamLobby)
```
        

The `Team` class is used to manage players in a team, their points, words or whatever you implement. They are automatically managed by the `TeamLobby` class.
If you wish to subclass this class to add more attributes or methods, you can do so. You will need to pass this new class into `TeamLobby(teamclass=YourTeamClass)`.

The `TeamLobby` class modifies the lobby buttons to include a team selector and the embed will show which player belongs to which team.

# Help categories

The `LobbyCog` class automatically creates 3 help categories for your game. These can be viewed using the `/BASE_GAME_CMD help` command. They include a help topic for the game `commands`, the `rules` and `credits`.
The credits and rules category are empty and to be filled by the game author, while the game commands category is automatically filled with the game's commands and their descriptions.

## Adding commands to the help command

By default the help command walks through each subcommand in its' base slash command and adds the docstring of the method as the command's explanation. If you wish to add a command to the help command, you need to add it to the `self.other_commands` dictionary in your subclassed `LobbyCog` class.

```python
self.other_commands.update({self.testcmd.name: self.testcmd})
#where self.testcmd is a method with a slash_command decorator
```

Adding subcommands to the base slash command is slightly different. You need to add a method to your subclassed `LobbyCog` class with the `add_subcommand` method and provide the name, callback and description of the subcommand.

```python
self.add_subcommand(name="leaderboard",
                    callback=self.leaderboard,
                    description="Displays the best player")
```

Again, the docstring of the `self.leaderboard` method will be used as the command's explanation. These steps are necessary for the commands to appear in the help category.

## Adding rules and credits

To add rules and credits to the help command, you would edit your cog's `help_categories` attribute. This is a dictionary with the keys being the category names and the values being a `HelpCategory` class.
You can edit the instances of these classes to add your own rules and credits. Alternatively just use the `rules` and `credits` properties of the `LobbyCog` class.

```python
self.credits = """Made by @theonlypeti"""
self.rules = """Don't talk about the dice club."""
```

Adding new help categories is done by creating an instance of the `HelpCategory` class and adding it using `add_help_category`.

```python
self.add_help_category(HelpCategory(label="House Rules",
                                    description="This category is about house rules",
                                    emoji="🎲",
                                    helptext="There are no rules, the host always wins."))
```

When you want to mention a command in a help category, it could happen that `command.get_mention()` will throw an error regarding the command not being registered. 
This happens because the commands are registered after all the cogs are loaded, but the helptext is defined before the bot logs in and registers all the commands.
You would need to define the helptext after the bot is `await wait_until_ready()`, or generate the helptext dynamically when called.

# Timer class

The `Timer` class provides a lightweight, asyncio-based countdown timer used throughout games and lobbies.

## Purpose

Use `Timer` to implement turn timers, countdowns, or other timed events inside your game's `Game` instance. It integrates with the lobby/game model and provides small interactive views (Start/Stop buttons) as well as programmatic control.

## Key behaviours

- `start(interaction: Optional[Interaction])` schedules the countdown as a background asyncio task. If an `interaction` is supplied, permission checks are performed with `can_start`.
- `stop(interaction: Interaction)` signals the timer to stop early and runs the `on_stop` hook.
- `wait()` can be awaited to block until the timer finishes (either by timeout or stop) and returns `True` if finished naturally or `False` if stopped.
- `render(channel_or_interaction)` sends a simple embed with Start/Stop controls that honor `stoppable`.

## Constructor

```py
Timer(game: Game, duration: timedelta, name: str = None, stoppable: bool = True)
```

Parameters:

- `game` – the `Game` instance that owns the timer (used by the default hook implementations to post messages to the channel).
- `duration` – a `timedelta` describing how long the countdown should run.
- `name` – optional human-readable title used in the built-in embed (defaults to "Timer").
- `stoppable` – whether users are allowed to stop the timer via the UI (defaults to `True`).

Attributes (important ones):

- `game` – owning `Game` instance.
- `duration` – countdown `timedelta`.
- `name`, `description` – used for the embed content.
- `stoppable` – if `False`, the built-in Stop button will not be provided, and also no other custom written stopping methods will work.
- `started_at` – UTC datetime when the timer was started (or `None`).
- `started_by` – `discord.User` that started the timer (if any).
- `stopped` – `False` if running/not started, or the UTC datetime when stopped.
- `stopped_by` – the user who stopped the timer (if stopped).

## Hooks

Replace these attributes with coroutines to customize behaviour when the timer starts, stops, or ends:

- `on_start(timer, interaction)` – called after `start()` completes; default: `mock_start` sends a small message to the game's channel.
- `on_stop(timer, interaction)` – called after a user stops the timer; default: `mock_stop` notifies the channel who stopped it.
- `on_end(timer)` – called when the timer ends naturally; default: `mock_end` posts the timer embed to the game's channel.

The default hooks are intentionally simple; swap them for your game logic (for instance: advance turn, perform penalties, or pick next player).

## Permission checks

The class provides two overridable permission methods:

- `can_start(interaction)` – by default only the lobby leader may start the timer; override to change behaviour, for example next turn's player.
- `can_stop(interaction)` – by default only the lobby leader may stop the timer; override to change behaviour, for example current turn's player.

Both methods default to sending an ephemeral error via `embedutil.error` if the action is disallowed.

## Methods summary

- `start(interaction: Optional[Interaction])` – start the timer. If `interaction` is provided, permission is checked and `on_start` is invoked.
- `stop(interaction: Interaction)` – stop the timer early. Returns `True` if the timer is stopped by this call.
- `render(channel_or_interaction)` – send the default timer embed with interactive Start/Stop buttons.
- `wait()` – await the timer's completion. Returns `True` if ended naturally, `False` if stopped.
- `get_embed()` – returns the built-in `nextcord.Embed` representing the timer's current state. Can be edited for custom implementation or used premade for custom rendering.

## Example usage

Interactive (send UI with a Start button):

```py
from datetime import timedelta

turn_timer = Timer(game=self, duration=timedelta(seconds=30), name="Turn Timer")
await turn_timer.render(interaction)  # sends an embed with a "Start Timer" button
```

Programmatic start & wait:

```py
await turn_timer.start()  # start automatically without waiting for a user interaction
finished_naturally = await turn_timer.wait()
if finished_naturally:
    # proceed to next turn, noone interrupted it
else:
    # timer stopped early by someone, handle accordingly
```

Custom hooks:

```py
async def on_time_up(timer: Timer):
    # called when time runs out
    await timer.game.next_turn()

turn_timer.on_end = on_time_up
```

## Notes

- By default, only the lobby leader may start/stop the timer; override `can_start`/`can_stop` to relax this.
- Calling `start()` while the timer is already running is rejected by default (sends an ephemeral error).
- `render()` uses the built-in `TimerStartView` / `TimerStopView`. Messages sent by the UI may be auto-deleted after the duration to keep channels tidy.
