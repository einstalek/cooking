import random
import string
import time
from threading import Thread
from typing import List

from ContextUnit import ContextUnit, UnitType
from IntentParser import Intent, IntentParser
from RedisCursor import RedisCursor
from abcManager import Manager
from pymorphy2 import MorphAnalyzer
import re

import pika
from pika.adapters.blocking_connection import BlockingChannel


class DialogManager:
    """
    Класс, принимающий реплики человека и извлекающий из них интенты
    """
    morph = MorphAnalyzer()

    def __init__(self, cm: Manager):
        self.id = 'DM' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        self.context_manager = cm
        self.stack: List[ContextUnit] = []
        self.parser = IntentParser()
        self.finished = False

    def to_dict(self):
        conf = {
            'id': self.id,
            'context_manager': self.context_manager.id,
            'stack': ' '.join([cu.id for cu in self.stack]),
        }
        return conf

    def save_to_db(self):
        cursor = RedisCursor()
        cursor.save_to_db(self.to_dict())
        for cu in self.stack:
            cursor.save_to_db(cu.to_dict())

    def extract_intent(self, response):
        """
        Извлекает из пришедшего сообщения интент и уведомляет об этом CM
        :param response:
        :return:
        """
        if self.finished:
            return

        intent = self.parser.extract_intent(response)

        if intent is None and len(response) > 0:
            # В случае, когда последним стоит выбор следующего действия
            # и сейчас ввели название следующего действия
            node_name = self.fill_choice_unit(response)
            if node_name:
                self.context_manager.handle_intent(Intent.CHANGE_NEXT, node_name)

            # TODO: учесть частицу не перед глаголом
            # Если назван глагол в подтверждение перехода
            verb = self.fill_verb_response(response)
            if verb:
                verbs = self.extract_verbs_from_phrase(self.stack[-1].phrase)
                if any(verb in x for x in verbs):
                    self.context_manager.handle_intent(Intent.NEXT_SIMPLE)

        if intent is not None:
            self.context_manager.handle_intent(intent)

        self.save_to_db()
        self.context_manager.save_to_db()

    def push(self, unit: ContextUnit):
        self.stack.append(unit)

        if unit.type == UnitType.CONFIRMATION:
            for u in self.stack[:-1]:
                if not u.solved:
                    u.solved = True

    def run(self):
        t = Thread(target=self.read_from_mq)
        t.start()

    # Забираем запросы от эмулятора из MQ
    def read_from_mq(self):
        conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
        self.channel: BlockingChannel = conn.channel()

        self.channel.queue_declare("task_queue", durable=True)
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(self.on_request_callback,
                              queue="task_queue")
        self.channel.start_consuming()

    def on_request_callback(self, ch: BlockingChannel, method, properties, body: bytes):
        if self.finished:
            return
        self.extract_intent(body.decode())
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def fill_choice_unit(self, response):
        try:
            top_unit = self.stack[-1]
        except IndexError:
            return
        if not top_unit.type == UnitType.CHOICE:
            return None
        for param in top_unit.params:
            if response in param:
                return param
        return None

    def fill_verb_response(self, response):
        parsed = self.morph.parse(response)
        is_verb = 'VERB' in parsed[0][1]
        if is_verb:
            return parsed[0].normal_form
        return None

    def extract_verbs_from_phrase(self, phrase) -> List[str]:
        words = [w for w in re.split("\W", phrase) if len(w) > 0]
        verbs = []
        for w in words:
            parsed = self.morph.parse(w)
            if 'VERB' in parsed[0][1]:
                verbs.append(parsed[0].normal_form)
        return verbs

    def read_from_stdin(self):
        """
        Считывание команд из stdin
        :return:
        """
        while True:
            request = input()
            if request:
                self.extract_intent(request)
            time.sleep(0.5)

    def stop(self):
        self.finished = True
        self.channel.stop_consuming()
