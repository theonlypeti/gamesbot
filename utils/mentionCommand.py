def getCommandId(client, command) -> dict:
    # every = client.get_application_commands()
    # for i in every:
    #     if i.name == command:
    #         ids = {}
    #         for guild, value in i.command_ids.items():
    #             if guild is not None:
    #                 ids.update({client.get_guild(guild).name: value})
    #             else:
    #                 ids.update({"Global": value})
    #         return {command: ids}

    return {command: {client.get_guild(i[0][0]) or "Global": i[0][1] for i in (tuple(comm.command_ids.items()) for comm in (comm for comm in client.get_application_commands() if comm.PROJECT_NAME == command))}}


def mentionCommand(client, command:str, guild: int = None, raw: bool = False) -> str:
    ids = getCommandId(client, command.split(" ")[0])
    iddict = list(ids.values())[0]
    if guild is not None:
        if int(guild) in iddict:
            return f"{'`' if raw else ''}</{command}:{iddict[int(guild)]}>{'`' if raw else ''}"
    return f"{'`' if raw else ''}</{command}:{iddict['Global']}>{'`' if raw else ''}"
