from typing import List
import yaml


class Node:
    def __init__(self, name, time: int, requirements=None, switchable=True, technical=False,
                 parent=None, file: str = None):
        """

        :param name:
        :param time:
        :param requirements:
        :param switchable: если True, то дальше по порядку обязательно идет следующий узел
        :param technical: если True, до к моменту завершения действия сразу начинается следующее действие
        :param parent:
        """
        if requirements is None:
            requirements = []
        assert all(req in requirements for req in requirements)
        self.name = name
        self.inp: List[Node] = []
        self.out: Node = None
        self.requirements = requirements
        self.time = time
        self.queue_name = None
        self.switchable = switchable
        self.technical = technical
        self.parent = parent
        self.file = file
        self.info = {}
        if self.file:
            self.info = yaml.load(open("actions/" + self.file))

    def add_input(self, other):
        self.inp.extend(other)
        for _node in other:
            _node.out = self

    def is_leaf(self):
        return len(self.inp) == 0

    def is_head(self):
        return self.out is None

    def __call__(self, *other):
        self.add_input(other)
        return self

    def __repr__(self):
        return self.name
