class MqConnectionError(Exception):
    def __init__(self, *args: object) -> None:
        self.message = "Не удалось подключиться к MQ"
        super().__init__(self.message)


class StartExistingTimerError(Exception):
    def __init__(self):
        self.message = "Получена команда создать уже существующий таймер"
        super().__init__(self.message)


class RegistrationRefusedError(Exception):
    def __init__(self):
        self.message = "Регистрация эмулятора не удалась"
        super().__init__(self.message)

