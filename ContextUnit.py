from enum import Enum
from typing import List


class UnitType(Enum):
    CONFIRMATION = 0,
    CHOICE = 1,


class ContextUnit:
    def __init__(self, phrase: str, params: List = None, unit_type: UnitType = UnitType.CONFIRMATION):
        self.type = unit_type
        self.phrase = phrase
        self.params = params

    def __repr__(self):
        return self.phrase + " " + str(self.type)
