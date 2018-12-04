from typing import List
import random

from Node import Node


class Tree:
    def __init__(self, head: Node, switch_proba=0.5):
        self.switch_proba = switch_proba
        self.head = head
        self.num_queues = len(self.head.inp)
        self.queue_names = []

    def leaves(self, start_node=None) -> List[Node]:
        """
        Листья всего дерева или поддерева, начинающегося из start_node
        :param start_node:
        :return:
        """
        _leaves = []

        def _get_tree_leaves(_node: Node):
            for inp in _node.inp:
                if inp.is_leaf():
                    _leaves.append(inp)
                else:
                    _get_tree_leaves(inp)

        if start_node is None:
            start_node = self.head
        _get_tree_leaves(start_node)
        return _leaves

    def assign_queue_names(self, names: List[str]):
        """
        Распределить имена очередей по веткам
        :param names:
        :return:
        """
        self.queue_names = names

        def _propagate_name(_node: Node, name: str):
            for inp in _node.inp:
                inp.queue_name = name
                _propagate_name(inp, name)

        for i, inp in enumerate(self.head.inp):
            inp.queue_name = names[i]
            _propagate_name(inp, names[i])

    def queue_nodes(self, queue_name):
        """
        Все узлы очереди с заданым именем очереди
        :param queue_name:
        :return:
        """
        nodes = []

        def _compare_name(_node: Node):
            for inp in _node.inp:
                if inp.queue_name == queue_name:
                    nodes.append(inp)
                    _compare_name(inp)

        _compare_name(self.head)
        return nodes

    def random_path(self, finished=None, all_visited_nodes=None, start_node=None):
        """
        Вспомогательная функция, ищет случайный путь в дереве
        При указании параметров, ищет путь при условии уже посещенных узлов
        :param finished:
        :param all_visited_nodes:
        :param start_node:
        :return:
        """
        if finished is None:
            finished = set()
            all_visited_nodes = []
            start_node: Node = random.sample(self.leaves(), 1)[0]

        current_node, current_queue = start_node, start_node.queue_name
        while True:
            all_visited_nodes.append(current_node)
            if current_node.out.is_head():
                finished.add(current_queue)

            if random.random() < self.switch_proba:
                # Можно уменьшить switch_proba, и тогда переключения между очередями станут реже
                next_queue = current_queue
            else:
                try:
                    next_queue = random.sample([name for name in self.queue_names
                                                if name != current_queue and name not in finished], 1)[0]
                except ValueError:
                    next_queue = current_queue

            if current_node.technical:
                time = current_node.time

            possible_nodes_to_move = self.queue_nodes(next_queue)
            if current_node.switchable:
                # Если можно сменить перескочить в другой узел
                nodes_to_move = []
                for _node in possible_nodes_to_move:
                    if _node not in all_visited_nodes \
                            and _node.out is not None \
                            and all(inp in all_visited_nodes for inp in _node.inp):
                        nodes_to_move.append(_node)
            else:
                nodes_to_move = [current_node.out]
                next_queue = current_queue

            if len(nodes_to_move) == 0 and len(all_visited_nodes) < len(self):
                all_visited_nodes.remove(current_node)
                continue
            elif len(all_visited_nodes) == len(self):
                return all_visited_nodes

            next_node: Node = random.sample(nodes_to_move, 1)[0]
            current_node, current_queue = next_node, next_queue

    def continue_path(self, path: List[Node]):
        """
        Вспомогательная функция
        Ищет случайный обход дерева, начинающийся с определенных узлов
        :param path:
        :return:
        """
        finished = set()
        all_visited_nodes = path.copy()
        start_nodes = [node for node in self.leaves() if node not in all_visited_nodes]

        for queue_name in self.queue_names:
            queue_nodes = self.queue_nodes(queue_name)
            if all(x in all_visited_nodes for x in queue_nodes):
                finished.add(queue_name)
            for node in queue_nodes:
                if node not in all_visited_nodes and all(x in all_visited_nodes for x in node.inp):
                    start_nodes.append(node)
        start_node = random.sample(start_nodes, 1)[0]
        return self.random_path(finished, all_visited_nodes, start_node)

    def path(self, path: List[Node]=None):
        """
        Находит путь случайных обход дерева
        Можно указать, с каких узлов начинать обход
        :param path:
        :return:
        """
        if path is None:
            return self.random_path()
        else:
            return self.continue_path(path)

    def requirements(self):
        """
        Собирает список ресурсов со всех узлов
        :return:
        """
        requirements = set()

        def _get_requirements(node: Node):
            for inp in node.inp:
                for req in inp.requirements:
                    requirements.add(req)
                _get_requirements(inp)
        _get_requirements(self.head)
        return sorted(requirements)

    def __len__(self):
        """
        Длина полного обхода дерева без корня
        :return:
        """
        _len = 0

        def _count_children(_node: Node):
            nonlocal _len
            for inp in _node.inp:
                _len += 1
                _count_children(inp)

        _count_children(self.head)
        return _len
