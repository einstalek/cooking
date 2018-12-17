from enum import Enum


class Intent(Enum):
    NEXT = 0,  # Переход к следующему по порядку действию
    REPEAT = 1,  # Повтори предыдущую реплику
    CHOOSE_NEXT = 2,  # Давай что-нибудь другое
    CHANGE_NEXT = 3,  # Дальше будем чистить картошку
    NEGATIVE = 4,


class IntentParser:
    positive = {"да", "ага", "дальше", "готово", "сделал", "сделала", "ок"}
    negative = {"не", "нет"}
    repeat = {"повтори", "еще раз", "еще"}
    choose_next = {"другое", "поменяй", "измени"}

    def __init__(self):
        pass

    def extract_intent(self, phrase: str):
        intent = None
        if any(x in phrase for x in self.positive):
            intent = Intent.NEXT
        if any(x in phrase for x in self.repeat):
            intent = Intent.REPEAT
        if any(x in phrase for x in self.choose_next):
            intent = Intent.CHOOSE_NEXT
        if any(x in phrase for x in self.negative):
            intent = Intent.NEGATIVE
        return intent
