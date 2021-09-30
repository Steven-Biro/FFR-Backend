import asyncio
import asyncio
import logging
import re
import time
from datetime import datetime, timedelta
from math import ceil
from random import random
from typing import List

from discord.ext import commands
from discord.utils import get
from discord.message import Message
from pymongo import MongoClient

from .racing.races import Races
from .roles import Roles
from .voting.polls import Polls
from . import constants

# format logging
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S")

description = "FFR discord bot"

db = MongoClient('localhost', 27017)

bot = commands.Bot(command_prefix="?", description=description,
                   case_insensitive=True)


bot.add_cog(Races(bot, db))
bot.add_cog(Roles(bot))
bot.add_cog(Polls(bot, db))


@bot.event
async def on_ready():
    logging.info("Logged in as")
    logging.info(bot.user.name)
    logging.info(bot.user.id)
    logging.info("------")


def is_admin(ctx):
    user = ctx.author
    return (any(role.name in constants.ADMINS for role in user.roles))\
        or (user.id == int(140605120579764226))


def allow_seed_rolling(ctx):
    return (ctx.channel.name == constants.call_for_races_channel) or \
           (ctx.channel.category_id == get(ctx.guild.categories, name="races")
            .id)


@bot.command()
async def purgemembers(ctx):
    """
    Removes members from the role associated with the channel,
    works for asyncseedrole and challengeseedrole
    :param ctx: context of the command
    :return: None
    """
    user = ctx.message.author
    role = await getrole(ctx)

    if role in user.roles and role.name in constants.adminroles:
        if role.name == constants.challengeseedadmin:
            role = get(ctx.message.guild.roles,
                       name=constants.challengeseedrole)
        else:
            role = get(ctx.message.guild.roles,
                       name=constants.asyncseedrole)
        members = ctx.message.guild.members
        role_members = [x for x in members if role in x.roles]

        for x in role_members:
            await x.remove_roles(role)
    else:
        await user.send("... Wait a second.. YOU AREN'T AN ADMIN! (note, you"
                        " need the correct admin role and need to use this"
                        " in the spoilerchat for the role you want to purge"
                        " members from)")

    await ctx.message.delete()


@bot.command()
async def submit(ctx, runnertime: str = None):
    """
    Submits a runners time to the leaderboard and gives the appropriate role
    :param runnertime: time of the runner, in the format H:M:S, e.g. 2:32:12
    :param ctx: context of the command
    :return: None
    """
    user = ctx.message.author
    role = await getrole(ctx)
    if (role.name == constants.ducklingrole and
            constants.rolerequiredduckling not in
            [role.name for role in user.roles]):
        await user.send("You're not a duckling!")
        await ctx.message.delete()
        return

    if runnertime is None:
        await user.send("You must include a time when you submit a time.")
        await ctx.message.delete()
        return

    if role is not None and role not in user.roles\
            and role.name in constants.nonadminroles:
        try:
            # convert to seconds using this method to make sure the time is
            # readable and valid
            # also allows for time input to be lazy, ie 1:2:3 == 01:02:03 yet
            # still maintain a consistent style on the leaderboard
            t = datetime.strptime(runnertime, "%H:%M:%S")
        except ValueError:
            await user.send("The time you provided '" + str(runnertime) +
                            "', this is not in the format HH:MM:SS"
                            "(or you took a day or longer)")
            await ctx.message.delete()
            return

        await user.add_roles(role)
        delta = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
        username = re.sub('[()-]', '', user.display_name)
        leaderboard = await getleaderboard(ctx)
        leaderboard_list = leaderboard.content.split("\n")

        # the title is at the start and the forfeit # is after the hyphen at
        # the end of the last line
        title = leaderboard_list[0]
        forfeits = int(leaderboard_list[-1].split('-')[-1])

        # trim the leaderboard to remove the title and forfeit message
        leaderboard_list = leaderboard_list[2:len(leaderboard_list) - 2]

        for i in range(len(leaderboard_list)):
            leaderboard_list[i] = re.split('[)-]', leaderboard_list[i])[1:]

        # convert the time back to hours minutes and seconds for the
        # leaderboard
        totsec = delta.total_seconds()
        h = totsec // 3600
        m = (totsec % 3600) // 60
        s = (totsec % 3600) % 60

        leaderboard_list.append(
            [" " + username + " ", " %d:%02d:%02d" % (h, m, s)])

        # sort the times
        leaderboard_list.sort(
            key=lambda x: datetime.strptime(x[1].strip(), "%H:%M:%S"))

        # build the string for the leaderboard
        new_leaderboard = title + "\n\n"
        for i in range(len(leaderboard_list)):
            new_leaderboard += str(i + 1) + ")" +\
                leaderboard_list[i][0] + "-" +\
                leaderboard_list[i][1] + "\n"
        new_leaderboard += "\nForfeits - " + str(forfeits)

        await leaderboard.edit(content=new_leaderboard)
        await (await getspoilerchat(ctx)).send('GG %s' % user.mention)
        await ctx.message.delete()
        await changeparticipants(ctx)
    else:
        await user.send("You already have the relevent role.")
        await ctx.message.delete()


