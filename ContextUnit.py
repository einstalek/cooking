import random
import string
from enum import Enum
from typing import List


class UnitType(Enum):
    CONFIRMATION = 0,
    CHOICE = 1,


class ContextUnit:
    def __init__(self, phrase: str, params: List = None, unit_type: UnitType = UnitType.CONFIRMATION):
        self.id = 'CU' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        self.type = unit_type.name
        self.phrase = phrase
        self.params = params
        self.solved = False

    def to_dict(self):
        conf = {
            'id': self.id,
            'type': self.type,
            'phrase': self.phrase,
            'solved': self.solved,
            'params': '\t'.join(self.params)
        }
        return conf

    @staticmethod
    def from_dict(d):
        _id = d['id']
        phrase = d['phrase']
        unit_type = UnitType[d['type']]
        solved = True if d['solved'] == 'True' else False
        params = d['params'].split('\t')
        params = params if len(params) > 0 else None
        cu = ContextUnit(phrase, params, unit_type)
        cu.solved = solved
        cu.id = _id
        return cu

    def __repr__(self):
        return self.phrase + " " + str(self.type)
