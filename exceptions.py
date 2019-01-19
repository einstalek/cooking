class MqConnectionError(Exception):
    def __init__(self, *args: object) -> None:
        self.message = "Не удалось подключиться к MQ"
        super().__init__(self.message)

