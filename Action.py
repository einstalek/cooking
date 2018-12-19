from typing import List
from Node import Node
from Timer import Timer
from abcManager import Manager
from ContextUnit import ContextUnit
import random
import re


class Action:
    def __init__(self, node: Node, cm: Manager):
        self.__node = node
        node.parent = self
        self.timer = Timer(node.time, node.name, self)
        self.cm = cm

    def node(self) -> Node:
        return self.__node

    def inp(self) -> List[Node]:
        return self.__node.inp

    def out(self) -> Node:
        return self.__node.out

    def update(self):
        self.timer.update()

    def start(self):
        self.timer.start()

    def unpause(self):
        self.timer.unpause()

    def stop(self):
        self.timer.stop()

    def stop_children(self):
        for child in self.child_actions():
            child.stop()

    def paused(self):
        return self.timer.paused

    def pause(self):
        self.timer.pause()

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


