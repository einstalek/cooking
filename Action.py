import string
from typing import List
from Node import Node
from Timer import Timer, TimerEvent, TimerMessage
from abcManager import Manager
from ContextUnit import ContextUnit
import random
import re


class Action:
    def __init__(self, node: Node, cm: Manager):
        self.id = 'A' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        self.__node = node
        node.parent = self

        self.timer_id = Timer.gen_id()
        self.secs = node.time
        self.timer_name = node.name
        self.cm = cm
        self.paused = None
        self.elapsed = False

    def to_dict(self):
        conf = {
            'id': self.id,
            'node': self.__node.id,
            'timer_id': self.timer_id,
            'cm': self.cm.id
        }
        return conf

    def timer_message(self, event: TimerEvent) -> str:
        return TimerMessage(self.timer_id, self.timer_name, self.secs, event).to_str(self.cm.em_id)

    def node(self) -> Node:
        return self.__node

    def inp(self) -> List[Node]:
        return self.__node.inp

    def out(self) -> Node:
        return self.__node.out

    def start(self):
        self.cm.on_outcoming_timer_event(self.timer_message(TimerEvent.START))

    def unpause(self):
        self.paused = False
        self.cm.on_outcoming_timer_event(self.timer_message(TimerEvent.UNPAUSE))

    def restart(self):
        self.cm.on_outcoming_timer_event(self.timer_message(TimerEvent.RESTART))

    def stop(self):
        self.elapsed = True
        self.cm.on_outcoming_timer_event(self.timer_message(TimerEvent.STOP))

    def stop_children(self):
        for child in self.child_actions():
            child.stop()

    def paused(self):
        return self.paused

    def pause(self):
        self.paused = True
        self.cm.on_outcoming_timer_event(self.timer_message(TimerEvent.PAUSE))

    def is_technical(self):
        return 'h' not in self.__node.requirements

    def queue_name(self):
        return self.__node.queue_name

    def child_actions(self):
        children = []

        def _get_children(action):
            for inp in action.inp():
                if inp.parent is None:
                    print(inp, inp.parent)
                else:
                    children.append(inp.parent)
                    _get_children(inp.parent)

        _get_children(self)
        return children

    def __repr__(self):
        if self.__node.file:
            return self.__node.info["Name"]
        return self.__node.name

    def speak(self):
        if self.__node.file is None:
            print(self.__node.name)
        else:
            phrase = random.sample(self.__node.info["Phrase"], 1)[0]
            warnings = self.__node.info["Warning"]
            params = self.extract_params(phrase)
            reformatted = self.reformat(params, phrase)

            if warnings:
                warning = random.sample(warnings, 1)[0]
                reformatted += "\n" + warning

            print(reformatted)
            self.cm.on_action_spoken(ContextUnit(reformatted, params))

    def remind(self):
        if self.__node.file is None:
            print("isn't", self, "done yet?")
        else:
            phrase = random.sample(self.__node.info["Remind"], 1)[0]
            params = self.extract_params(phrase)
            print(self.reformat(params, phrase))

    @staticmethod
    def extract_params(phrase: str) -> List[str]:
        """
        Извлекает имена параметров из фразы
        :param phrase:
        :return:
        """
        search = re.findall("{\w*}", phrase)
        return [x[1:-1] for x in search]

    def reformat(self, params, phrase: str):
        """
        Для каждлого параметра из params берет значение из параметров, указанных в Node
        и вставляет их в phrase
        :param params:
        :param phrase:
        :return:
        """
        reformatted: str = phrase
        if "ingredients" in params and self.node().inp_ingredients:
            reformatted = reformatted.replace("{ingredients}", ", ".join([x.name for x in self.node().inp_ingredients]))
        if "time" in params:
            reformatted = reformatted.replace("{time}", str(self.node().time))
        if self.node().params:
            for param in self.node().params:
                reformatted = reformatted.replace("{" + param + "}", self.node().params[param])
        return reformatted


