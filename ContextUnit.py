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
        self.type = unit_type
        self.phrase = phrase
        self.params = params
        self.solved = False

    def to_dict(self):
        conf = {
            'type': self.type,
            'phrase': self.phrase,
            'solved': self.solved
        }
        return {**conf, **self.params}

    def __repr__(self):
        return self.phrase + " " + str(self.type)
