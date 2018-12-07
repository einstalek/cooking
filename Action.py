from typing import List
from Node import Node
from Timer import Timer, Manager
import random


class Action:
    def __init__(self, node: Node, cm: Manager):
        self.__node = node
        node.parent = self
        self.timer = Timer(node.time, node.name, self)
        self.cm = cm

    def node(self):
        return self.__node

    def inp(self) -> List[Node]:
        return self.__node.inp

    def out(self) -> Node:
        return self.__node.out

    def update(self):
        self.timer.update()

    def start(self):
        self.timer.start()

    def restart(self):
        self.timer.restart()

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
        return self.__node.name

    def speak(self):
        if self.__node.file is None:
            print(self.__node.name, self.__node.time)
        else:
            phrase = random.sample(self.__node.info["Phrase"], 1)[0]
            print(phrase)

    def remind(self):
        if self.__node.file is None:
            print("isn't", self, "done yet?")
        else:
            phrase = random.sample(self.__node.info["Remind"], 1)[0]
            print(phrase)
