import datetime
import socket
import time
from threading import Thread
from typing import Dict

import pika
from pika.adapters.blocking_connection import BlockingChannel

import custom_exceptions
from pika import exceptions as pika_exceptions

from base_structures.timer import Timer, TimerEvent, TimerMessage
from managers.context_manager import ContextManager
from recipes.recipe_manager import RecipeManager
from redis_utils.restorer import Restorer
from recipes import eggs_tmin, cutlets_puree
from servers.server_message import ServerMessage, MessageType


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

        self.timers: Dict[str, Dict[str, Timer]] = {}

    def initialize(self):
        Thread(target=self.run_server).start()
        # Thread(target=self.start_consuming_timer_events).start()
        Thread(target=self.start_consuming_requests).start()
        Thread(target=self.update).start()
        self.log("Initialized")

    def run_server(self):
        while True:
            client_sock, addr = self.server.accept()
            while True:
                data = client_sock.recv(1024)
                if not data:
                    break
                else:
                    mssg = data.decode('utf-8').split('\t')

                    if len(mssg) == 1:
                        # Пришел запрос на регистрацию
                        em_id = mssg[0]
                        self.select_recipe(em_id)
                        self.log("created session for " + em_id)

                    elif len(mssg) == 2:
                        # Пришло название выбранного рецепта
                        em_id, recipe_name = mssg
                        recipe = [recipe for recipe in self.recipe_manager.recipes
                                  if recipe.final.name == recipe_name][0]
                        tree = self.recipe_manager.activate(recipe)

                        cm = ContextManager(tree, em_id=em_id, n_iterations=100)
                        cm.server = self
                        self.timers[em_id] = {}
                        cm.initialize()
                        self.emulators[em_id] = cm.dialog_manager.id
                        cm.dialog_manager.save_to_db()
                        cm.save_to_db()

                    break

    def select_recipe(self, em_id: str):
        available_recipes = ", ".join([recipe.final.name for recipe in self.recipe_manager.recipes])
        select_mssg = "Выберите один из следующих рецептов:\n" + available_recipes
        self.publish_response(em_id, select_mssg, MessageType.SELECT)

    def publish_response(self, em_id: str, mssg: str, mssg_type: MessageType):
        """
        Отправляет ответы в MQ
        :param em_id:
        :param mssg_type:
        :param mssg:
        :return:
        """
        try:
            conn = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        except pika_exceptions.ConnectionClosed:
            raise custom_exceptions.MqConnectionError
        channel: BlockingChannel = conn.channel()
        channel.queue_declare(queue='response_queue', durable=True)
        channel.basic_publish(exchange='',
                              routing_key='response_queue',
                              body='\t'.join([em_id, mssg_type.name, mssg]),
                              properties=pika.BasicProperties(
                                  delivery_mode=1
                              ))
        conn.close()

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
        context_manager.server = self

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
        context_manager = dialog_manager.context_manager
        context_manager.server = self

        dialog_manager.on_request_callback(mssg.request[0][0])

        dialog_manager.save_to_db()
        dialog_manager.context_manager.save_to_db()
        ch.basic_ack(delivery_tag=method.delivery_tag)

    @staticmethod
    def log(*args):
        print(datetime.datetime.now(), ":", *args)

    def on_timer_command(self, em_id: str, timer_mssg: TimerMessage):
        event = timer_mssg.event
        timer_id = timer_mssg.timer_id

        if event == TimerEvent.START:
            timer = Timer(timer_mssg.time, timer_mssg.name, self)
            timer.id = timer_id
            self.timers[em_id][timer_id] = timer
            timer.start()
        else:
            assert em_id in self.timers
            assert timer_id in self.timers[em_id]

            if event == TimerEvent.PAUSE:
                self.timers[em_id][timer_id].pause()
            elif event == TimerEvent.UNPAUSE:
                self.timers[em_id][timer_id].unpause()
            elif event == TimerEvent.RESTART:
                self.timers[em_id][timer_id].restart()
            elif event == TimerEvent.STOP:
                self.timers[em_id][timer_id].stop()

    def on_timer_elapsed(self, timer_id):
        em_id = None
        for _id in self.timers:
            if timer_id in self.timers[_id]:
                em_id = _id
        if em_id is None:
            return

        dm_id = self.emulators[em_id]
        dialog_manager = self.restorer.restore_dialog_manager(dm_id)
        context_manager = dialog_manager.context_manager
        context_manager.server = self

        context_manager.on_incoming_timer_event_callback(em_id, timer_id)
        dialog_manager.save_to_db()
        dialog_manager.context_manager.save_to_db()

    def update(self):
        """
        Обновляет таймеры
        :return:
        """
        while True:
            for em_id in self.timers:
                try:
                    for timer_id in self.timers[em_id]:
                        self.timers[em_id][timer_id].update()
                except RuntimeError:
                    continue
            time.sleep(0.5)


if __name__ == '__main__':
    Server().initialize()



