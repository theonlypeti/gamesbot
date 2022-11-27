import os
import random
from nextcord.ext import commands
import asyncpraw
import nextcord as discord
import emoji
from dotenv import load_dotenv
load_dotenv(r"./credentials/reddit.env") #this is where the reddit account password is stored


class RedditCog(commands.Cog):
    def __init__(self, client, baselogger):
        global logger
        self.client = client
        logger = baselogger.getChild(f"{__name__}Logger")

        if os.getenv("REDDIT_CLIENT_ID") == "example":
            logger.warning(
                """Reddit login data was not changed in credentials/reddit.env, reddit commands will not be available
                get your own reddit api token here https://www.reddit.com/prefs/apps
                or run this bot with the "--no_reddit" command line argument.""")

        self.reddit = asyncpraw.Reddit(client_id=os.getenv("REDDIT_CLIENT_ID"),
                                       client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                                       user_agent=os.getenv("REDDIT_USER_AGENT"),
                                       username=os.getenv("REDDIT_USERNAME"),
                                       password=os.getenv("REDDIT_PWD"))

    @discord.slash_command(name="sub", description="Retrieve a random post from a given subreddit.")
    async def sub(self, ctx: discord.Interaction, subreddit: str = discord.SlashOption(name="subreddit", description="a subreddit name without the /r/")):
        await ctx.response.defer()
        if not ctx.channel.is_nsfw() and await self.reddit.subreddit(subreddit.strip("/r/")).over18:
            await ctx.send(embed=discord.Embed(
                title="That is an NSFW subreddit you are tying to send into a non-NSFW text channel.",
                color=discord.Color.red()))
            return
        try:
            try:
                sub = await self.reddit.subreddit(subreddit.strip("/r/"))
                post = await sub.random()
            except Exception as e:
                #        except redditapi.prawcore.exceptions.NotFound:
                #            await ctx.channel.send("That subreddit is not found??")
                #        except redditapi.prawcore.exceptions.Forbidden:
                #            await ctx.channel.send("Forbidden: received 403 HTTP response, what kinda sub are you trying to see?!?")
                await ctx.send(f"{e}")  # i dont really know how to handle these errors xd
                logger.error(e)
            else:
                if not post:
                    await ctx.send("That subreddit does not allow sorting by random, sorry.")
                    return
                if post.is_self:  # if only textpost, no link or image
                    viewObj = discord.ui.View()
                    viewObj.add_item(discord.ui.Button(
                        style=discord.ButtonStyle.link,
                        url="https://redd.it/" + post.id,
                        label="Comments",
                        emoji=emoji.emojize(":memo:")))
                    await ctx.send(embed=discord.Embed(
                        title=post.title,
                        description=(post.selftext if post.selftext else None)
                    ), view=viewObj)
                else:
                    await ctx.send(post.url)
        except Exception as e:
            await ctx.send(f"{e}")
            raise e

    @discord.slash_command(name="cat", description="Send a random cat pic")
    async def cat(self, ctx):
        await ctx.response.defer()
        subs = "absolutelynotmeow_irl,Catsinasock,kittyhasaquestion,catloaf,thisismylifemeow,MEOW_IRL,noodlebones,bottlebrush,notmycat,Blep,CatsOnCats,PetAfterVet,CuddlePuddle,CatsAndPlants,curledfeetsies,teefies,tuckedinkitties,catfaceplant,CatsAndDogsBFF,squishypuppers,airplaneears,shouldercats,PeanutWhiskers,catbellies,CatCircles,catfaceplant,catsonglass,ragdolls,fatSquirrelHate,SupermodelCats,Catswhoyell,IllegallySmolCats,aww,AnimalsBeingBros,peoplefuckingdying,thecatdimension,TouchThaFishy,FancyFeet,cuddleroll,DrillCats,CatsWhoYell,catsareliquid,blurrypicturesofcats,spreadytoes,sorryoccupied,politecats,blackpussy,KittyTailWrap,thecattrapisworkings,khajiithaswares,catgrabs,stolendogbeds,bridgecats,standardissuecats,catswhoquack,catpranks,catsarealiens,dagadtmacskak,fatcat,fromKittenToCat,illegallySmolCats,MaineCoon,noodlebones,politecats,scrungycats,shouldercats,sorryoccupied,stolendogbeds,stuffOnCats,thinkcat,disneyeyes,cuddlykitties,wet_pussy,girlswithhugepussies,catsinboxes,catsonmeth,catsstandingup,catsstaringatthings,catsvsthemselves,catswhoblep,catswithjobs,catswithmustaches,OneOrangeBraincell".split(",")
        sub = random.choice(subs) #pick from a list of cat subs
        catsub = await self.reddit.subreddit(sub)
        try:
            async for submission in catsub.stream.submissions():
                if submission.url.startswith("https://i"): #get an image
                    await ctx.send(submission.url)
                    return
        except Exception as e:
            await ctx.send(e)

    @discord.slash_command(name="bored", description="Word games to play with friends in a chat")
    async def bored(self, ctx: discord.Interaction):
        try:
            sub = await self.reddit.subreddit("threadgames")
            post = await sub.random()
        except Exception as e:
            await ctx.send(f"{e}")
            raise e
        else:
            if post.is_self:
                viewObj = discord.ui.View()
                viewObj.add_item(discord.ui.Button(
                    style=discord.ButtonStyle.link,
                    url="https://redd.it/" + post.id,
                    label="Comments",
                    emoji=emoji.emojize(":memo:")))
                await ctx.send(embed=discord.Embed(
                    title=post.title,
                    description=(post.selftext if post.selftext else "")
                    ),
                    view=viewObj)
            else:
                await ctx.send(post.url)


def setup(client, baselogger):
    client.add_cog(RedditCog(client, baselogger))
