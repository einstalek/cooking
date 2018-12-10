from typing import List
import yaml

from Ingredient import Ingredient


class Node:
    """
    Класс, хранящий информацию о действии
    """
    def __init__(self, name, time: int, requirements=None, switchable=True, technical=False,
                 file: str = None, parent=None, inp_ingredients=None, out_ingredient=None, **kargs):
        """

        :param name:
        :param time:
        :param requirements:
        :param switchable: если True, то дальше по порядку обязательно идет следующий узел
        :param technical: если True, до к моменту завершения действия сразу начинается следующее действие
        :param parent: ссылка на обертку Action
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

        self.out_ingredient = Ingredient(out_ingredient)
        self.inp_ingredients = None
        if inp_ingredients:
            self.inp_ingredients: List[Ingredient] = [Ingredient(x) for x in inp_ingredients]

        self.params = None
        if kargs:
            self.params = kargs

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
        for node in other:
            if node.out_ingredient:
                if self.inp_ingredients is None:
                    self.inp_ingredients = []
                self.inp_ingredients.append(node.out_ingredient)
        return self

    def __repr__(self):
        return self.name
