from enum import Enum


class Intent(Enum):
    NEXT_SIMPLE = 0,  # Переход к следующему по порядку действию
    REPEAT = 1,  # Повтори предыдущую реплику
    CHOOSE_NEXT = 2,  # Давай что-нибудь другое
    CHANGE_NEXT = 3,  # Дальше будем чистить картошку
    NEGATIVE_SIMPLE = 4,
    INIT = 5,


class IntentParser:
    positive = {"да", "ага", "дальше", "готово", "сделал", "сделала", "ок", "закончил"}
    negative = {"не", "нет"}
    repeat = {"повтори", "еще раз", "еще"}
    choose_next = {"другое", "поменяй", "измени"}
    init = {"давай готовить"}

    def __init__(self):
        pass

    def extract_intent(self, phrase: str) -> Intent:
        intent = None
        if any(x in phrase for x in self.positive):
            intent = Intent.NEXT_SIMPLE
        if any(x in phrase for x in self.repeat):
            intent = Intent.REPEAT
        if any(x in phrase for x in self.choose_next):
            intent = Intent.CHOOSE_NEXT
        if any(x in phrase for x in self.negative):
            intent = Intent.NEGATIVE_SIMPLE
        if any(x in phrase for x in self.init):
            intent = Intent.INIT
        return intent
