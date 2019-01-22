import datetime
import socket
from threading import Thread
from typing import Dict

import pika
from pika.adapters.blocking_connection import BlockingChannel

from managers.context_manager import ContextManager
from recipes.recipe_manager import RecipeManager
from redis_utils.restorer import Restorer
from base_structures.tree import Tree
from recipes import eggs_tmin, cutlets_puree
from servers.server_message import ServerMessage


class Server:
    def __init__(self, host="localhost", port=9999):
        self.host = host
        self.port = port

        self.restorer = Restorer()
        self.emulators: Dict[str, str] = {}

        # сокет для связи в WebServer
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen(10)

        self.recipe_manager = RecipeManager(
            cutlets_puree,
            eggs_tmin,
        )

    def initialize(self):
        Thread(target=self.run_server).start()
        Thread(target=self.start_consuming_timer_events).start()
        Thread(target=self.start_consuming_requests).start()
        self.log("Initialized")

    def run_server(self):
        while True:
            client_sock, addr = self.server.accept()
            while True:
                data = client_sock.recv(1024)
                if not data:
                    break
                else:
                    # Для нового эмулятора сохраняем начальный CM и DM в Redis
                    final = eggs_tmin.final
                    tree = Tree(final, switch_proba=0.01)
                    tree.assign_queue_names(["омлет", "тмин"])

                    # final = cutlets_puree.final
                    # tree = Tree(final, switch_proba=0.001)
                    # tree.assign_queue_names(["котлеты", "пюре", "соус"])

                    em_id = data.decode('utf-8')
                    cm = ContextManager(tree, em_id=em_id, n_iterations=100)
                    self.log("created session for " + em_id)
                    cm.initialize()
                    self.emulators[em_id] = cm.dialog_manager.id
                    cm.dialog_manager.save_to_db()
                    cm.save_to_db()
                    break

    def select_recipe(self):
        # TODO: implement
        available_recipes = ", ".join([recipe.final.name for recipe in self.recipe_manager.recipes])


    def start_consuming_timer_events(self):
        """
        Забираем из MQ события истечения времен у таймеров на эмуляторе
        :return:
        """
        conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
        channel: BlockingChannel = conn.channel()

        channel.queue_declare("timer_event", durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(self.on_incoming_timer_event_callback,
                              queue="timer_event")
        channel.start_consuming()

    def start_consuming_requests(self):
        conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
        self.channel: BlockingChannel = conn.channel()

        self.channel.queue_declare("task_queue", durable=True)
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(self.on_request_callback,
                              queue="task_queue")
        self.channel.start_consuming()

    def on_incoming_timer_event_callback(self, ch: BlockingChannel, method, properties, body: bytes):
        """
        Что происходит, когда пришло событие об истечении времени таймера на эмуляторе
        :param ch:
        :param method:
        :param properties:
        :param body:
        :return:
        """
        mssg = ServerMessage.from_bytes(body)
        if mssg.em_id not in self.emulators:
            self.log("no session for " + mssg.em_id)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        dm_id = self.emulators[mssg.em_id]
        dialog_manager = self.restorer.restore_dialog_manager(dm_id)
        context_manager = dialog_manager.context_manager

        context_manager.on_incoming_timer_event_callback(mssg)

        dialog_manager.save_to_db()
        dialog_manager.context_manager.save_to_db()
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def on_request_callback(self, ch: BlockingChannel, method, properties, body: bytes):
        """
        Что происходит, когда от эмулятора пришел запрос
        :param ch:
        :param method:
        :param properties:
        :param body:
        :return:
        """
        mssg = ServerMessage.from_bytes(body)
        if mssg.em_id not in self.emulators:
            self.log("no session for " + mssg.em_id)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        dm_id = self.emulators[mssg.em_id]
        dialog_manager = self.restorer.restore_dialog_manager(dm_id)

        dialog_manager.on_request_callback(mssg.request[0][0])

        dialog_manager.save_to_db()
        dialog_manager.context_manager.save_to_db()
        ch.basic_ack(delivery_tag=method.delivery_tag)

    @staticmethod
    def log(*args):
        print(datetime.datetime.now(), ":", *args)


if __name__ == '__main__':
    Server().initialize()



