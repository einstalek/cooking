from Action import Intent
from Timer import Manager


class InputHandler:
    def __init__(self, dm: Manager):
        self.dm = dm

    def run(self):
        response = input()
        if 'r' == response:
            intent = Intent.REPEAT
        else:
            intent = Intent.NEXT
        self.dm.handle_intent(intent)
