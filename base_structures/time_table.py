from typing import List
from base_structures.node import Node


class TimeTable:
    """
    Структура, показывающая занятость ресурсов при определенном обходе дерева
    Используется для оценки времени каждого пути
    """
    def __init__(self, requirements, max_size=200, verbose=False):
        self.requirements = requirements
        self.max_size = max_size
        self.taken = {req: [0] * self.max_size for req in requirements}
        self.last_index = {req: 0 for req in requirements}
        self.verbose = verbose

    def add_node(self, node: Node):
        requirements = node.requirements
        last_index = max(self.last_index[req] for req in requirements)
        last_index = max(last_index, self.last_index['h'])
        for req in requirements:
            self.last_index[req] = last_index + node.time
            self.taken[req][last_index: last_index + node.time] = [1] * node.time

        if self.verbose:
            print(node, node.time)
            for req in self.requirements:
                if self.time() > 0:
                    print(self.taken[req][:self.time()], req)
                else:
                    print(self.taken[req], req)

    def __call__(self, path: List[Node]):
        for node in path:
            self.add_node(node)
        return self

    def time(self):
        return max(self.last_index[req] for req in self.requirements)

    def print(self):
        for req in self.requirements:
            print(self.taken[req][:self.time()], req)