@bot.command()
async def remove(ctx):
    """
    Removes people from the leaderboard and allows them to reenter a time
    This entire function is gross, it works but is messy
    :param ctx: context of the command
    :param players: @mentions of the players that will be removed from
                    the leaderboard
    :return: None
    """
    user = ctx.message.author
    if ctx.message.mentions is None:
        await user.send("You did not mention a player.")
        await ctx.message.delete()
        return

    channel = ctx.message.channel
    roles = ctx.message.guild.roles
    role = None
    channels = ctx.message.guild.channels
    challengeseed = get(channels, name=constants.challengeseedleaderboard)
    constants.asyncseed = get(channels, name=constants.asyncleaderboard)
    if channel == challengeseed:
        role = get(roles, name=constants.challengeseedadmin)
        remove_role = get(roles, name=constants.challengeseedrole)
        participantnumchannel = get(channels,
                                    name=constants.challengeseedchannel)
    if channel == constants.asyncseed:
        role = get(roles, name=constants.asyncseedadmin)
        remove_role = get(roles, name=constants.asyncseedrole)
        participantnumchannel = get(channels, name=constants.asyncchannel)
    if role in user.roles:
        leaderboard = await channel.history(limit=100).flatten()
        for x in leaderboard:
            if bot.user == x.author:
                leaderboard = x
                break

        leaderboard_list = leaderboard.content.split("\n")

        # the title is at the start and the forfeit # is after the hyphen at
        # the end of the last line
        title = leaderboard_list[0]
        forfeits = int(leaderboard_list[-1].split('-')[-1])

        # trim the leaderboard to remove the title and forfeit message
        leaderboard_list = leaderboard_list[2:len(leaderboard_list) - 2]

        for i in range(len(leaderboard_list)):
            leaderboard_list[i] = re.split('[)-]', leaderboard_list[i])[1:]

        players = ctx.message.mentions
        if not players:
            await user.send("You did not mention a player.")
            await ctx.message.delete()
            return

        for player in players:
            i = 0
            for i in range(len(leaderboard_list)):
                if leaderboard_list[i][0][1:len(
                        leaderboard_list[i][0]) - 1] == re.sub('[()-]', '',
                                                               player
                                                               .display_name):
                    del leaderboard_list[i]
                    await player.remove_roles(remove_role)
                    await changeparticipants(ctx, increment=False,
                                             channel=participantnumchannel)
                    break

        # should already be sorted
        # leaderboard_list.sort(
        #   key=lambda x: datetime.strptime(x[1].strip(), "%H:%M:%S"))

        # build the string for the leaderboard
        new_leaderboard = title + "\n\n"
        for i in range(len(leaderboard_list)):
            new_leaderboard += str(i + 1) + ")" +\
                leaderboard_list[i][0] + "-" +\
                leaderboard_list[i][1] + "\n"
        new_leaderboard += "\nForfeits - " + str(forfeits)

        await leaderboard.edit(content=new_leaderboard)
        await ctx.message.delete()


