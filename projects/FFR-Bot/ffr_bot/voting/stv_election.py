import math
from voting.poll import Poll, AlreadyVoted, VoteNotOpen, VoteAlreadyClosed
from voting.ffrvoter import FFRVoter
import logging
import csv


class StvElection(Poll):
    """
    A single transferable vote election
    https://en.wikipedia.org/wiki/Single_transferable_vote

    :raises KeyError: [description]
    :raises KeyError: [description]
    """

    def __init__(self, poll_id, channel_id, seat_count):
        logging.debug("creating STV election")
        super().__init__(poll_id, channel_id)
        self.seat_count = seat_count
        self.type = "election"
        self.add_option_arg_len = 1

    def update_description(self, id: str, description: str):
        try:
            self.options[id]["description"] = description
        except KeyError:
            raise KeyError("That id doesn't exist")

    def list_options(self, name_only=False):
        r_val = ""
        for option in self.options.values():
            r_val += (str(option["mention"])
                      + "\n  display name: "
                      + str(option["display_name"])
                      + "\n\n")
        return r_val

    def add_option(self, ctx: any, args: list):
        mentions = ctx.message.mentions
        user = mentions[0]
        id = str(user.id)
        mention = user.mention
        display_name = user.display_name
        if (id in self.options):
            raise KeyError("That id already exists")
        else:
            self.options[id] = {"id": id,
                                "mention": mention,
                                "display_name": display_name,
                                "index": len(self.options)}

    def get_vote_text(self):
        r_val = "\n\n\nCandidates:\n"
        r_val += self.list_options()
        r_val += ("\n\n\nTo vote in this poll, rank the avalible options"
                  + " starting at 1, copy and paste the following, and "
                  + "replace the <x>s with your ranking:")
        return r_val

    def get_submitballot_template(self):
        r_val = "\n\n?submitballot " + self.channel_id
        for option in self.options.values():
            r_val += ("\n\"<x>, "
                      + option["display_name"]
                      + ", "
                      + str(option["id"])
                      + "\"")

        return r_val

    def check_valid_ballot(self, ballot_args: list):
        ranks = []
        try:
            for arg in ballot_args:
                rank = arg.split(",")[0].strip("<>")
                id = arg.split(",")[2].strip()
                logging.debug(rank)
                logging.debug(id)
                int(id)
                if rank == "x":
                    continue
                rank = int(rank)
                id_exists = id in self.options.keys()
                rank_valid = (rank > 0
                              and rank <= len(self.options)
                              and rank not in ranks)
                if not (id_exists and rank_valid):
                    return False
                ranks.append(rank)
        except (ValueError, IndexError):
            return False
        count = 0
        for rank in sorted(ranks):
            count += 1
            if rank != count:
                return False
        if count != len(ranks) or count == 0:
            return False

        return True

    def process_ballot(self, ballot_args):
        ballot = dict()
        for arg in ballot_args:
            rank = arg.split(",")[0].strip("<>")
            if rank == "x":
                continue
            id = arg.split(",")[2].strip()
            ballot[str(int(rank))] = id
        return ballot

    def confirm_vote_text(self, ballot_args: list):
        ballot_text = "Rank | User | display name\n\n"
        ballot = self.process_ballot(ballot_args)
        logging.info(str(ballot_args) + "\n" + str(ballot))

        for key, value in sorted(ballot.items(), key=lambda rank:
                                 int(rank[0])):
            option = self.options[value]
            ballot_text += (str(key)
                            + " | "
                            + str(option["mention"])
                            + " | "
                            + option["display_name"]
                            + "\n")

        return ballot_text

    def submit_vote(self, voter_id: str, voter_name: str, ballot_args: list):
        """
        Adds a vote for the voter with the id given for the votee id given

        :param voter_id: The id for the discord user voting
        :type voter_id: str
        :param voter_name: The name for the discord user voting
        :type voter_name: str
        :param ballot_args: the ballot
        :type ballot_args: list
        """
        if self.started is False:
            raise VoteNotOpen

        elif self.ended is True:
            raise VoteAlreadyClosed

        elif self.check_if_voted(voter_id):
            raise AlreadyVoted

        else:
            voter = FFRVoter(voter_id, voter_name)
            ballot = self.process_ballot(ballot_args)
            try:
                voter.set_vote(ballot)
                self.voters[voter_id] = voter
            except KeyError:
                logging.error("KeyError in submit_vote")
                pass

    def get_results(self):
        results = self.get_winners()
        r_val = "The winners are: "
        for winner in results["winners"]:
            r_val += "\n" + self.options[winner]["mention"]

        if len(results["tied"]) != 0:
            r_val += "\nThe following people tied:\n"
            for tie in results["tied"]:
                r_val += self.options[tie]["mention"] + "\n"

        r_val += "\n\nTotal votes: " + str(len(self.voters))
        return r_val

    def get_winner(self):
        raise NotImplementedError

    def get_winners(self):
        quota = self.calc_quota()
        logging.info("Quota: " + str(quota))
        winners = set()
        options = set(self.options.keys())
        remaining_options = options - winners
        votes = [voter.get_vote() for voter in self.voters.values()]
        tied = set()
        round_num = 1
        count = None

        while (len(winners) < self.seat_count
               and len(winners) + len(remaining_options) != self.seat_count
               and len(tied) == 0):

            count = self.update_count(count,
                                      round_num,
                                      votes,
                                      options,
                                      winners,
                                      remaining_options,
                                      quota)

            try:
                max_count = max([v["total"] for k, v in count[str(
                    round_num)].items() if k in remaining_options])
            except ValueError:
                logging.info("no remaining options, options: "
                             + str(remaining_options)
                             + "\nwinners: "
                             + str(winners))
                return {"winners": winners, "tied": tied}

            logging.info("Max count: " + str(max_count))
            if max_count >= quota:

                in_progress_winners = set()
                for k, v in count[str(round_num)].items():
                    if v["total"] >= quota:
                        in_progress_winners.add(k)
                        logging.info("winner id: " + str(k))

                winners |= in_progress_winners
                remaining_options -= winners

            else:
                min_count = min([v["total"] for k, v in count[str(
                    round_num)].items() if k in remaining_options])
                logging.info("Min count: " + str(min_count))
                options_to_remove = set([option for option
                                         in options if option
                                         in remaining_options
                                         and count[str(round_num)]
                                         [option]["total"]
                                         == min_count])
                logging.info("options to remove" + str(options_to_remove))

                if (len(
                        remaining_options -
                        options_to_remove)
                        + len(winners)) < self.seat_count:
                    tied = options_to_remove
                else:
                    remaining_options -= options_to_remove

            round_num += 1

        if (len(winners) < self.seat_count
                and len(tied) == 0):
            if len(winners) + len(remaining_options) == self.seat_count:
                winners |= remaining_options
            else:
                logging.warning("no tied, but winners + remaining"
                                + " is not equal to the seat count!!")
        logging.info("Winners: " + str(winners))
        logging.info("Tied: " + str(tied))
        return {"winners": winners, "tied": tied}

    def update_count(
            self,
            count,
            round_num,
            votes,
            options,
            winners,
            remaining_options,
            quota):

        if count is None:
            count = {str(round_num): dict()}

            for option in options:
                count[str(round_num)][option] = {"votes": [], "total": 0}

            logging.info("logging votes")
            for vote in votes:
                logging.info(vote)
                vote["weight"] = 1
                count[str(round_num)][vote["1"]]["votes"].append(vote)

        else:
            count[str(round_num)] = dict()
            removed_options = []
            for option_key, option_v in count[str(round_num - 1)].items():
                if option_key in remaining_options:
                    count[str(round_num)][option_key] = option_v
                else:
                    removed_options.append(option_key)

            for removed_option_key in removed_options:
                logging.info("removed option key is: "
                             + str(removed_option_key))
                option = self.options[removed_option_key]
                for vote in\
                        count[str(round_num - 1)][removed_option_key]["votes"]:
                    logging.info("new voter")
                    for k, v in sorted(
                            vote.items(), key=lambda x: self.vote_sort(x)):
                        if k == "weight":
                            continue
                        logging.info("vote info stuff: " + str(k) + " "
                                     + str(v))
                        logging.info("remaining options: "
                                     + str(remaining_options))
                        logging.info(str(v)
                                     + " in remaining options: "
                                     + str(v in remaining_options))
                        if v in remaining_options:
                            logging.info("found next ranked option still"
                                         + " in the running: " + str(v))
                            if removed_option_key in winners:
                                logging.info(
                                    "voter's earlier option won: "
                                    + str(removed_option_key))
                                total = count[str(round_num - 1)
                                              ][removed_option_key]["total"]
                                surplus = total - quota
                                old_weight = str(vote["weight"])
                                vote["weight"] *= surplus / total
                                weight = str(vote["weight"])
                                logging.info("\ntotal votes for previous "
                                             + "option: " + str(total) + "\n"
                                             + "quota: " + str(quota) + "\n"
                                             + "surplus: " + str(surplus)
                                             + "\nold weight: " + old_weight
                                             + "\nnew weight: " + weight)
                                if vote["weight"] == 0:
                                    logging.info("vote weight is zero,"
                                                 + " skipping")
                                    break
                            logging.info("transering vote of weight: "
                                         + str(vote["weight"])
                                         + " to: "
                                         + str(v))
                            count[str(round_num)][v]["votes"].append(vote)
                            break

        # update the total vote count for that option
        for option in count[str(round_num)].values():
            total = 0
            for vote in option["votes"]:
                total += vote["weight"]
            option["total"] = total

        logging.info("round count: " + str(count[str(round_num)]))
        return count

    def vote_sort(self, key):
        try:
            return int(key[0])
        except ValueError:
            return -1

    def calc_quota(self):
        """
        https://en.wikipedia.org/wiki/Single_transferable_vote
        #More_refined_method:_setting_the_quota

        :return: the required number of votes to be elected
        :rtype: int
        """
        votes = len(self.voters)
        return (math.floor(votes / (self.seat_count + 1))) + 1

    def get_csv(self):
        votes = [voter.get_vote() for voter in self.voters.values()]
        for i in range(len(votes)):
            for k in votes[i].keys():
                votes[i][k] += (" - "
                                + self.options[votes[i][k]]["display_name"]
                                + " - "
                                + self.options[votes[i][k]]["mention"])
        name = "votes.csv"
        with open(name, 'w') as csvFile:
            fields = [str(x) for x in range(1, len(self.options) + 1)]
            writer = csv.DictWriter(csvFile, fieldnames=fields)
            writer.writeheader()
            writer.writerows(votes)
        csvFile.close()
        return name

    def get_voter_info(self):
        votes = []
        for voter in self.voters.values():
            vote = voter.get_vote()
            for k in vote.keys():
                vote[k] += (" - "
                            + self.options[vote[k]]["display_name"]
                            + " - "
                            + self.options[vote[k]]["mention"])
            vote["voter name"] = voter.name
            vote["voter id"] = voter.id
            votes.append(vote)

        name = "voter_info.csv"
        with open(name, 'w') as csvFile:
            fields = ["voter name", "voter id"]
            fields.extend(
                [str(x) for x in range(1, len(self.options) + 1)])
            logging.info(fields)
            writer = csv.DictWriter(csvFile, fieldnames=fields)
            writer.writeheader()
            writer.writerows(votes)
        csvFile.close()
        return name
