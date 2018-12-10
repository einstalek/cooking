from typing import List
from Action import Action
from Node import Node
from threading import Thread
import time
import random

from TimeTable import TimeTable
from Timer import Manager
from DialogManager import DialogManager, Intent


class ContextManager(Manager):
    """
    Класс, ответственный за переключения между действиями
    Так же принимает Intent от DialogManager-а при реагирует на него
    """

    def __init__(self, tree, n_iterations=500):
        self.n_iterations = n_iterations
        self.tree = tree
        self.stack: List[Action] = []
        self.finished_stack = []
        self.path: List[Node] = None
        self.current_path_idx = None
        self.input = DialogManager(self)

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
        # print(self.path)

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

        top_action.speak()

        if top_action.paused():
            top_action.restart()
        else:
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
        elif intent == Intent.NOT_READY:
            self.handle_not_ready_response()

    def handle_next_response(self):
        """
        Интент перехода к следующему действию
        :return:
        """
        try:
            top_action = self.stack[-1]
        except IndexError:
            print("Finished")
            return

        if not top_action.is_technical():
            top_action.stop()
            top_action.stop_children()

        self.stack.pop()
        self.finished_stack.append(top_action)

        self.current_path_idx += 1
        if len(self.stack) == 0:
            try:
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

    def on_timer_elapsed(self, action: Action):
        """
        Обработчик события истечения времени у таймера
        :return:
        """
        self.handle_timeout_response(action)

    def handle_timeout_response(self, action: Action):
        """
        Обработчик таймаута у текущего действия
        :return:
        """
        if not action.is_technical() or len(action.out().inp) > 1:
            # Если не требуется переходить к другому действию, просто напоминаем о таймауте и замолкаем
            self.remind(action)
        elif action.is_technical() and len(action.out().inp) == 1:
            print()
            # Если вышел таймер технического действия, ставим на паузу текущее действие
            # И кладем в стэк следующее  действие
            current_action = self.stack[-1]
            # Совпадает ли очередь у действия на вершине стэка и у сработавшего действия
            if action.queue_name() == current_action.queue_name():
                # Тут ситцация, когда перешли в действию, когда предшествующее ему
                # техническое действие не успело завершиться
                self.wait_for_response()
            else:
                # Ставим в стэк над приостановленным действием следующее и меняем их порядок в self.path
                current_action.pause()
                current_action.stop_children()
                print("Let's return to", action.queue_name(), "from", action)
                next_action = None
                for node in self.path[self.current_path_idx + 1:]:
                    if node.queue_name == action.queue_name():
                        next_action = Action(node, self)
                        break
                idx = self.path.index(next_action.node())
                self.path[self.current_path_idx:] = [self.path[idx]] + \
                                                    [x for x in self.path[self.current_path_idx:]
                                                     if x != next_action.node()]
                self.stack.append(next_action)
                self.handle_top_action()

    def remind(self, action):
        if not action.is_technical():
            action.remind()
        else:
            print("REMINDER:", action)
        self.wait_for_response()

    def handle_not_ready_response(self):
        # TODO
        top_action = self.stack[-1]
        prev_action = None
        for action in self.finished_stack:
            if action.queue_name() == top_action.queue_name() and not action.timer.elapsed:
                prev_action = action
        assert prev_action is not None
        self.wait_for_response()



