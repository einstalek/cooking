import random
import string
from typing import List
import yaml

from base_structures.ingredient import Ingredient


class Node:
    """
    Класс, хранящий информацию о действии
    """

    def __init__(self, name: str, time: int, requirements=None, switchable=True, technical=False,
                 file: str = None, parent=None, inp_ingredients: List[str] = None, out_ingredient=None, **kargs):
        """

        :param name:
        :param time:
        :param requirements:
        :param switchable: если True, то дальше по порядку обязательно идет следующий узел
        :param technical: если True, до к моменту завершения действия сразу начинается следующее действие
        :param parent: ссылка на обертку Action
        """
        self.id = 'N' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        self.name = name

        if requirements is None:
            requirements = []
        self.requirements = requirements

        self.inp: List[Node] = []
        self.out: Node = None

        self.time = time
        self.queue_name = None
        self.switchable = switchable
        self.technical = technical
        self.parent = parent

        self.file = file
        self.info = {}
        if self.file:
            self.info = yaml.load(open("../actions/" + self.file))

        self.out_ingredient = None
        if out_ingredient:
            self.out_ingredient = Ingredient(out_ingredient)
        self.inp_ingredients = None

        if inp_ingredients:
            self.inp_ingredients: List[Ingredient] = [Ingredient(x) for x in inp_ingredients]

        self.params = None
        if kargs:
            self.params = kargs

    def to_dict(self):
        try:
            conf = {
                'id': self.id,
                'requirements': ' '.join(self.requirements),
                'name': self.name,
                'inp': ' '.join([node.id for node in self.inp]),
                'out': self.out.id if self.out else '',
                'time': self.time,
                'queue_name': self.queue_name,
                'switchable': self.switchable,
                'technical': self.technical,
                'parent': self.parent.id if self.parent else '',
                'out_ingredient': self.out_ingredient.id if self.out_ingredient else '',
                'inp_ingredients': ' '.join([ingr.id for ingr in self.inp_ingredients]) if self.inp_ingredients else '',
                'file': self.file if self.file else '',
                'params': '-'.join([str(x) + '=' + str(y) for (x, y) in self.params.items()]) if self.params else ''
            }
        except AttributeError:
            print(self.parent)
            raise ValueError
        return conf

    @staticmethod
    def from_dict(d):
        node = Node(d['name'], int(d['time']))
        node.id = d['id']
        node.requirements = d['requirements'].split()
        node.inp = d['inp'].split() if d['inp'] != '' else []
        node.out = d['out'] if d['out'] != '' else None
        node.inp_ingredients = d['inp_ingredients'].split() if d['inp_ingredients'] != '' else None
        node.out_ingredient = d['out_ingredient'] if d['out_ingredient'] != '' else None
        node.switchable = True if d['switchable'] == 'True' else False
        node.technical = True if d['technical'] == 'True' else False
        node.parent = d['parent'] if d['parent'] != '' else None
        node.queue_name = d['queue_name']
        node.file = d['file'] if d['file'] != '' else None
        node.info = {}
        if node.file:
            node.info = yaml.load(open("../actions/" + node.file))
        node.params = None
        if d['params'] != '':
            items = [x.split('=') for x in d['params'].split('-')]
            node.params = {x:y for (x, y) in items}
        return node

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

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id + ">" + self.name

    def children(self):
        result = []

        def _get_children(node):
            for inp in node.inp:
                result.append(inp)
                _get_children(inp)

        _get_children(self)
        return result
