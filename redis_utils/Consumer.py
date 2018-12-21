import pika
from pika.adapters.blocking_connection import BlockingChannel
import time


class Consumer:
    def __init__(self, mq_host="localhost"):
        self.mq_host = mq_host

    @staticmethod
    def callback(ch: BlockingChannel, method, properties, body):
        print("received", body)
        time.sleep(10)
        print('done')
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def run(self):
        conn = pika.BlockingConnection(pika.ConnectionParameters(self.mq_host))
        channel: BlockingChannel = conn.channel()

        channel.queue_declare("task_queue", durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(self.callback,
                              queue="task_queue")
        channel.start_consuming()


if __name__ == "__main__":
    Consumer().run()
