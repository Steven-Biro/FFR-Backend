from discord.ext import commands
from discord.utils import get
from discord import File
import logging
from datetime import datetime, timezone
from concurrent.futures import TimeoutError

import constants
import text
from voting.poll import Poll
from voting.stv_election import StvElection


def is_admin(ctx):
    user = ctx.author
    return (any(role.name in constants.ADMINS for role in user.roles)) or (
        user.id == int(140605120579764226))


def is_steven(ctx):
    user = ctx.author
    return user.id == int(140605120579764226)


class Polls(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.polls = dict()
        self.db = db
        try:
            self.load_all()
        except Exception as e:
            logging.error("Error loading saved voting, maybe use command"
                          + " clear_db to wipe stored data")
            logging.exception(e)

    def load_all(self):
        logging.info("loading saved voting")
        # temp = dict(self.redis_db.hgetall('voting'))
        # for k, v in temp.items():
        #     self.polls[k.decode("utf-8")] = pickle.loads(v)
        # for poll in self.polls.values():
        #     logging.debug(poll)

    def save_one(self, id):
        logging.info("saving poll " + id)
        # poll = self.polls[id]
        # self.redis_db.hset("voting",
        #                    id, pickle.dumps(poll,
        #                                     protocol=pickle.HIGHEST_PROTOCOL))
        # logging.info("saved")
        # self.verify_save(id)

    def verify_save(self, id):
        original = self.polls[id]
        # saved = pickle.loads(self.redis_db.hget("voting", id))
        logging.debug("original: " + str(original))
        # logging.debug("saved: " + str(saved))
        # logging.debug(saved == original)

    @commands.command()
    @commands.check(is_steven)
    async def clear_db(self, ctx):
        # self.redis_db.flushall()
        logging.info("cleared redis db")
        self.polls = dict()

    @commands.command(aliases=["cp"])
    @commands.check(is_admin)
    async def createpoll(self, ctx, poll_type, *, name=None):
        if name is None:
            await ctx.author.send("you didnt set a name for your poll")
            return

        pollchannel = await ctx.guild\
            .create_text_channel(name,
                                 category=get(ctx.guild.categories,
                                              name=constants.polls_category),
                                 reason="bot generated channel for a poll,"
                                        + " will be deleted after poll "
                                          "finishes")

        if poll_type == "poll":
            poll = Poll(name, str(pollchannel.id))
        elif poll_type == "election":
            poll = StvElection(name, str(pollchannel.id), constants.seat_count)
        else:
            await ctx.author.send(text.invalid_poll_type)
            return
        self.polls[str(pollchannel.id)] = poll
        self.save_one(str(pollchannel.id))

    @commands.command(aliases=["sp"])
    @commands.check(is_admin)
    async def startpoll(self, ctx):
        try:
            poll = self.polls[str(ctx.channel.id)]
        except KeyError:
            await ctx.author.send(text.no_poll_in_channel)
            await ctx.message.delete()
            return

        if len(poll.options) < 2:
            error_text = text.not_enough_options \
                         + poll.list_options(name_only=True)
            await ctx.author.send(error_text)
            await ctx.message.delete()
            return
        elif poll.started:
            await ctx.author.send(text.poll_already_started)
            await ctx.message.delete()
            return
        elif poll.ended:
            await ctx.author.send(text.poll_already_ended)
            await ctx.message.delete()
            return

        poll.start_poll()
        output = "this poll is now open!\nThe following options are avalible"\
                 + ", use `?vote` in this channel to vote, you will recieve "\
                   "a PM "\
                 + "from FFRBot" + "\n\nOptions:\n\n" + poll.list_options()
        await ctx.channel.send(output)
        self.save_one(str(ctx.channel.id))

    @commands.command(aliases=["ao"])
    @commands.check(is_admin)
    async def addoption(self, ctx, *args):
        try:
            poll = self.polls[str(ctx.channel.id)]
        except KeyError:
            await ctx.author.send(text.no_poll_in_channel)
            await ctx.message.delete()
            return

        if poll.started:
            await ctx.author.send(text.poll_already_started)
            await ctx.message.delete()
            return

        if len(args) != poll.add_option_arg_len:
            await ctx.author.send(text.add_option_wrong_format)
            await ctx.message.delete()
            return

        try:
            poll.add_option(ctx, args)
        except KeyError:
            await ctx.channel.send(text.option_already_exists)
            return

        self.save_one(str(ctx.channel.id))
        await ctx.message.add_reaction('✔')

    @commands.command(aliases=["v"])
    async def vote(self, ctx):
        # TODO combine vote and submitvote using self.bot.wait_for
        try:
            poll = self.polls[str(ctx.channel.id)]
        except KeyError:
            await ctx.author.send(text.no_poll_in_channel)
            await ctx.message.delete()
            return

        account_age = (datetime.now(timezone.utc) -
                       ctx.author.created_at.replace(tzinfo=timezone.utc)).days

        server_join_date = ctx.author.joined_at.replace(tzinfo=timezone.utc)
        bad_hardcoded_date = datetime.fromisoformat(
            "2020-05-08 22:54:53.546944+00:00")

        server_join_ok = server_join_date < bad_hardcoded_date

        if poll.check_if_voted(str(ctx.author.id)):
            await ctx.author.send(text.already_voted)

        elif account_age < constants.voting_age_days:
            await ctx.author.send(text.account_age(account_age,
                                                   constants.voting_age_days))

        elif not server_join_ok:
            await ctx.author.send(text.not_in_server_long_enough)

        elif poll.started is False:
            await ctx.channel.send(text.poll_not_started)

        elif poll.ended is True:
            await ctx.channel.send(text.poll_already_ended)

        else:
            await ctx.author.send(poll.get_vote_text())
            await ctx.author.send(poll.get_submitballot_template())

        await ctx.message.delete()

    @commands.command()
    @commands.dm_only()
    async def submitballot(self, ctx, channel_id, *args):
        try:
            poll = self.polls[channel_id]
        except KeyError:
            await ctx.author.send(text.cant_find_poll)
            return

        account_age = (datetime.now(timezone.utc) -
                       ctx.author.created_at.replace(tzinfo=timezone.utc)).days

        if poll.check_if_voted(str(ctx.author.id)):
            await ctx.author.send(text.already_voted)

        elif account_age < constants.voting_age_days:
            await ctx.author.send(text.account_age(account_age,
                                                   constants.voting_age_days))

        elif poll.started is False:
            await ctx.channel.send(text.poll_not_started)

        elif poll.ended is True:
            await ctx.channel.send(text.poll_already_ended)

        elif not poll.check_valid_ballot(args):
            await ctx.author.send("bad ballot")

        else:
            await ctx.author.send(text.confirm_vote
                                  + "\n"
                                  + poll.confirm_vote_text(args))

            def check(m):
                return m.author == ctx.author\
                    and m.channel == ctx.channel

            reply = None
            while (reply is None
                   or not (reply.content.lower() == "yes"
                           or reply.content.lower() == "no")):
                try:
                    reply = await self.bot.wait_for('message',
                                                    timeout=120,
                                                    check=check)
                except TimeoutError:
                    await ctx.author.send(text.timeout)
                    return
            if reply.content.lower() == "yes":
                print("\n\n" + str(args) + "\n\n")
                poll.submit_vote(str(ctx.author.id), ctx.author.name, args)
                self.save_one(channel_id)
                await ctx.author.send(text.vote_processed)
            else:
                await ctx.author.send(text.vote_not_processed)
                return

    @commands.command(aliases=["ep"])
    @commands.check(is_admin)
    async def endpoll(self, ctx, channel_id=None):
        try:
            poll = self.polls[str(ctx.channel.id)]
        except KeyError:
            await ctx.author.send(text.no_poll_in_channel)
            await ctx.message.delete()
            return

        if not poll.started:
            await ctx.author.send(text.poll_not_started)
            await ctx.message.delete()
            return
        elif poll.ended:
            await ctx.author.send(text.poll_already_ended)
            await ctx.message.delete()
            return

        await ctx.channel.send(text.confirm_end_poll)

        def check(m):
            return m.author == ctx.author\
                and m.channel == ctx.channel

        reply = None
        while (reply is None
               or not (reply.content.lower() == "yes"
                       or reply.content.lower() == "no")):
            try:
                reply = await self.bot.wait_for('message',
                                                timeout=120,
                                                check=check)
            except TimeoutError:
                await ctx.channel.send(text.timeout)
                return
        if reply.content.lower() == "yes":
            output = poll.get_results()
            await ctx.channel.send(text.poll_now_closed)
            csv_file_name = poll.get_csv()
            if csv_file_name:
                with open(csv_file_name, mode="rb") as csv_file:
                    f = File(csv_file)
                    await ctx.channel.send(output, file=f)
            else:
                await ctx.channel.send(output)
            poll.end_poll()
            self.save_one(str(ctx.channel.id))
        else:
            await ctx.channel.send(text.poll_still_open)
            return

    @commands.command()
    @commands.check(is_admin)
    async def undoendpoll(self, ctx):
        try:
            poll = self.polls[str(ctx.channel.id)]
        except KeyError:
            await ctx.author.send(text.no_poll_in_channel)
            await ctx.message.delete()
            return
        if poll.ended:
            poll.undo_end_poll()
            await ctx.message.delete()
        else:
            return

    @commands.command()
    @commands.check(is_admin)
    async def forceclosepoll(self, ctx):
        try:
            poll = self.polls[str(ctx.channel.id)]
        except KeyError:
            await ctx.author.send(text.no_poll_in_channel)
            await ctx.message.delete()
            return

        await ctx.channel.send("reply `yes` to forcibly end this poll, "
                               + "or reply `no` to stop")

        def check(m):
            return m.author == ctx.author\
                and m.channel == ctx.channel

        reply = None
        while (reply is None
               or not (reply.content.lower() == "yes"
                       or reply.content.lower() == "no")):
            try:
                reply = await self.bot.wait_for('message',
                                                timeout=120,
                                                check=check)
            except TimeoutError:
                await ctx.channel.send(text.timeout)
                return
        if reply.content.lower() == "yes":
            await ctx.channel.send("logging who deleted this poll with "
                                   + "a role create and delete")
            reason = poll.poll_id + " force deleted by: " +\
                ctx.author.name + "\ndisplay name: " +\
                ctx.author.display_name
            role = await ctx.guild.create_role(name="deleted-poll",
                                               reason=reason)
            await role.delete(reason=reason)
            poll.end_poll()
            self.save_one(poll.get_channel())
            await ctx.message.add_reaction('✔')

    @commands.command()
    @commands.check(is_admin)
    async def getcsv(self, ctx):
        try:
            poll = self.polls[str(ctx.channel.id)]
        except KeyError:
            await ctx.author.send(text.no_poll_in_channel)
            await ctx.message.delete()
            return
        file_name = poll.get_csv()
        with open(file_name, mode="rb") as csv_file:
            f = File(csv_file)
            await ctx.channel.send("votes", file=f)

    @commands.command()
    async def getcount(self, ctx):
        try:
            poll = self.polls[str(ctx.channel.id)]
        except KeyError:
            await ctx.author.send(text.no_poll_in_channel)
            await ctx.message.delete()
            return
        await ctx.author.send("number of ballots cast: "
                              + str(poll.get_count()))
        await ctx.message.delete()

    @commands.command()
    @commands.check(is_steven)
    async def removevote(self, ctx, *args):
        try:
            poll = self.polls[str(ctx.channel.id)]
        except KeyError:
            await ctx.author.send(text.no_poll_in_channel)
            await ctx.message.delete()
            return

        for user_id in args:
            try:
                result = poll.remove_voter(user_id)
                if result is False:
                    await ctx.author.send(
                        "the user id: " + user_id + " was not found in the "
                                                    "voter list")
            except Exception:
                await ctx.author.send(
                    "the user id: " + user_id + " caused an exception")
                continue

    @commands.command()
    @commands.check(is_steven)
    async def check(self, ctx, pollid=None):
        try:
            if (pollid):
                poll = self.polls[str(pollid)]
            else:
                poll = self.polls[str(ctx.channel.id)]
        except KeyError:
            await ctx.author.send(text.no_poll_in_channel)
            await ctx.message.delete()
            return

        try:
            file_name = poll.get_voter_info()
            with open(file_name, mode="rb") as csv_file:
                f = File(csv_file)
                await ctx.author.send("voter_info", file=f)
            await ctx.message.delete()
        except Exception:
            await ctx.message.delete()

    @commands.command()
    @commands.check(is_steven)
    async def check2(self, ctx, pollid=None):
        try:
            if (pollid):
                poll = self.polls[str(pollid)]
            else:
                poll = self.polls[str(ctx.channel.id)]
        except KeyError:
            await ctx.author.send(text.no_poll_in_channel)
            await ctx.message.delete()
            return

        try:
            voter_names = poll.get_voter_names()
            await ctx.author.send(str(voter_names))
            await ctx.message.delete()
        except Exception:
            await ctx.message.delete()
