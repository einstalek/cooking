import time
from threading import Thread
from typing import List

from ContextUnit import ContextUnit, UnitType
from IntentParser import Intent, IntentParser
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
        self.context_manager = cm
        self._stack: List[ContextUnit] = []
        self.parser = IntentParser()

    def extract_intent(self, response):
        """
        Извлекает из пришедшего сообщения интент и уведомляет об этом CM
        :param response:
        :return:
        """
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
                verbs = self.extract_verbs_from_phrase(self._stack[-1].phrase)
                if any(verb in x for x in verbs):
                    self.context_manager.handle_intent(Intent.NEXT_SIMPLE)

        if intent is not None:
            self.context_manager.handle_intent(intent)
        time.sleep(0.5)

    def push(self, unit: ContextUnit):
        self._stack.append(unit)

        if unit.type == UnitType.CONFIRMATION:
            for u in self._stack[:-1]:
                if not u.solved:
                    u.solved = True

    def run(self):
        conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
        channel: BlockingChannel = conn.channel()

        channel.queue_declare("task_queue", durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(self.callback,
                              queue="task_queue")
        channel.start_consuming()
        # t = Thread(target=self.read_from_stdin)
        # t.start()

    def callback(self, ch: BlockingChannel, method, properties, body: bytes):
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print("GOT MESSAGE:", body.decode())
        self.extract_intent(body.decode())

    def fill_choice_unit(self, response):
        try:
            top_unit = self._stack[-1]
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
