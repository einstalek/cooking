import pika
from pika.adapters.blocking_connection import BlockingChannel


class WebServer:
    def __init__(self, mq_host="localhost"):
        self.mq_host = mq_host
        self.emulator_id = None

    def on_request(self, request):
        """
        Кладет в MQ команду от человека
        :param request:
        :return:
        """
        conn = pika.BlockingConnection(pika.ConnectionParameters(self.mq_host))
        channel: BlockingChannel = conn.channel()

        channel.queue_declare(queue="task_queue", durable=True)
        channel.basic_publish(exchange="",
                              routing_key="task_queue",
                              properties=pika.BasicProperties(
                                  delivery_mode=2),
                              body=request)
        conn.close()

    def on_timer_elapsed(self, timer_id):
        """
        Кладет в MQ сообщение о завершении таймера
        :param timer_id:
        :return:
        """
        conn = pika.BlockingConnection(pika.ConnectionParameters(self.mq_host))
        channel: BlockingChannel = conn.channel()

        channel.queue_declare(queue="timer_elapsed_queue", durable=True)
        channel.basic_publish(exchange="",
                              routing_key="timer_elapsed_queue",
                              properties=pika.BasicProperties(
                                  delivery_mode=2),
                              body=timer_id)
        conn.close()

    def on_create_timer(self):
        """
        Должен забирать из MQ команду для заведения таймера и передавать ее на HE
        :return:
        """
        pass

    def add_emulator(self, emulator_id):
        self.emulator_id = emulator_id
