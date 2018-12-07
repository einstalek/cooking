from enum import Enum
from Timer import Manager


class Intent(Enum):
    NEXT = 0,  # Переход к следующему по порядку действию
    REPEAT = 1,  # Повтори предыдущую реплику
    TIMEOUT = 2,    # У действия сработал таймер
    NOT_READY = 3,  # TODO: Не могу перейти к следующему действию, ибо предыдущее еще не завершилось
    GET_DETAIL = 4,     # TODO: Вопрос о какой-то детали из какого-то действия


class DialogManager:
    """
    Класс, принимающий реплики человека и извлекающий из них интенты
    """
    def __init__(self, dm: Manager):
        self.dm = dm

    def run(self):
        response = input()
        if 'r' == response:
            intent = Intent.REPEAT
        elif 'n' == response:
            intent = Intent.NOT_READY
        else:
            intent = Intent.NEXT
        self.dm.handle_intent(intent)
