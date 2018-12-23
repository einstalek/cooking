import random
import string


class Ingredient:
    def __init__(self, name):
        self.id = 'I' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        self.name = name

    def __repr__(self):
        return self.name
