from functools import lru_cache
from nextcord import Client, SlashApplicationCommand, Object
from nextcord.utils import find

@lru_cache(maxsize=100)
def mentionCommand(client: Client, command, guild: int = None, raw: bool = False) -> str | None:
    if guild:
        guild = Object(guild)
    cmdname = command.split(" ")[0]
    every: list[SlashApplicationCommand] = filter(lambda i: isinstance(i, SlashApplicationCommand), client.get_all_application_commands())
    cmd: SlashApplicationCommand = find(lambda i: i.name == cmdname, every)
    # try:
    #     a = client.get_application_command_from_signature(command, nextcord.ApplicationCommandType.chat_input, guild_id=guild.id if guild else None)
    # except Exception as e:
    #     pass #i dont know the children
    # cmd = filter(lambda i: i.guild == guild, cmd)
    if not cmd:
        return None
    try:
        ment = cmd.get_mention(guild)
    except ValueError as e:
        ment = cmd.get_mention(None)
    ment = ment.partition(":")
    ment = "</" + command + "".join(ment[1:])
    return f"{'`' if raw else ''}{ment}{'`' if raw else ''}"

