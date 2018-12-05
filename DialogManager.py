from typing import List
from Action import Action, Intent
from Node import Node
from threading import Thread
import time

from TimeTable import TimeTable
from Timer import Timer, Manager
from InputHandler import InputHandler


class DialogManager(Manager):
    def __init__(self, tree, n_iterations=500):
        self.n_iterations = n_iterations
        self.tree = tree
        self.stack: List[Action] = []
        self.path: List[Node] = None
        self.current_idx = None
        self.input = InputHandler(self)

        Manager.__init__(self)

        t = Thread(target=self.update)
        t.start()

    def initialize(self):
        pop, err = self.tree.evolve(count=100, epochs=250, mutate=0.5)
        self.path = self.tree.select(pop, 1)[0]
        print("OVERALL:", TimeTable(self.tree.requirements())(self.path).time())
        self.current_idx = 0
        self.stack.append(Action(self.path[self.current_idx], self))
        print(self.path)

        self.on_stack_changed()

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
            time.sleep(1)

    def handle_intent(self, intent: Intent):
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

    def handle_next_response(self):
        """
        Интент перехода к следующему действию
        :param args:
        :param kargs:
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

    def handle_repeat_response(self, *args, **kargs):
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
        print("isn't it done yet?")
        self.wait_for_response()

    def on_timer_elapsed(self, timer: Timer):
        """
        Обработчик события истечения времени у таймера
        :param timer:
        :return:
        """
        action: Action = timer.parent
        if action.is_technical():
            print("REMINDER:", action)
        else:
            self.handle_timeout_response()




