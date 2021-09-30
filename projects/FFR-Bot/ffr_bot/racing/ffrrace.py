import os
from typing import Dict, Union
from ..common.discord_user import DiscordUser

class Racer(DiscordUser):
    """
    a class for a discord user racing
    """
    def __init__(self, id: str, name: str, display_name: str):
        super().__init__(id, name, display_name)

class Race:
    """
    A class to model a FFR race
    """
    def __init__(self, id: str, name: str, owner: str, flags: str = None):
        self.id: str = id
        self.name: Union[str, None] = name
        self.flags: Union[str, None] = flags
        self.runners: Dict[str, DiscordUser] = dict()
        self.started: bool = False
        self.ended: bool = False
        self.role = None
        self.channel = None
        self.owner = None

    def savedata(self):
        raise NotImplementedError

    def add_runner(self, runner: DiscordUser):
        self.runners[runner.id] = runner

    def remove_runner(self, runner: DiscordUser):
        del self.runners[runner.id]

    def start(self):
        self.started = True

    def forfeit_runner(self, runner: DiscordUser):
        raise NotImplementedError


    def end_race(self):
        if (self.started):
            self.ended = True
        else:
            raise RaceNotStarted

class RaceNotStarted(Exception):
    """
    raised when the race has not started yet but was expected to have.
    """
    pass
