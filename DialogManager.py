from threading import Thread
import time
from typing import List

from ContextUnit import ContextUnit, UnitType
from IntentParser import Intent, IntentParser
from abcManager import Manager


class DialogManager:
    """
    Класс, принимающий реплики человека и извлекающий из них интенты
    """

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
                node_name = self.fill_choice_unit(response)
                self.context_manager.handle_intent(Intent.CHANGE_NEXT, node_name)

            if intent is not None:
                self.context_manager.handle_intent(intent)
            time.sleep(0.5)

    def push(self, unit: ContextUnit):
        self._stack.append(unit)

    def run(self):
        t = Thread(target=self.extract_intent)
        t.start()

    def fill_choice_unit(self, response):
        if not self._stack[-1].type == UnitType.CHOICE:
            return None
        for param in self._stack[-1].params:
            if response in param:
                return param
        return None



