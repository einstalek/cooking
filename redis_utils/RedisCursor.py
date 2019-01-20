from typing import Dict

import redis


class RedisCursor:
    __instance = None
    __conn: redis.Redis = None
    isep = '\t'
    kvsep = ':'

    class __SingleTon__:
        def __init__(self, host, port, db):
            self.host = host
            self.port = port
            self.db = db

    def __init__(self, host="localhost", port=6379, db=0):
        if RedisCursor.__instance is None:
            RedisCursor.__instance = self.__SingleTon__(host, port, db)
            RedisCursor.__conn = redis.Redis(host=host, port=port, db=db)

    def inst(self):
        return RedisCursor.__instance

    def conn(self):
        return RedisCursor.__conn

    def save_to_db(self, kargs: Dict):
        assert 'id' in kargs
        key, value = kargs['id'], "\t".join([str(k) + ':' + str(v) for (k, v) in kargs.items()])
        self.conn().set(key, value)

    def get(self, key):
        """
        Возвращает декодированный словарь
        :param key:
        :return:
        """
        try:
            return self.value_to_dict(self.conn().get(key).decode())
        except AttributeError as e:
            print("wrong key:", key)
            raise KeyError

    def value_to_dict(self, value: str):
        """
        Преобразует строку из redis в словарь
        :param value:
        :return:
        """
        items = [x.split(self.kvsep) for x in value.split(self.isep)]
        kargs = {x[0]: x[1] for x in items}
        return kargs


if __name__ == '__main__':
    disp = RedisCursor()
    disp.save_to_db({"id" : 12, 'k': 11})


