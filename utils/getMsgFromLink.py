async def getMsgFromLink(client, link):
    link = link.split('/')
    channel_id = int(link[5])
    msg_id = int(link[6])
    channel = client.get_channel(channel_id)
    message = channel.get_partial_message(msg_id)
    return message
