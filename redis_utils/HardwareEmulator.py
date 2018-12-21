from redis_utils.WebServer import WebServer


class HardwareEmulator:
    def __init__(self, host="localhost", port=8888):
        self.host = host
        self.port = port
        self.server = WebServer()

    def send(self, request):
        self.server.on_message(request)

    def run(self):
        while True:
            request = input()
            if request:
                self.send(request)


if __name__ == "__main__":
    HardwareEmulator().run()

