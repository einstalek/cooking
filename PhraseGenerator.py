import os
import random
import re
from typing import List, Dict

path = os.path.dirname(os.path.realpath(__file__))


class PhraseGenerator:
    @staticmethod
    def phrase(file) -> str:
        try:
            with open(os.path.join(path, "dialogs/" + file + ".dialog")) as f:
                phrases = [x.strip() for x in f.readlines()]
                return random.sample(phrases, 1)[0]
        except FileNotFoundError:
            return " ".join(file.split("."))

    @staticmethod
    def extract_params(phrase: str) -> List[str]:
        search = re.findall("{\w*}", phrase)
        return [x[1:-1] for x in search]

    @staticmethod
    def reformat(to_insert: Dict, phrase: str):
        reformatted: str = phrase
        params = PhraseGenerator.extract_params(phrase)
        assert all(x in params for x in to_insert)

        for param in to_insert:
            reformatted = reformatted.replace("{" + param + "}", str(to_insert[param]))

        # Если остались не заполненные параметры, заменяем их пробелами
        for param in params:
            if param not in to_insert:
                reformatted = reformatted.replace("{" + param + "}", "")
        return reformatted

    @staticmethod
    def speak(file, **params):
        phrase = PhraseGenerator.phrase(file)
        print(PhraseGenerator.reformat(params, phrase))


if __name__ == "__main__":
    PhraseGenerator().speak("switch.queue", queue_name="пюре")
