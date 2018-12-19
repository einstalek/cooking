from threading import Thread
import time
from typing import List

from ContextUnit import ContextUnit, UnitType
from IntentParser import Intent, IntentParser
from abcManager import Manager
from pymorphy2 import MorphAnalyzer


class DialogManager:
    """
    Класс, принимающий реплики человека и извлекающий из них интенты
    """
    morph = MorphAnalyzer()

    def __init__(self, cm: Manager):
        self.context_manager = cm
        self._stack: List[ContextUnit] = []
        self.run()
        self.parser = IntentParser()

    def extract_intent(self):
        while True:
            response = input()
            intent = self.parser.extract_intent(response)

            if intent is None and len(response) > 0:
                # В случае, когда последним стоит выбор следующего действия
                # и сейчас ввели название следующего действия
                node_name = self.fill_choice_unit(response)
                if node_name:
                    self.context_manager.handle_intent(Intent.CHANGE_NEXT, node_name)

                # TODO: сделать это и извлечение глагола из фразы действия
                # Если назван глагол в подтверждение перехода
                verb = self.fill_choice_unit(response)
                if verb:
                    print(verb)

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
        t = Thread(target=self.extract_intent)
        t.start()

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



