class FFRVoter:
    """
    This is a class representing a voter in an election

    :param id: This voter's discord id
    :type id: str
    :param name: This voter's discord name
    :type name: str
    """

    def __init__(self, id: str, name: str):
        """
        Constructor method
        """
        self.id = id
        self.name = name
        self.vote = ""

    def __str__(self):
        return self.id + " " + self.name + " " + str(self.vote)

    def __repr__(self):
        return self.id + " " + self.name + " " + str(self.vote)

    def get_vote(self):
        """
        Returns a list of who/what this user has voted for

        :return: A list of strings representing what this user voted for
        :rtype: list
        """
        # return self.vote
        ballot = dict()
        for key, value in self.vote.items():
            ballot[str(int(key))] = value
        return ballot

    def set_vote(self, vote):
        """
        Sets this user's vote

        :param vote: the vote this user cast
        :type vote: list or str
        """
        self.vote = vote
