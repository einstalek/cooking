from enum import Enum
from Timer import Manager


class Intent(Enum):
    NEXT = 0,  # Переход к следующему по порядку действию
    REPEAT = 1,  # Повтори предыдущую реплику
    TIMEOUT = 2,  # У действия сработал таймер
    CHANGE = 3,  # Давай что-нибудь другое


class DialogManager:
    """
    Класс, принимающий реплики человека и извлекающий из них интенты
    """

    def __init__(self, cm: Manager):
        self.context_manager = cm
        self.stack = []

    def run(self):
        response = input()
        if 'r' == response:
            intent = Intent.REPEAT
        elif 'n' == response:
            intent = Intent.NEXT
        elif 'c' == response:
            intent = Intent.CHANGE
        else:
            intent = Intent.NEXT
        # сохраняем пришедший интент и предшуствующее ему состояние CM
        self.stack.append([intent, self.context_manager.current_state()])
        self.context_manager.handle_intent(intent)

