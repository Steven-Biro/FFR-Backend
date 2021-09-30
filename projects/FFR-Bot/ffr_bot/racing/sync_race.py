from racing.ffrrace import Race

import time
from datetime import timedelta
from sys import maxsize
import redis
import os

redis_db = redis.Redis(host=os.environ.get("REDIS_HOST", "localhost"),
                       port=int(os.environ.get("REDIS_PORT", "6379")))


class SyncRace(Race):
    """
    A class to model a synchronous FFR race
    """

    def __init__(self, id, name=None, flags=None):
        self.id = id
        self.name = name
        self.flags = flags
        self.runners = dict()
        self.started = False
        self.role = None
        self.channel = None
        self.owner = None
        self.readycount = 0
        self.message = None
        self.restream = None

    def addRunner(self, runnerid, runner):
        self.runners[runnerid] = dict(
            [("name", runner), ("stime", None), ("etime", None),
             ("ready", False)])

    def removeRunner(self, runnerid):
        del self.runners[runnerid]

    def ready(self, runnerid):
        if (self.runners[runnerid]["ready"]):
            return
        self.runners[runnerid]["ready"] = True
        self.readycount += 1

    def unready(self, runnerid):
        if (self.runners[runnerid]["ready"] is False):
            return
        self.runners[runnerid]["ready"] = False
        self.readycount -= 1

    def start(self):
        self.started = True
        stime = time.perf_counter_ns()
        for runnerid in self.runners.values():
            runnerid["stime"] = stime

    def done(self, runnerid):
        etime = time.perf_counter_ns()
        self.runners[runnerid]["etime"] = etime

        if (all(r["etime"] is not None for r in self.runners.values())):
            return self.finishRace()

        rval = timedelta(microseconds=round(
            etime - self.runners[runnerid]["stime"], -3) // 1000)
        return self.runners[runnerid]["name"] + ": " + str(rval)

    def undone(self, runnerid):
        self.runners[runnerid]["etime"] = None
        return self.runners[runnerid]["name"] + " is back in the race!"

    def forfeit(self, runnerid):
        self.runners[runnerid]["etime"] = maxsize
        if (all(r["etime"] is not None for r in self.runners.values())):
            return self.finishRace()

        return self.runners[runnerid]["name"] + " forfeited"

    def getUpdate(self):
        rval = "Current Entrants:\n"
        for runner in self.runners.values():
            rval += runner["name"] + " "
            if (self.started):
                if (runner["etime"] is maxsize):
                    rval += "forfeited"
                elif (runner["etime"] is not None):
                    time = timedelta(microseconds=round(
                        runner["etime"] - runner["stime"], -3) // 1000)
                    rval += "done: " + str(time)
                else:
                    rval += "still going"
            else:
                rval += ("ready" if runner["ready"] else "not ready")
            rval += "\n"
        return rval

    def getTime(self):
        for i in self.runners.values():
            return timedelta(microseconds=round(
                time.perf_counter_ns() - i["stime"], -3) // 1000)

    def finishRace(self):
        rstring = "Race " + self.name + " results:\n\n"
        place = 0
        for runner in sorted(list(self.runners.values()),
                             key=lambda k: k["etime"]):
            place += 1
            rstring += str(place) + ") " + runner["name"] + ": "
            if (runner["etime"] is maxsize):
                rstring += "Forfeited\n"
            else:
                rstring += str(timedelta(microseconds=round(
                    runner["etime"] - runner["stime"], -3) // 1000)) + "\n"
        return rstring
