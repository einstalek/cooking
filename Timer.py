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
        self.timedelta = seconds
        self.time_started = None
        self.time_elapsed = None
        self.elapsed = False
        self.active = False
        self.name = name
        self.parent = parent
        self.paused = False
        self.passed = None

    def start(self) -> None:
        self.time_started = datetime.datetime.now()
        self.time_elapsed = self.time_started + datetime.timedelta(seconds=self.timedelta)
        self.active = True
        if self.name:
            print('Timer "' + self.name + '" started')

    def time_left(self) -> Optional[datetime.datetime]:
        if self.active:
            return self.time_elapsed - datetime.datetime.now()
        return None

    def update(self) -> None:
        """
        Обновляет статус таймера
        Если статус изменился, уведомляет об этом DM
        :return:
        """
        if self.active and not self.elapsed and not self.paused and datetime.datetime.now() > self.time_elapsed:
            # print("Timer", self.parent, "elapsed")
            dm: Manager = self.parent.dm
            dm.on_timer_elapsed(self.parent)
            self.elapsed = True

    def stop(self):
        self.elapsed = True

    def pause(self):
        self.paused = True
        self.passed = datetime.datetime.now() - self.time_started

    def restart(self):
        self.time_elapsed = datetime.datetime.now() + self.passed
        self.paused = False


if __name__ == "__main__":
    timer = Timer(3, "check", None)
    timer.start()
    while not timer.elapsed:
        timer.update()

