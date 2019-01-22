import random
import string
from abc import ABC

from servers.web_server import WebServer


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

    def publish_timer_command(self, mssg: str):
        pass

    def publish_response(self, mssg: str):
        pass

    def save_to_db(self):
        pass