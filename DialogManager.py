from typing import List
from Action import Action, Intent
from Node import Node
from threading import Thread
import time
import random

from TimeTable import TimeTable
from Timer import Timer, Manager
from InputHandler import InputHandler


class DialogManager(Manager):
    def __init__(self, tree, n_iterations=500):
        self.n_iterations = n_iterations
        self.tree = tree
        self.stack: List[Action] = []
        self.finished_stack = []
        self.path: List[Node] = None
        self.current_path_idx = None
        self.input = InputHandler(self)

        Manager.__init__(self)

        t = Thread(target=self.update)
        t.start()

    def initialize(self):
        # pop, err = self.tree.evolve(count=100, epochs=300, mutate=0.25)
        # self.path = self.tree.select(pop, 1)[0]
        random.seed(10)
        self.path = self.tree.mm_path(n_iterations=2000)
        print("OVERALL TIME:", TimeTable(self.tree.requirements())(self.path).time())
        self.current_path_idx = 0
        self.stack.append(Action(self.path[self.current_path_idx], self))
        print(self.path)

        self.handle_top_action()

    def handle_top_action(self):
        """
        Вызывается для обработки несовершенного действия на вершине стэка
        :return:
        """
        try:
            top_action = self.stack[-1]
        except IndexError:
            print("Finished")
            return

        if top_action.timer.paused:
            top_action.timer.restart()
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
        t = Thread(target=self.input.run)
        t.start()

    def update(self):
        """
        Функция, работающая в отдельном потоке
        Обновляет таймеры действий в стэке с перерывом в 1 секунду
        :return:
        """
        while True:
            for action in self.stack:
                action.update()
            for action in self.finished_stack:
                action.update()
            time.sleep(1)

    def handle_intent(self, intent: Intent):
        """
        Обработчик интентов
        :param intent:
        :return:
        """
        if intent == Intent.NEXT:
            self.handle_next_response()
        elif intent == Intent.REPEAT:
            self.handle_repeat_response()

    def handle_next_response(self):
        print(self.stack, self.finished_stack)
        """
        Интент перехода к следующему действию
        :return:
        """
        top_action = self.stack[-1]
        if not top_action.is_technical():
            top_action.stop()
        self.stack.pop()
        self.finished_stack.append(top_action)

        if len(self.stack) == 0:
            try:
                self.current_path_idx += 1
                self.stack.append(Action(self.path[self.current_path_idx], self))
            except IndexError:
                print("Finished")
                return
        self.handle_top_action()

    def handle_repeat_response(self, *args, **kargs):
        """
        Интент повторения реплики текущего действия
        :return:
        """
        top_action = self.stack[-1]
        top_action.speak()
        self.wait_for_response()

    def handle_timeout_response(self, action: Action):
        """
        Обработчик таймаута у текущего действия
        :return:
        """
        current_action = self.stack[-1]
        if not action.is_technical():
            # Если действие не техническое, то просто напоминаем о нем
            print("isn't", action, "done yet?")
            self.wait_for_response()
        else:
            print()
            print("Let's return to", action.node.queue_name)
            next_action = Action(action.node.out, self)
            self.stack.append(next_action)
            current_action.pause()
            self.handle_top_action()

    def on_timer_elapsed(self, action: Action):
        """
        Обработчик события истечения времени у таймера
        :return:
        """
        self.handle_timeout_response(action)




