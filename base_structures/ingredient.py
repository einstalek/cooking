import random
import string


class Ingredient:
    def __init__(self, name: str):
        """

        :param name: название ингридиента и опционально его количество через ":"
        """
        self.id = 'I' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        if ':' not in name:
            self.name = name
            self.quantity = None
        else:
            self.name, self.quantity = name.split(':')

    def to_dict(self):
        conf = {
            'name': self.name + ':' + self.quantity if self.quantity else self.name,
            'id': self.id,
        }
        return conf

    @staticmethod
    def from_dict(d):
        ingr = Ingredient(d['name'])
        ingr.id = d['id']
        return ingr

    def __repr__(self):
        if self.quantity:
            return self.quantity + ' ' + self.name
        else:
            return self.name

    def __str__(self):
        if self.quantity:
            return self.quantity + ' ' + self.name
        else:
            return self.name
