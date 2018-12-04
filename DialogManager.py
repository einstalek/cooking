from typing import List
from Action import Action, Intent
from Node import Node
from TimeTable import TimeTable
from threading import Thread
import time

from Timer import Timer, Manager


class DialogManager(Manager):
    def __init__(self, tree, n_iterations=500):
        self.n_iterations = n_iterations
        self.tree = tree
        self.stack: List[Action] = []
        self.path: List[Node] = None
        self.current_idx = None

        Manager.__init__(self)

        t = Thread(target=self.update)
        t.start()

    def fastest_path(self, tree, start_path=None):
        """
        Находит скорейший путь по дереву
        :param tree:
        :param start_path:
        :return:
        """
        requirements = tree.requirements()
        min_path, min_time, min_table = None, 110, None
        for i in range(self.n_iterations):
            path = tree.path(start_path)
            table = TimeTable(requirements, 200)(path)
            if table.time() < min_time:
                min_time = table.time()
                min_path = path
                min_table = table
        return min_path, min_table

    def initialize(self):
        self.path, table = self.fastest_path(self.tree)
        self.current_idx = 0
        self.stack.append(Action(self.path[self.current_idx], self))

        print(self.path)
        table.print()

        # self.on_stack_changed()

    def on_stack_changed(self):
        """
        Вызывается для обработки действия на верху стэка
        :return:
        """
        try:
            top_action = self.stack[-1]
        except IndexError:
            print("stack is empty")
            return
        top_action.speak()
        top_action.start()
        if top_action.is_technical():
            print()
            self.handle_next_response()
        else:
            self.wait_for_response()

    def wait_for_response(self):
        """
        Ожидание реплики со стороны клиента
        :return:
        """
        response = input()
        if 'r' == response:
            intent = Intent.REPEAT
        else:
            intent = Intent.NEXT
        self.handle_intent(intent)

    def update(self):
        """
        Функция, работающая в отдельном потоке
        Обновляет таймеры действий в стэке с перерывом в 1 секунду
        :return:
        """
        while True:
            for action in self.stack:
                action.update()
            time.sleep(1)

    def handle_intent(self, intent: Intent, *args, **kargs):
        """
        Обработчик интентов
        :param intent:
        :param args:
        :param kargs:
        :return:
        """
        if intent == Intent.NEXT:
            self.handle_next_response()
        elif intent == Intent.REPEAT:
            self.handle_repeat_response()
        elif intent == Intent.TIMEOUT:
            self.handle_timeout_response()

    def handle_next_response(self):
        """
        Интент перехода к следующему действию
        :return:
        """
        top_action = self.stack[-1]
        if not top_action.is_technical():
            # Если действие не техническое, то останавливаем таймеры у всех детей и добавляем в стэк следующее действие
            top_action.stop()
        self.current_idx += 1
        try:
            self.stack.append(Action(self.path[self.current_idx], self))
        except IndexError:
            print("Finished")
            return
        self.on_stack_changed()

    def handle_repeat_response(self):
        """
        Интент повторения реплики текущего действия
        :return:
        """
        top_action = self.stack[-1]
        top_action.speak()
        self.wait_for_response()

    def handle_timeout_response(self):
        """
        Обработчик таймаута у текущего действия, если оно не является техническим
        :return:
        """
        pass

    def on_timer_elapsed(self, timer: Timer):
        """
        Обработчик события истечения времени у таймера
        :param timer:
        :return:
        """
        action: Action = timer.parent
        print("REMINDER:", action.node.name)



