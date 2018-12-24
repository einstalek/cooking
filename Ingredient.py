import random
import string


class Ingredient:
    def __init__(self, name):
        self.id = 'I' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        self.name = name

    def to_dict(self):
        conf = {
            'name': self.name,
            'id': self.id
        }
        return conf

    @staticmethod
    def from_dict(d):
        ingr = Ingredient(d['name'])
        ingr.id = d['id']
        return ingr

    def __repr__(self):
        return self.id + ">" + self.name
