import rom


class Ingredient(rom.Model):
    id = rom.String(required=True, unique=True)
    name = rom.String()


class Node(rom.Model):
    id = rom.String(required=True, unique=True)
    requirements = rom.String()
    name = rom.String()
    inp = rom.String()
    out = rom.String()
    time = rom.Float(),
    queue_name = rom.String()
    switchable = rom.Boolean()
    technical = rom.Boolean()
    parent = rom.String()
    out_ingredient = rom.String()
    inp_ingredients: rom.String()
