import datetime
import random
import string
from enum import Enum

from redis_utils.ServerMessage import MessageType


class TimerEvent(Enum):
    START = 0,
    PAUSE = 1,
    UNPAUSE = 2,
    STOP = 3,
    RESTART = 4


class TimerMessage:
    def __init__(self, timer_id: str, name: str, time: int, event: TimerEvent):
        self.timer_id = timer_id
        self.name = name
        self.time = time
        self.event = event

    def to_str(self, em_id) -> str:
        """
        EMULATOR TIMER ID NAME EVENT
        :param em_id:
        :return:
        """
        return em_id + "\t" + '\t'.join([MessageType.TIMER.name,
                                         self.timer_id,
                                         self.name,
                                         str(self.time),
                                         self.event.name])


class Timer:
    def __init__(self, seconds, name, parent):
        """

        :param seconds:
        :param name:
        :param parent:
        """
        self.id = self.gen_id()
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
            # cm: Manager = self.parent.cm
            # cm.on_timer_elapsed(self.parent)
            self.parent.on_timer_elapsed(self.id)

    def stop(self):
        if self.elapsed:
            return
        self.elapsed = True

    def pause(self):
        assert self.active
        self.paused = True
        self.left = datetime.timedelta(seconds=self.timedelta) - (datetime.datetime.now() - self.time_started)

    def unpause(self):
        assert self.paused
        self.time_elapsed = datetime.datetime.now() + self.left
        self.paused = False

    def time_left(self):
        if not self.elapsed and self.active:
            return self.time_elapsed - datetime.datetime.now()

    def restart(self):
        self.__init__(self.timedelta, self.name, self.parent)
        self.start()

    @staticmethod
    def gen_id():
        return 'T' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
