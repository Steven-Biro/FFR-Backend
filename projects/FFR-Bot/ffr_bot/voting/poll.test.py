import unittest
from voting.poll import Poll


class TestPoll(unittest.TestCase):

    def test_instantiation(self):
        poll = Poll("test", "fake id")
        self.assertEqual(str(poll), r"test{}{}fake id")

    def test_add_option(self):
        poll = Poll("test", "fake id")
        poll.add_option(None, ["option #1", "This is the first option"])
        self.assertEqual(str(poll),
                         r"test{'option #1': {'id': 'option #1', 'description'"
                         r": 'This is the first option', 'voters': [], 'index'"
                         r": 0}}{}fake id")

    def test_submit_vote(self):
        poll = Poll("test", "fake id")
        poll.add_option(None, ["option #1", "This is the first option"])
        poll.add_option(None, ["option #2", "This is the second option"])
        poll.start_poll()
        poll.submit_vote("test pollr id", "test name", ["1"])
        self.assertEqual(str(poll.voters), r"{'test pollr id': test pollr id "
                                           r"test name option #1}")

    def test_update_description(self):
        poll = Poll("test", "fake id")
        poll.add_option(None, ["option #1", "This is the first option"])
        poll.add_option(None, ["option #2", "This is the second option"])
        poll.update_description(
            "option #1", "updated first option description")
        self.assertEqual(str(poll.options),
                         r"{'option #1': {'id': 'option #1', 'description': "
                         r"'updated first option description', 'voters': [], "
                         r"'index': 0},"
                         r" 'option #2': {'id': 'option #2', 'description': "
                         r"'This is the second option', 'voters': [], "
                         r"'index': 1}}")

    def test_get_winner(self):
        poll = Poll("test", "fake id")
        poll.add_option(None, ["option #1", "This is the first option"])
        poll.add_option(None, ["option #2", "This is the second option"])
        poll.start_poll()
        for i in range(100):
            choice = i % 3 != 0
            option = "1" if choice else "2"
            poll.submit_vote(str(i), str(i) + " name", [option])
        self.assertEqual(poll.get_winner()["id"], "option #1")

        poll2 = Poll("test", "fake id")
        poll2.add_option(None, ["option #1", "This is the first option"])
        poll2.add_option(None, ["option #2", "This is the second option"])
        poll2.start_poll()
        for i in range(100):
            choice = i % 2 != 0
            option = "1" if choice else "2"
            poll2.submit_vote(str(i), str(i) + " name", [option])
        self.assertFalse(poll2.get_winner())

    def test_get_results(self):
        poll = Poll("test", "fake id")
        poll.add_option(None, ["option #1", "This is the first option"])
        poll.add_option(None, ["option #2", "This is the second option"])
        poll.start_poll()
        for i in range(1333):
            choice = i % 3 != 0
            option = "1" if choice else "2"
            poll.submit_vote(str(i), str(i) + " name", [option])
        self.assertEqual(poll.get_results(), """The winner is: option #1

option #1: 67%   888 votes
option #2: 33%   445 votes

Total votes: 1333""")

        poll2 = Poll("test", "fake id")
        poll2.add_option(None, ["option #1", "This is the first option"])
        poll2.add_option(None, ["option #2", "This is the second option"])
        poll2.start_poll()
        for i in range(100):
            choice = i % 2 != 0
            option = "1" if choice else "2"
            poll2.submit_vote(str(i), str(i) + " name", [option])
        self.assertEqual(poll2.get_results(), """Its a Tie!

option #1: 50%   50 votes
option #2: 50%   50 votes

Total votes: 100""")


TestPoll().test_instantiation()
if __name__ == "__main__":
    unittest.main()
