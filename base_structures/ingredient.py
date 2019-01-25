import random
import string


class Ingredient:
    def __init__(self, name: str, quantity: str = None):
        self.id = 'I' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        self.name = name
        self.quantity = quantity

    def to_dict(self):
        conf = {
            'name': self.name,
            'id': self.id,
            'quantity': self.quantity if self.quantity else ''
        }
        return conf

    @staticmethod
    def from_dict(d):
        quantity = None if d['quantity'] == '' else d['quantity']
        ingr = Ingredient(d['name'], quantity)
        ingr.id = d['id']
        return ingr

    def __repr__(self):
        if self.quantity:
            return self.quantity + ' ' + self.name
        else:
            return self.name

    def __str__(self):
        return self.name
