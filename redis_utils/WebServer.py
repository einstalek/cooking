import pika
from pika.adapters.blocking_connection import BlockingChannel


class WebServer:
    def __init__(self, mq_host="localhost"):
        self.mq_host = mq_host

    def on_message(self, request):
        conn = pika.BlockingConnection(pika.ConnectionParameters(self.mq_host))
        channel: BlockingChannel = conn.channel()

        channel.queue_declare(queue="task_queue", durable=True)
        channel.basic_publish(exchange="",
                              routing_key="task_queue",
                              properties=pika.BasicProperties(
                                  delivery_mode=2),
                              body=request)
        conn.close()
