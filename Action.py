from enum import Enum
from typing import List

from Node import Node
from Timer import Timer, Manager


class Intent(Enum):
    NEXT = 0,
    REPEAT = 1,
    TIMEOUT = 2,
    TEMP_SKIP = 3,
    NOT_READY = 4,


class Action:
    def __init__(self, node: Node, dm: Manager):
        self.node = node
        node.parent = self
        self.timer = Timer(node.time, node.name, self)
        self.dm = dm

    def update(self):
        self.timer.update()

    def start(self):
        self.timer.start()

    def stop(self):
        self.timer.stop()
        for child in self.child_actions():
            assert isinstance(child, Action)
            child.stop()

    def pause(self):
        self.timer.pause()

    def speak(self):
        print(self.node.name, self.node.time)

    def is_technical(self):
        return 'h' not in self.node.requirements

    def child_actions(self):
        children = []

        def _get_children(action):
            try:
                node: Node = action.node
            except AttributeError:
                print(action)
            for inp in node.inp:
                children.append(inp.parent)
                _get_children(inp.parent)
        _get_children(self)
        return children

    def __repr__(self):
        return self.node.name


