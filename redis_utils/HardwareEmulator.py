import random
import string
from threading import Thread
from typing import Dict

from Timer import Timer
from redis_utils.WebServer import WebServer


class HardwareEmulator:
    def __init__(self, host="localhost", port=8888):
        self.id = 'HE' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        self.host = host
        self.port = port
        self.server = WebServer()
        self.timers: Dict[str, Timer] = {}

        # self.ticker = Thread(target=self.update)
        # self.ticker.start()

    def send(self, request):
        self.server.on_request(request)

    def run(self):
        while True:
            request = input()
            if request:
                self.send(request)

    def update(self):
        while True:
            for timer_id in self.timers:
                self.timers[timer_id].update()

    def add_timer(self, timer: Timer):
        self.timers[timer.id] = timer


if __name__ == "__main__":
    HardwareEmulator().run()

