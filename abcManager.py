import random
import string
from abc import ABC

from redis_utils.WebServer import WebServer


class Manager(ABC):
    def __init__(self):
        self.em_id: str = None
        self.finished = False
        self.id = 'CM' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        self.server: WebServer = None

    def on_timer_elapsed(self, action: object):
        pass

    def handle_intent(self, intent, params=None):
        pass

    def current_state(self):
        pass

    def on_action_spoken(self, phrase):
        pass

    def on_outcoming_timer_event(self, mssg: str):
        pass
