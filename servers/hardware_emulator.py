import random
import string
import sys
import time
from threading import Thread
from typing import Dict
import socket

sys.path.insert(0, "/Users/einstalek/graph")

from base_structures.timer import Timer, TimerEvent
from custom_exceptions import RegistrationRefusedError, StartExistingTimerError
from servers.server_message import ServerMessage, MessageType


class HardwareEmulator:
    def __init__(self, host="localhost", port=8888):
        self.host = host
        self.port = port
        self.id = 'HE' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        self.server = None
        self.timers: Dict[str, Timer] = {}
        self.id = self.gen_id()
        self.finished = False
        self.selected = False

        # Запуск тикера
        self.ticker = Thread(target=self.update)
        self.ticker.start()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def run(self):
        """
        Запуск потока со считыванием ответов сообщений из сокета
        :return:
        """
        self.socket_read_thread = Thread(target=self.read_from_socket)
        self.socket_read_thread.start()

    def read_from_input(self):
        """
        Функция работает в отдельном потоке, считывая команды из stdin и отправляя их на сервер
        :return:
        """
        while not self.finished:
            request = input()
            if request:
                mssg = ServerMessage.gen_mssg(self.id, MessageType.REQUEST, request)
                self.send_on_server(mssg)

    def read_from_socket(self):
        """
        Принимает сообщения, приходящие от сервера
        :return:
        """
        while not self.finished:
            raw_mssg = self.socket.recv(1024)
            if not raw_mssg:
                break
            mssg = ServerMessage.from_bytes(raw_mssg)

            # Пришла команда о таймере
            if mssg.mssg_type == MessageType.TIMER:
                request = mssg.request[0]
                timer_id, timer_name, secs, event = request
                secs = int(secs)
                event = TimerEvent[event]
                if event == TimerEvent.START:
                    self.on_start_timer(timer_id, timer_name, secs)

                if event == TimerEvent.PAUSE:
                    self.on_pause_timer(timer_id)

                if event == TimerEvent.UNPAUSE:
                    self.on_unpause_timer(timer_id)

                if event == TimerEvent.STOP:
                    self.on_stop_timer(timer_id)

                if event == TimerEvent.RESTART:
                    self.on_restart_timer(timer_id)

            if mssg.mssg_type == MessageType.RESPONSE:
                print(mssg.request[0][0])
                print("...")

            if mssg.mssg_type == MessageType.SELECT:
                print(mssg.request[0][0])
                self.handle_recipe_selection(mssg.request[0][0])

            if mssg.mssg_type == MessageType.FINISH:
                print("Навык заввершил работу")
                self.finished = True

    def handle_recipe_selection(self, recipes):
        recipes = recipes.split("\n")[1]  # отделить предложение от списка
        n_trials = 3
        for _ in range(n_trials):
            resp = input("...\n")
            try:
                selected = [recipe for recipe in recipes.split(', ') if resp in recipe][0]
            except IndexError:
                print("Неверное название рецепта")
                continue
            self.on_recipe_chosen(selected)
            break

    def on_recipe_chosen(self, recipe: str):
        mssg = ServerMessage.gen_mssg(self.id, MessageType.SELECT, recipe)
        self.socket.send(mssg)

        self.stdin_thread = Thread(target=self.read_from_input)
        self.stdin_thread.start()

    def update(self):
        """
        Обновляет таймеры
        :return:
        """
        while True:
            for timer_id in self.timers:
                self.timers[timer_id].update()
            time.sleep(0.5)

    def on_start_timer(self, timer_id, name, secs):
        """
        Заводит таймер по команде от сервера
        :param timer_id:
        :param name:
        :param secs:
        :return:
        """
        timer = Timer(secs, name, parent=self)
        timer.id = timer_id
        if timer_id in self.timers:
            raise StartExistingTimerError

        self.timers[timer_id] = timer
        timer.start()

    def on_timer_elapsed(self, timer_id):
        """
        Отправляет на сервер события завершения таймера
        :param timer_id:
        :return:
        """
        mssg = ServerMessage.gen_mssg(self.id, MessageType.TIMER, timer_id)
        self.socket.send(mssg)

    def on_pause_timer(self, timer_id):
        self.timers[timer_id].pause()

    def on_unpause_timer(self, timer_id):
        self.timers[timer_id].unpause()

    def on_restart_timer(self, timer_id):
        self.timers[timer_id].restart()

    def on_stop_timer(self, timer_id):
        self.timers[timer_id].stop()

    def register(self) -> bool:
        try:
            self.socket.connect((self.host, self.port))
        except ConnectionRefusedError:
            raise RegistrationRefusedError

        mssg = ServerMessage.gen_mssg(self.id, MessageType.REGISTER)
        self.send_on_server(mssg)
        return True

    @staticmethod
    def gen_id():
        return 'E' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

    def send_on_server(self, mssg: bytes):
        self.socket.send(mssg)


if __name__ == '__main__':
    emulator = HardwareEmulator(host="localhost", port=8889)
    print(emulator.id)
    connected = emulator.register()
    if connected:
        Thread(target=emulator.run).start()