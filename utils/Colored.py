from typing import List

import nextcord as discord


class ColorGroup:
    def __init__(self, dccolor: discord.Colour, name: str = None, cmdcolor: str = None,
                 emote_s: str = None, emote_r: str = None, emote_h: str = None):
        self.dccolor = dccolor
        self.hex = str(dccolor)
        self.rgb = dccolor.to_rgb()
        self.emoji_round = emote_r
        self.emoji_square = emote_s
        self.emoji_heart = emote_h
        self.name = name
        self.cmdcolor = cmdcolor

    def string(self, input_string: str) -> str:
        return f"{self.cmdcolor}{input_string}\033[0m"

    def text(self, input_string: str) -> str:
        return f"```ansi\n{self.string(input_string)}\033[0m\n```"


class Colored:
    red = ColorGroup(discord.Colour.red(), "Red", "\033[31m", "🟥", "🔴", "❤️")
    blue = ColorGroup(discord.Colour.dark_blue(), "Blue", "\033[34m", "🟦", "🔵", "💙")
    green = ColorGroup(discord.Colour.green(), "Green", "\033[32m", "🟩", "🟢", "💚")
    yellow = ColorGroup(discord.Colour.gold(), "Yellow", "\033[33m", "🟨", "🟡", "💛")
    orange = ColorGroup(discord.Colour.orange(), "Orange", "\033[41m\033[37m", "🟧", "🟠", "🧡")
    purple = ColorGroup(discord.Colour.purple(), "Purple", "\033[35m", "🟪", "🟣", "💜")
    # pink = Color(discord.Colour.magenta(), "Pink", "pink", "??", "", "🩷")
    # aqua = Color(discord.Colour.blue(), "Aqua", "\033[36m", "??", "", "🩵")
    # grey = Color(discord.Colour.light_grey(), "Grey", "grey", "??", "", "🩶")
    white = ColorGroup(discord.Colour.from_rgb(240, 240, 240), "White", "\033[37m", "⬜", "⚪", "🤍")
    black = ColorGroup(discord.Colour.from_rgb(20, 20, 20), "Black", "\033[30m", "⬛", "⚫", "🖤")
    brown = ColorGroup(discord.Colour.dark_gold(), "Brown", "\033[41m\033[30m", "🟫", "🟤", "🤎")

    @classmethod
    def list(cls) -> dict[str, ColorGroup]:
        return {att: getattr(cls, att) for att in dir(cls) if not att.startswith("_") and att not in ("list", "get_color", "text")}

    @classmethod
    def get_color(cls, name: str) -> ColorGroup:
        return getattr(cls, name)

    @classmethod
    def text(cls, texts: List[tuple[str, ColorGroup]]) -> str:
        combined = "".join([clr.string(txt) for txt, clr in texts])
        return f"```ansi\n{combined}\033[0m\n```"


