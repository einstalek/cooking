import string
from typing import List, Dict
import random

from redis_utils.redis_cursor import RedisCursor
from base_structures.time_table import TimeTable
from base_structures.node import Node


class Tree:
    """
    Класс, хранящий зависимости между действиями в графе
    """
    def __init__(self, head: Node=None, switch_proba=0.5):
        self.id = 'TREE' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        self.switch_proba = switch_proba
        self.head = head
        if self.head:
            self.num_queues = len(self.head.inp)
        self.queue_names = []

    def to_dict(self):
        conf = {
            'id': self.id,
            'switch_proba': self.switch_proba,
            'head': self.head.id,
            'num_queues': len(self.head.inp),
            'queue_names': ','.join(self.queue_names)
        }
        return conf

    @staticmethod
    def from_dict(d):
        tree = Tree()
        tree.id = d['id']
        tree.switch_proba = float(d['switch_proba'])
        tree.num_queues = int(d['num_queues'])
        tree.queue_names = d['queue_names'].split(',')
        return tree

    def save_to_db(self):
        """
        Сохраняет в Redis:
            1) Параметры дерева
            2) Все узлы и ссылки между ними
            3) Ингридиенты
        :return:
        """
        dispatcher = RedisCursor()
        # сохраняем параметры дерева
        dispatcher.save_to_db(self.to_dict())

        def _save_ingredients(node: Node):
            if node.inp_ingredients:
                for ingr in node.inp_ingredients:
                    dispatcher.save_to_db(ingr.to_dict())
            if node.out_ingredient:
                dispatcher.save_to_db(node.out_ingredient.to_dict())

        def _save_children(node: Node):
            for x in node.inp:
                dispatcher.save_to_db(x.to_dict())
                _save_ingredients(x)
                _save_children(x)

        # сохраняем узлы дерева
        dispatcher.save_to_db(self.head.to_dict())
        _save_ingredients(self.head)
        _save_children(self.head)

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

    def rational_start(self) -> Node:
        """
        Строит путь в соответсвии с дополнительными правилами:
            1) Начинает с длинной ветки
            2) Переключается только при запуске или срабатывании таймера
            3) Стремится завершить длинные ветки быстрее
        :return:
        """
        time_queue= self.time_queue_dist()
        longest_queue = sorted(time_queue.items(), key=lambda x: x[0], reverse=False)[0][0]
        start_node = random.sample([node for node in self.leaves() if node.queue_name == longest_queue], 1)[0]
        return start_node

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
            start_node = self.rational_start()
            # start_node: Node = random.sample(self.leaves(), 1)[0]

        time_dist = self.time_queue_dist()

        current_node, current_queue = start_node, start_node.queue_name
        while True:
            all_visited_nodes.append(current_node)
            if current_node.out.is_head():
                finished.add(current_queue)

            if random.random() > self.switch_proba:
                # Можно уменьшить switch_proba, и тогда переключения между очередями станут реже
                next_queue = current_queue
            else:
                try:
                    possible_queue_moves = [name for name in self.queue_names
                                            if name != current_queue and name not in finished]
                    max_priority = max([time_dist[name] for name in possible_queue_moves])
                    possible_queue_moves = [name for name in possible_queue_moves if time_dist[name] == max_priority]
                    next_queue = random.sample(possible_queue_moves, 1)[0]
                except ValueError:
                    next_queue = current_queue

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

    def path(self, path: List[Node] = None):
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

    def nodes(self) -> List[Node]:
        """
        Возвращает все узлы дерева кроме корня
        :return:
        """
        children = []

        def _get_children(node: Node):
            for inp in node.inp:
                children.append(inp)
                _get_children(inp)

        _get_children(self.head)
        return children

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

    def individual(self) -> List[Node]:
        # nodes = self.nodes()
        # random.shuffle(nodes)
        return self.path()

    def fitness(self, individual: List[Node]):
        """
        The bigger the better
        :param individual:
        :return:
        """
        _sum = 0
        visited_nodes = []
        for node in individual:
            if not all(inp in visited_nodes for inp in node.inp):
                # Если посетили узел, не посетив всех его детей
                _sum -= 60
            try:
                prev_node = visited_nodes[-1]
                if not prev_node.switchable and node != prev_node.out:
                    # Если перескочили на узле, на котором нельзя было это делать
                    _sum -= 60
            except IndexError:
                pass
            if len(node.inp) == 1 and node.inp[0].technical:
                # Штрафуем за чрезмерное ожидание после технического действия
                prev_tech_node = node.inp[0]
                try:
                    idx = visited_nodes.index(prev_tech_node)
                    time = prev_tech_node.time
                    delta = time
                    try:
                        for _node in visited_nodes[idx + 1:]:
                            if not node.technical:
                                delta -= _node.time
                    except IndexError:
                        pass
                    _sum -= abs(delta)
                except ValueError:
                    pass

            try:
                if node.queue_name != visited_nodes[-1].queue_name:
                    # Штрафуем за скачки между очередями
                    _sum -= 20
            except IndexError:
                pass

            visited_nodes.append(node)
        _sum -= TimeTable(self.requirements(), max_size=200)(individual).time()
        return _sum

    def population(self, count: int) -> List[List[Node]]:
        return [self.individual() for _ in range(count)]

    def grade(self, population: List[List[Node]]):
        _sum = sum(self.fitness(individual) for individual in population)
        return _sum / len(population)

    def cross_individuals(self, first: List[Node], second: List[Node], n_trials: int=20):
        """
        Скрещивание двух особей
        Особь на выходе получается не хуже обоих родителей
        :param n_trials:
        :param first:
        :param second:
        :return:
        """
        fit_first, fit_second = self.fitness(first), self.fitness(second)
        best = first[:] if fit_first > fit_second else second[:]
        max_ind, max_fit = best, self.fitness(best)
        for i in range(n_trials):
            idx1, idx2 = random.sample(list(range(0, len(best))), 2)
            temp = max_ind[:]
            temp[idx1], temp[idx2] = temp[idx2], temp[idx1]
            temp_fit = self.fitness(temp)
            if temp_fit > max_fit:
                max_ind = temp
                max_fit = temp_fit
        return max_ind

    def mutation(self):
        new = self.path()
        return new

    def epoch(self, population, retain=0.5, mutate=0.3):
        """
        Смена одного поколения
        Новое поколение формируется из скрещиваний и мутаций
        :param population:
        :param retain:
        :param mutate:
        :return:
        """
        grades = [(ind, self.fitness(ind)) for ind in population]
        pop_size = len(population)
        sorted_pop = [x[0] for x in sorted(grades, key=lambda x: x[1], reverse=True)]
        parents = sorted_pop[:int(pop_size * retain)]
        new_pop = []
        for i in range(pop_size):
            if random.random() < mutate:
                new = self.mutation()
            else:
                idx1, idx2 = random.sample(list(range(0, len(parents))), 2)
                new = self.cross_individuals(parents[idx1], parents[idx2])
            new_pop.append(new)
        assert len(new_pop) == pop_size
        return new_pop

    def evolve(self, count: int=50, epochs: int=100, retain: float=0.5, mutate: float=0.2):
        """
        Процесс отбора в нескольких поколениях
        :param count:
        :param epochs:
        :param retain:
        :param mutate:
        :return:
        """
        mean_error = []
        start_pop = self.population(count)
        current_epoch, current_pop = 0, start_pop
        while current_epoch < epochs:
            new_pop = self.epoch(current_pop, retain, mutate)
            mean_error.append(self.grade(new_pop))
            # new_best_ind = self.select(new_pop, 1)[0]
            # new_best_score = self.fitness(new_best_ind)
            # best_error.append(new_best_score)
            current_pop = new_pop
            current_epoch += 1
        return current_pop, mean_error

    def select(self, population: List[List[Node]], count: int=1):
        grades = [(ind, self.fitness(ind)) for ind in population]
        sorted_pop = [x[0] for x in sorted(grades, key=lambda x: x[1], reverse=True)]
        return sorted_pop[:count]

    def mm_path(self, n_iterations: int = 100, start: List[Node] = None) -> List[Node]:
        """
        Ищет лучший обход среди случайно сгенерированных
        :param start:
        :param n_iterations:
        :return:
        """
        best = self.path(start)
        best_fit = self.fitness(best)
        for i in range(n_iterations):
            path = self.path(start)
            fit = self.fitness(path)
            if fit > best_fit:
                best_fit = fit
                best = path
        return best

    def time_queue_dist(self) -> Dict[str, float]:
        return {queue_name: sum([node.time for node in self.queue_nodes(queue_name)])
                for queue_name in self.queue_names}




