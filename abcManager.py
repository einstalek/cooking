from abc import ABC


class Manager(ABC):
    def __init__(self):
        self.finished = False

    def on_timer_elapsed(self, action: object):
        pass

    def handle_intent(self, intent, params=None):
        pass

    def current_state(self):
        pass

    def on_action_spoken(self, phrase):
        pass
