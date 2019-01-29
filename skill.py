from threading import Thread
from typing import Dict, List, Set

import pika
from pika.adapters.blocking_connection import BlockingChannel

from server_message import MessageType, ServerMessage
from skillsdk.model.voice_channel_message import VoiceChanelMessage
from skillsdk.sdk import AppClient

skill_client: AppClient = AppClient('cooking', 'key', API_HOST='ec2-63-33-202-35.eu-west-1.compute.amazonaws.com')
finished: Set = set()
clients: Dict[str, List[str]] = {}
code = None


def handler(message: VoiceChanelMessage):
    print("got message", message.message_text)
    global code
    if code is None:
        code = message.receiver_code

    if message.sender_code in finished:
        return

    client_id = message.sender_code
    device_id = message.device_id
    dialog_id = message.dialog_id

    if client_id not in clients:
        clients[client_id] = [device_id, dialog_id]
        body = '\t'.join([client_id, MessageType.REGISTER.name, message.message_text])

        conn = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel: BlockingChannel = conn.channel()
        channel.queue_declare(queue='init_queue', durable=True)
        channel.basic_publish(exchange='',
                              routing_key='init_queue',
                              body=body,
                              properties=pika.BasicProperties(
                                  delivery_mode=1))
        conn.close()
    else:
        body = '\t'.join([client_id, MessageType.REQUEST.name, message.message_text])
        conn = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel: BlockingChannel = conn.channel()
        channel.queue_declare(queue='task_queue', durable=True)
        channel.basic_publish(exchange='',
                              routing_key='task_queue',
                              body=body,
                              properties=pika.BasicProperties(
                                  delivery_mode=1))
        conn.close()


def response_callback(ch: BlockingChannel, method, properties, body: bytes):
    """
    :param ch:
    :param method:
    :param properties:
    :param body:
    :return:
    """
    global finished, code

    response = ServerMessage.from_bytes(body)
    client_id = response.em_id
    if client_id not in clients:
        return

    to_client_message = VoiceChanelMessage()
    to_client_message.sender_code = code
    to_client_message.receiver_code = client_id
    to_client_message.device_id, to_client_message.dialog_id = clients[client_id]
    to_client_message.message_text = response.request[0][0]
    skill_client.send_message_to_client(to_client_message)

    if response.mssg_type == MessageType.FINISH:
        finished.add(client_id)
    ch.basic_ack(delivery_tag=method.delivery_tag)


def start_consuming():
    conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel: BlockingChannel = conn.channel()
    channel.queue_declare("response_queue", durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(response_callback, queue="response_queue")
    channel.start_consuming()


Thread(target=start_consuming).start()
skill_client.set_new_message_handler(handler)
skill_client.start_skill()






