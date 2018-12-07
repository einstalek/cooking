import datetime
from typing import Optional

from abc import ABC


class Manager(ABC):
    def on_timer_elapsed(self, action: object):
        pass

    def handle_intent(self, intent):
        pass


class Timer:
    def __init__(self, seconds, name, parent):
        self.name = name
        self.timedelta = seconds
        self.time_started = None
        self.time_elapsed = None
        self.elapsed = False
        self.active = False
        self.paused = None
        self.left = None
        self.parent = parent

    def start(self) -> None:
        self.time_started = datetime.datetime.now()
        self.time_elapsed = self.time_started + datetime.timedelta(seconds=self.timedelta)
        self.active = True

    def update(self) -> None:
        """
        Обновляет статус таймера
        Если статус изменился, уведомляет об этом DM
        :return:
        """
        if self.active and not self.elapsed and not self.paused and datetime.datetime.now() > self.time_elapsed:
            self.elapsed = True
            cm: Manager = self.parent.cm
            cm.on_timer_elapsed(self.parent)

    def stop(self):
        if self.elapsed:
            return
        self.elapsed = True

    def pause(self):
        assert self.active
        self.paused = True
        self.left = datetime.timedelta(seconds=self.timedelta) - (datetime.datetime.now() - self.time_started)

    def restart(self):
        self.time_elapsed = datetime.datetime.now() + self.left
        self.paused = False


if __name__ == "__main__":
    timer = Timer(3, "check", None)
    timer.start()
    while not timer.elapsed:
        timer.update()
