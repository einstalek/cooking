import socket
from threading import Thread
from typing import Dict

import pika
from pika.adapters.blocking_connection import BlockingChannel

from Timer import TimerEvent
from redis_utils.ServerMessage import ServerMessage, MessageType


class WebServer:
    def __init__(self, mq_host="localhost", port=8888):
        self.mq_host = mq_host
        self.port = port
        self.emulators: Dict[str, socket.socket] = {}
        self.finished = set()

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(("localhost", port))
        self.server.listen(10)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.t = Thread(target=self.run)
        self.t.start()
        Thread(target=self.consume_timer_commands).start()
        Thread(target=self.consume_responses).start()

    def run(self):
        """
        Ожидает сообщения от эмуляторов
        :return:
        """
        while True:
            client_sock, addr = self.server.accept()
            while True:
                data = client_sock.recv(1024)
                if not data:
                    break
                else:
                    mssg = ServerMessage.from_bytes(data)
                    self.handle_incoming_mssg(mssg, client_sock)

    def handle_incoming_mssg(self, mssg: ServerMessage, client_sock: socket.socket):
        """
        Кладет сообщения от эмулятора из сокета  в MQ
        :param mssg:
        :param client_sock:
        :return:
        """
        em_id = mssg.em_id

        if em_id in self.finished:
            return

        if em_id not in self.emulators and mssg.mssg_type == MessageType.REGISTER:
            print("registered", em_id)
            self.emulators[em_id] = client_sock
            try:
                self.socket.connect(("localhost", 9999))
                self.socket.send(em_id.encode('utf-8'))
                self.socket.close()
            except OSError:
                print("error occurred")

        # Текстовый запрос от клиента отправляем в MQ
        if mssg.mssg_type == MessageType.REQUEST:
            print("request from", em_id, mssg.request[0][0])
            conn = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
            channel: BlockingChannel = conn.channel()
            channel.queue_declare(queue='task_queue', durable=True)
            channel.basic_publish(exchange='',
                                  routing_key='task_queue',
                                  # body=mssg.request[0][0],
                                  body='\t'.join([mssg.em_id, MessageType.REQUEST.name, mssg.request[0][0]]),
                                  properties=pika.BasicProperties(
                                      delivery_mode=2
                                  ))
            conn.close()

        # Вышло время у таймера
        if mssg.mssg_type == MessageType.TIMER:
            print("timer event from he", mssg.request[0][0])
            conn = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
            channel: BlockingChannel = conn.channel()
            channel.queue_declare(queue='timer_event', durable=True)
            channel.basic_publish(exchange='',
                                  routing_key='timer_event',
                                  # TODO: implement this
                                  body='\t'.join([mssg.em_id, MessageType.TIMER.name, mssg.request[0][0]]),
                                  properties=pika.BasicProperties(
                                      delivery_mode=2
                                  ))
            conn.close()

    def consume_timer_commands(self):
        """
        Забирает команду от таймере из MQ и отправляет ее на эмулятор
        :return:
        """
        conn = pika.BlockingConnection(pika.ConnectionParameters(self.mq_host))
        channel: BlockingChannel = conn.channel()

        channel.queue_declare("timer_command", durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(self.timer_command_callback,
                              queue="timer_command")
        channel.start_consuming()

    def consume_responses(self):
        conn = pika.BlockingConnection(pika.ConnectionParameters(self.mq_host))
        channel: BlockingChannel = conn.channel()

        channel.queue_declare("response_queue", durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(self.response_callback,
                              queue="response_queue")
        channel.start_consuming()

    def timer_command_callback(self, ch: BlockingChannel, method, properties, body: bytes):
        """
        Отправляет команду от таймере на эмулятор
        :param ch:
        :param method:
        :param properties:
        :param body:
        :return:
        """
        print("timer command from mq", body.decode())
        mssg = ServerMessage.from_bytes(body)
        request = mssg.request[0]

        em_id = mssg.em_id
        timer_id, timer_name, timer_secs, timer_event = request
        timer_event = TimerEvent[timer_event]
        timer_secs = int(timer_secs)

        if em_id not in self.emulators:
            print("Нет эмулятора с ID", em_id)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        mssg = ServerMessage.gen_mssg(em_id, MessageType.TIMER, timer_id, timer_name, timer_secs, timer_event.name)
        self.emulators[em_id].send(mssg)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def response_callback(self, ch: BlockingChannel, method, properties, body: bytes):
        mssg = ServerMessage.from_bytes(body)
        print("response for", mssg.em_id)
        if mssg.em_id not in self.emulators:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        if mssg.mssg_type == MessageType.RESPONSE:
            self.emulators[mssg.em_id].send('\t'.join([mssg.em_id, MessageType.RESPONSE.name,
                                                       mssg.request[0][0]]).encode('utf-8'))
        elif mssg.mssg_type == MessageType.FINISH:
            self.emulators[mssg.em_id].send('\t'.join([mssg.em_id, MessageType.FINISH.name]).encode('utf-8'))
            self.finished.add(mssg.em_id)

        ch.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == "__main__":
    server = WebServer(port=8889)
