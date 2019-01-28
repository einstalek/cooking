import random
import string
from threading import Thread
import socket

from custom_exceptions import RegistrationRefusedError
from server_message import ServerMessage, MessageType


class HardwareEmulator:
    def __init__(self, host="localhost", port=8888):
        self.host = host
        self.port = port
        self.id = 'HE' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        self.server = None
        self.id = self.gen_id()
        self.finished = False
        self.selected = True

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def run(self):
        """
        Запуск потока со считыванием ответов сообщений из сокета
        :return:
        """
        self.socket_read_thread = Thread(target=self.read_from_socket)
        self.socket_read_thread.start()
        self.stdin_thread = Thread(target=self.read_from_input)
        self.stdin_thread.start()

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
    connected = emulator.register()
    if connected:
        Thread(target=emulator.run).start()
