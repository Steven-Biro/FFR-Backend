import unittest
from voting.stv_election import StvElection


class TestStvElection(unittest.TestCase):

    def test_instantiation(self):
        election = StvElection("test", "fake id", 5)
        self.assertEqual(str(election), r"test{}{}fake id")

    def test_submit_vote(self):
        election = StvElection("test", "fake id", 5)
        election.options["123"] = {"id": "123",
                                   "mention": "asdf",
                                   "display_name": "display_name",
                                   "index": len(election.options)}
        election.start_poll()
        election.submit_vote("321", "test name", ["1,,123"])
        self.assertEqual(str(election.voters),
                         r"{'321': 321 test name {'1': '123'}}")

    def test_get_winners(self):
        election = StvElection("test", "fake id", 5)
        for i in range(20):
            x = str(i)
            election.options[x] = {"id": x,
                                   "mention": x + "asdf",
                                   "display_name": x + "display_name",
                                   "index": len(election.options)}
        election.start_poll()
        for i in range(500):
            choice = i % 5
            x = str(i)
            election.submit_vote(x + "voterid",
                                 x + "votername",
                                 [str(1) + ",," + str(choice)])
        self.assertTrue(election.get_winners()["winners"] ==
                        set(["0", "1", "2", "3", "4"]))


TestStvElection().test_instantiation()
if __name__ == "__main__":
    unittest.main()
