from voting.ffrvoter import FFRVoter
import logging


class Poll:
    def __init__(self, poll_id, channel_id):
        self.options = dict()
        self.poll_id = poll_id
        self.voters = dict()
        self.started = False
        self.ended = False
        self.channel_id = channel_id
        self.type = "poll"
        self.add_option_arg_len = 2

    def __str__(self):
        r_val = self.poll_id
        r_val += str(self.options)
        r_val += str(self.voters)
        r_val += str(self.channel_id)
        return r_val

    def __eq__(self, other):
        return (self.options == other.options
                and self.poll_id == other.poll_id
                and self.voters == other.voters
                and self.started == other.started
                and self.ended == other.ended
                and self.channel_id == other.channel_id)

    def get_channel(self):
        return self.channel_id

    def get_count(self):
        return len(self.voters)

    def add_option(self, ctx: any, args: list):
        id = args[0]
        description = args[1]
        if (id in self.options):
            raise KeyError("That id already exists")
        else:
            self.options[id] = {"id": id,
                                "description": description,
                                "voters": [],
                                "index": len(self.options)}

    def list_options(self, name_only=False):
        r_val = ""
        count = 0
        for option in self.options.values():
            count += 1
            r_val += str(count) + ": "
            r_val += option["id"]\
                + ("" if name_only else " - " + option[
                    "description"]) + "\n\n"
        return r_val

    def start_poll(self):
        """
        sets the poll started flag
        """
        self.started = True

    def end_poll(self):
        """
        sets the poll ended flag
        """
        self.ended = True

    def undo_end_poll(self):
        self.ended = False

    def check_if_voted(self, voter_id: str):
        return voter_id in [x for x in self.voters.keys()]

    def submit_vote(self, voter_id: str, voter_name: str, args: list):
        """
        Adds a vote for the voter with the id given for the votee id given

        :param voter_id: The id for the discord user voting
        :type voter_id: str
        :param voter_name: The name for the discord user voting
        :type voter_name: str
        :param option_id: the id for the option being voted for
        :type option_id: str
        """
        if self.started is False:
            raise VoteNotOpen

        if self.ended is True:
            raise VoteAlreadyClosed

        if self.check_if_voted(voter_id):
            raise AlreadyVoted

        else:
            voter = FFRVoter(voter_id, voter_name)
            try:
                self.voters[str(voter_id)] = voter
                option_id = self.get_option_id_by_index(
                    int(args[0].strip("<>")) - 1)
                voter.set_vote(option_id)
                self.options[option_id]["voters"].append(voter)
            except KeyError:
                logging.error("KeyError in submit_vote")
                pass

    def remove_voter(self, id):
        if self.check_if_voted(id):
            del self.voters[id]
            return True
        else:
            return False

    def update_description(self, id: str, description: str):
        try:
            self.options[id]["description"] = description
        except KeyError:
            raise KeyError("That id doesn't exist")

    def get_winner(self):
        sorted_options = [value for value in
                          sorted(self.options.values(),
                                 key=lambda val: len(val["voters"]),
                                 reverse=True)]
        if (len(sorted_options[0]["voters"]) !=
                len(sorted_options[1]["voters"])):
            return sorted_options[0]
        else:
            return False

    def get_results(self):
        winner = self.get_winner()
        if winner is False:
            r_val = "Its a Tie!\n"
        else:
            r_val = "The winner is: " + self.get_winner()["id"] + "\n"
        for value in sorted(self.options.values(),
                            key=lambda val: len(val["voters"]),
                            reverse=True):
            r_val += "\n" + value["id"] + ": "\
                     + str(
                round(100 * len(value["voters"]) / len(self.voters)))\
                + "%   " + str(len(value["voters"])) + " votes"

        r_val += "\n\nTotal votes: " + str(len(self.voters))
        return r_val

    def get_vote_text(self):
        return ("To vote in this poll, find the option number you want, then "
                + "copy and paste the following, with the <x> replaced with"
                + " that number:")

    def get_submitballot_template(self):
        r_val = "\n`?submitballot " + str(self.channel_id) + " <x>`\n\n"
        r_val += self.list_options()
        return r_val

    def get_option_id_by_index(self, index: int):
        """
        returns the id associated with an option's index

        :param index: index of that option
        :type index: int
        :return: id of the option, or None if that index doesnt exist
        :rtype: string or None
        """
        logging.debug(self.options.values())
        logging.debug(len(self.options.values()))
        try:
            id = [k for k, v in self.options.items()
                  if v["index"] == index][0]
        except IndexError:
            id = None

        return id

    def check_valid_ballot(self, ballot_args: list):
        logging.debug(ballot_args[0])
        try:
            index = int(ballot_args[0].strip("<>")) - 1
        except ValueError:
            return False
        if index is None:
            return False
        option_id = self.get_option_id_by_index(index)
        logging.debug(option_id)
        if option_id is None:
            return False
        return True

    def confirm_vote_text(self, ballot_args: list):
        return "option number: " + str(ballot_args[0])

    def get_csv(self):
        return False

    def get_voter_info(self):
        return False

    def get_voter_names(self):
        voters = [voter.name for voter in self.voters.values()]
        return voters


class AlreadyVoted(Exception):
    """
    raised when that user has already voted
    """
    pass


class VoteNotOpen(Exception):
    """
    raised when this vote is not yet open
    """
    pass


class VoteAlreadyClosed(Exception):
    """
    raised when this vote is already closed
    """
    pass