@bot.command()
async def createleaderboard(ctx, name):
    """
    Creates a leaderboard post with a title and the number of forfeits
    :param ctx: context of the command
    :param name: title of the leaderboard
    :return: None
    """

    user = ctx.message.author
    if name is None:
        await user.send("You did not submit a name.")
        await ctx.message.delete()
        return
    role = await getrole(ctx)

    # gross way of doing this, works for now
    if role in user.roles and role.name == constants.challengeseedadmin:
        await get(ctx.message.guild.channels,
                  name=constants.challengeseedleaderboard)\
            .send(name + "\n\nForfeits - 0")
        await get(ctx.message.guild.channels,
                  name=constants.challengeseedchannel)\
            .send("Number of participants: 0")

    elif role in user.roles and role.name == constants.asyncseedadmin:
        await get(ctx.message.guild.channels,
                  name=constants.asyncleaderboard)\
            .send(name + "\n\nForfeits - 0")
        await get(ctx.message.guild.channels, name=constants.asyncchannel)\
            .send("Number of participants: 0")

    elif role in user.roles and role.name == constants.ducklingadminrole:
        await get(ctx.message.guild.channels,
                  name=constants.ducklingleaderboard)\
            .send(name + "\n\nForfeits - 0")
        await get(ctx.message.guild.channels, name=constants.ducklingchannel)\
            .send("Number of participants: 0")

    else:
        await user.send(("... Wait a second.. YOU AREN'T AN ADMIN! (note, you"
                         " need the admin role for this channel)"))

    await ctx.message.delete()


@bot.command()
async def ff(ctx):
    """
    Increments the number of forfeits and gives the appropriate
    role to the user
    :param ctx: context of the command
    :return: None
    """
    user = ctx.message.author
    role = await getrole(ctx)

    if role is not None and role not in user.roles\
            and role.name in constants.nonadminroles:

        await user.add_roles(role)
        leaderboard = await getleaderboard(ctx)
        new_leaderboard = leaderboard.content.split("\n")
        forfeits = int(new_leaderboard[-1].split("-")[-1]) + 1
        new_leaderboard[-1] = "Forfeits - " + str(forfeits)
        seperator = "\n"
        new_leaderboard = seperator.join(new_leaderboard)

        await leaderboard.edit(content=new_leaderboard)
        await ctx.message.delete()
        await changeparticipants(ctx)
    else:
        await ctx.message.delete()


# @bot.command()
# async def testexit():
#     await ctx.channel.send("exiting, should restart right away")
#     SystemExit()


@bot.command()
async def spec(ctx):
    """
    Gives the user the appropriate role
    :param ctx: context of the command
    :return: None
    """
    user = ctx.message.author
    role = await getrole(ctx)
    if role is not None and role.name in constants.nonadminroles:
        await user.add_roles(role)
    await ctx.message.delete()


async def getrole(ctx):
    """
    Returns the Role object depending on the channel the command is used in
    Acts as a check for making sure commands are executed in the correct
    spot as well
    :param ctx: context of the command
    :return: Role or None
    """

    user = ctx.message.author
    roles = ctx.message.guild.roles
    channel = ctx.message.channel
    channels = ctx.message.guild.channels
    challengeseed = get(channels, name=constants.challengeseedchannel)
    asyncseed = get(channels, name=constants.asyncchannel)
    ducklingseed = get(channels, name=constants.ducklingchannel)
    chalseedspoilerobj = get(channels, name=constants.challengeseedspoiler)
    asyseedspoilerobj = get(channels, name=constants.asyncspoiler)
    duckseedspoilerobj = get(channels, name=constants.ducklingspoiler)

    if channel == challengeseed:
        role = get(roles, name=constants.challengeseedrole)
    elif channel == asyncseed:
        role = get(roles, name=constants.asyncseedrole)
    elif channel == chalseedspoilerobj:
        role = get(roles, name=constants.challengeseedadmin)
    elif channel == asyseedspoilerobj:
        role = get(roles, name=constants.asyncseedadmin)
    elif channel == ducklingseed:
        role = get(roles, name=constants.ducklingrole)
    elif channel == duckseedspoilerobj:
        role = get(roles, name=constants.ducklingadminrole)
    else:
        await user.send("That command isn't allowed here.")
        return None

    return role


async def getleaderboard(ctx):
    """
    Returns the leaderboard Message object depending on the channel the
    command is used in
    :param ctx: context of the command
    :return: Message or None
    """
    user = ctx.message.author
    channel = ctx.message.channel
    channels = ctx.message.guild.channels
    challengeseed = get(channels, name=constants.challengeseedchannel)
    asyncseed = get(channels, name=constants.asyncchannel)
    ducklingseed = get(channels, name=constants.ducklingchannel)

    if channel == challengeseed:
        leaderboard = await get(
            channels,
            name=constants.challengeseedleaderboard).history(
            limit=100).flatten()
    elif channel == asyncseed:
        leaderboard = await get(channels, name=constants.asyncleaderboard)\
            .history(limit=100).flatten()
    elif channel == ducklingseed:
        leaderboard = await get(channels,
                                name=constants.ducklingleaderboard).history(
            limit=100).flatten()
    else:
        await user.send("That command isn't allowed here.")
        return None

    for x in leaderboard:
        if bot.user == x.author:
            leaderboard = x
            break

    return leaderboard


