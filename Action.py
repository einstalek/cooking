from enum import Enum
from typing import List

from Node import Node
from Timer import Timer


class Intent(Enum):
    NEXT = 0,
    REPEAT = 1,
    TIMEOUT = 2,


class Action:
    def __init__(self, node: Node, dm):
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

    def speak(self):
        print(self.node.name)

    def is_technical(self):
        return 'h' not in self.node.requirements

    def child_actions(self):
        children = []

        def _get_children(action):
            node: Node = action.node
            for inp in node.inp:
                children.append(inp.parent)
                _get_children(inp.parent)
        _get_children(self)
        return children


