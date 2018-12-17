from typing import List, Optional
from Action import Action
from ContextUnit import ContextUnit, UnitType
from Node import Node
from threading import Thread
import time
import random
import datetime

from TimeTable import TimeTable
from abcManager import Manager
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
        self.dialog_manager = DialogManager(self)

        Manager.__init__(self)

        t = Thread(target=self.update)
        t.start()

    def initialize(self):
        # random.seed(11)
        self.path = self.tree.mm_path(n_iterations=2000)
        print("РАСЧЕТНОЕ ВРЕМЯ:", TimeTable(self.tree.requirements())(self.path).time())
        self.current_path_idx = 0
        self.stack.append(Action(self.path[self.current_path_idx], self))
        self.handle_top_action()

    def current_state(self):
        """
        Состояние контекст мэнеджера описывается двумя стэками
        :return:
        """
        return self.stack.copy(), self.finished_stack.copy()

    def handle_intent(self, intent: Intent, params=None):
        """
        Обработчик интентов
        :param params:
        :param intent:
        :return:
        """
        if intent == Intent.NEXT:
            self.handle_next_response()
        elif intent == Intent.REPEAT:
            self.handle_repeat_response()
        elif intent == Intent.CHOOSE_NEXT:
            self.handle_choosing_next()
        elif intent == Intent.CHANGE_NEXT:
            self.handle_changing_next(params)

    def handle_top_action(self):
        """
        Вызывается для обработки несовершенного действия на вершине стэка
        :return:
        """
        try:
            top_action = self.stack[-1]
        except IndexError:
            return

        # Проверка, что предшествующие технические действия выполнены
        prev_action = self.last_waiting_action(top_action)
        assert prev_action is None

        # Выдается реплика действия
        top_action.speak()

        # Запускается или возобновляется таймер действия
        if top_action.paused():
            top_action.unpause()
        else:
            top_action.start()

        # переход к следующему действию или ожидание ответа от человека
        if top_action.is_technical():
            print()
            self.handle_next_response()
        else:
            self.wait_for_response()

    def handle_next_response(self):
        try:
            top_action = self.stack[-1]
        except IndexError:
            if len(self.path) == self.current_path_idx:
                pass
            else:
                # Узлы обошли не все, но когда человек дал команду 'дальше', стэк был пустой
                # Это произошло потому, что было ожидание какого-то технического действия
                # Поэтому здесь останавливаем техническое действие и идем дальше по path
                self.current_path_idx += 1
                return_to = Action(self.path[self.current_path_idx], self)
                return_to.stop_children()
                self.stack.append(return_to)
                self.handle_top_action()
            return

        if not top_action.is_technical():
            top_action.stop()
            top_action.stop_children()

        self.stack.pop()
        self.finished_stack.append(top_action)

        self.current_path_idx += 1
        if len(self.stack) == 0:
            try:
                next_action = Action(self.path[self.current_path_idx], self)
                prev_action = self.last_waiting_action(next_action)
                if prev_action is None:
                    # Если все нормально, двигаемся дальше по path
                    self.stack.append(Action(self.path[self.current_path_idx], self))
                else:
                    # Если следующему действию предшествует незавершенное техническое действие
                    # Пытаемся переключиться на другое действие
                    node_switch_to = self.try_to_switch(prev_action)
                    if node_switch_to is None:
                        # Если переключиться некуда, остается ждать завершения технического действия,
                        # сдвинуть current_index на 1 назад и может быть ждать ответа
                        self.current_path_idx -= 1
                        print("Ждем", prev_action.node().name)
                        self.wait_for_response()
                        return
                    else:
                        # Если есть куда перейти, пересчтываем path и добавляем другое действие на верх стэка
                        self.path = self.tree.mm_path(start=self.path[:self.current_path_idx] + [node_switch_to])
                        self.stack.append(Action(node_switch_to, self))
            except IndexError:
                pass
                return
        else:
            # Если в стэке уже что-то есть, то пока в него ничего не добавляем
            pass
        self.handle_top_action()

    def handle_timeout_response(self, action: Action):
        """
        Обработчик таймаута у текущего действия
        :return:
        """
        if not action.is_technical() or len(action.out().inp) > 1:
            # TODO: непонятный момент
            self.remind(action)
        elif action.is_technical() and len(action.out().inp) == 1:
            try:
                current_action = self.stack[-1]
            except IndexError:
                # Если стэк был пустым, значит мы ждади завершения технического действия
                self.current_path_idx += 1
                current_action = Action(self.path[self.current_path_idx], self)
                self.stack.append(current_action)
                self.handle_top_action()
                return
            if action.queue_name() != current_action.queue_name():
                # Ставим в стэк над приостановленным действием следующее и меняем их порядок в self.path
                current_action.pause()
                current_action.stop_children()
                print()
                print("Вернемся пока к", action.queue_name())
                next_action = None
                for node in self.path[self.current_path_idx + 1:]:
                    if node.queue_name == action.queue_name():
                        next_action = Action(node, self)
                        break
                assert next_action is not None
                self.path[self.current_path_idx:] = [next_action.node()] + \
                                                    [x for x in self.path[self.current_path_idx:]
                                                     if x != next_action.node()]
                self.stack.append(next_action)
                self.handle_top_action()

    def last_waiting_action(self, top_action) -> Optional[Action]:
        """
        Если в finished_stack есть незавершенное техническое действие
        которое предшествует top_action, то вернет его
        :param top_action:
        :return:
        """
        prev_action = None
        for action in self.finished_stack:
            if top_action.queue_name() == action.queue_name() \
                    and not action.timer.elapsed \
                    and action in top_action.child_actions():
                prev_action = action
                break
        return prev_action

    def try_to_switch(self, prev_action) -> Optional[Node]:
        """
        Пытается найти действие, которое можно выполнить раньше next_action
        :param prev_action: незавершенное действие, предшествующее next_action
        :return:
        """
        possible_moves: List[Node] = []
        # Собираем все возможные переходы
        for node in self.path[self.current_path_idx + 1:]:
            if all(self.node_finished(x) for x in node.children()) or len(node.inp) == 0:
                possible_moves.append(node)
        if len(possible_moves) == 0:
            return None

        time = prev_action.timer.time_left()
        time_diff = [abs(time - datetime.timedelta(seconds=node.time)) for node in possible_moves]
        chosen_node = possible_moves[time_diff.index(min(time_diff))]
        return chosen_node

    def node_finished(self, node):
        # Проверяет, что действие есть в завершенном стэке и оно остановлено
        for action in self.finished_stack:
            if action.node() == node and action.timer.elapsed:
                return True
        return False

    def wait_for_response(self):
        """
        Ожидание реплики со стороны клиента
        :return:
        """
        print("...")
        # t = Thread(target=self.dialog_manager.extract_intent)
        # t.start()

    def remind(self, action):
        if not action.is_technical():
            action.remind()
            self.wait_for_response()
        else:
            print("НАПОМИНАНИЕ:", action.node().name)

    def handle_repeat_response(self, *args, **kargs):
        """
        Интент повторения реплики текущего действия
        :return:
        """
        top_action = self.stack[-1]
        top_action.speak()
        self.wait_for_response()

    def handle_choosing_next(self):
        # TODO
        """
        Интент смены предлагаемого действия
        :return:
        """
        if len(self.stack) == 0:
            self.wait_for_response()
            return
        self.stack[-1].pause()
        possible_moves = []
        for node in self.path[self.current_path_idx + 1:]:
            if self.node_finished(node) or len(node.inp) == 0:
                possible_moves.append(node)

        if len(possible_moves) == 0:
            self.wait_for_response()
            return
        phrase = "Выберите следующее дествие:" + repr(possible_moves)
        print(phrase)
        self.dialog_manager.push(ContextUnit(phrase, unit_type=UnitType.CHOICE,
                                             params=[str(x) for x in possible_moves]))
        self.wait_for_response()

    def handle_changing_next(self, node_name):
        top_action = self.stack[-1]
        if node_name is None:
            if top_action.paused():
                top_action.timer.restart()
            self.wait_for_response()
            return
        node_to_change = [x for x in self.path[self.current_path_idx + 1:] if x.name == node_name][0]
        temp = self.path[:self.current_path_idx] + [node_to_change]
        new_path = self.tree.mm_path(start=temp, n_iterations=2000)
        print("Новое время:", TimeTable(self.tree.requirements())(new_path).time())
        self.path = new_path
        self.stack.pop()
        self.stack.append(Action(node_to_change, self))
        self.handle_top_action()

    def on_timer_elapsed(self, action: Action):
        """
        Обработчик события истечения времени у таймера
        :return:
        """
        self.handle_timeout_response(action)

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
            time.sleep(0.1)

    def on_action_spoken(self, unit):
        """
        Когда действие произнесло фразу, добавляем ее в стэк диалог менеджера
        :param unit:
        :return:
        """
        self.dialog_manager.push(unit)