async def getspoilerchat(ctx):
    """
    Returns the spoiler Channel object depending on the channel the command
    is used in
    :param ctx: context of the command
    :return: Channel or None
    """

    user = ctx.message.author
    channel = ctx.message.channel
    channels = ctx.message.guild.channels
    challengeseed = get(channels, name=constants.challengeseedchannel)
    asyncseed = get(channels, name=constants.asyncchannel)
    ducklingseed = get(channels, name=constants.ducklingchannel)

    if channel == challengeseed:
        spoilerchat = get(channels, name=constants.challengeseedspoiler)
    elif channel == asyncseed:
        spoilerchat = get(channels, name=constants.asyncspoiler)
    elif channel == ducklingseed:
        spoilerchat = get(channels, name=constants.ducklingspoiler)
    else:
        await user.send("That command isn't allowed here.")
        return None

    return spoilerchat


async def changeparticipants(ctx, increment=True, channel=None):
    """
    changes the participant number
    :param ctx: context of the command
    :param increment: sets if it is incremented or decremented
    :return: None
    """

    participants: List[Message] = await (
        ctx.message.channel if channel is None else channel).\
        history(limit=100).flatten()
    for x in participants:
        if x.author == bot.user:
            participants = x
            break
    num_partcipents = int(participants.content.split(":")[1])
    if increment:
        num_partcipents += 1
    else:
        num_partcipents -= 1
    new_participants = "Number of participants: " + str(num_partcipents)
    await participants.edit(content=new_participants)


# used to clear channels for testing purposes

# @bot.command(pass_context = True)
# async def purge(ctx):
#     channel = ctx.message.channel
#     await bot.purge_from(channel, limit=100000)

@bot.command()
async def whoami(ctx):
    await ctx.author.send(ctx.author.id)
    await ctx.message.delete()


@bot.command()
async def roll(ctx, dice):
    match = re.match(r"((\d{1,3})?d\d{1,9})", dice)
    if match is None:
        await ctx.message.channel.send(
            "Roll arguments must be in the form [N]dM ie. 3d6, d8")
        return
    rollargs = match.group().split('d')

    try:
        rollargs[0] = int(rollargs[0])
    except BaseException:
        rollargs[0] = 1
    rollargs[1] = int(rollargs[1])
    result = [ceil(random() * rollargs[1]) for i in range(rollargs[0])]
    textresult = "{} result: **{}**".format(match.group(), sum(result))
    await ctx.message.channel.send(textresult)


@bot.command()
async def coin(ctx):
    coinres = ""
    if random() >= 0.5:
        coinres = "Heads"
    else:
        coinres = "Tails"
    await ctx.message.channel.send("Coin landed on: **{}**".format(coinres))


def handle_exit(client, loop):
    # taken from https://stackoverflow.com/a/50981577
    loop.run_until_complete(client.logout())
    for t in asyncio.Task.all_tasks(loop=loop):
        if t.done():
            t.exception()
            continue
        t.cancel()
        try:
            loop.run_until_complete(asyncio.wait_for(t, 5, loop=loop))
            t.exception()
        except asyncio.InvalidStateError:
            pass
        except asyncio.TimeoutError:
            pass
        except asyncio.CancelledError:
            pass


def run_client(client, *args, **kwargs):
    loop = asyncio.get_event_loop()
    while True:
        try:
            logging.info("Starting connection")
            loop.run_until_complete(client.start(*args, **kwargs))
        except KeyboardInterrupt:
            handle_exit(client, loop)
            client.loop.close()
            logging.info("Program ended")
            break
        except Exception as e:
            logging.exception(e)
            handle_exit(client, loop)
        logging.info("Waiting until restart")
        time.sleep(constants.Sleep_Time)


def start():
    with open('token.txt', 'r') as f:
        token = f.read()
    token = token.strip()
    
    run_client(bot, token)
