import random
from typing import List, Optional

import pika
from pika.adapters.blocking_connection import BlockingChannel

from Action import Action
from ContextUnit import ContextUnit, UnitType
from Node import Node
from PhraseGenerator import PhraseGenerator
from RedisCursor import RedisCursor

from TimeTable import TimeTable
from abcManager import Manager
from DialogManager import DialogManager, Intent
from redis_utils.ServerMessage import ServerMessage, MessageType


class ContextManager(Manager):
    """
    Класс, ответственный за переключения между действиями
    Так же принимает Intent от DialogManager-а при реагирует на него
    """

    def __init__(self, tree, em_id, n_iterations=2000):
        super().__init__()
        self.n_iterations = n_iterations
        self.tree = tree
        self.stack: List[Action] = []
        self.finished_stack: List[Action] = []
        self.path: List[Node] = None
        self.current_path_idx: int = None
        self.dialog_manager = DialogManager(self)
        self.em_id = em_id

    def to_dict(self):
        conf = {
            'id': self.id,
            'n_iterations': self.n_iterations,
            'tree': self.tree.id,
            'stack': ' '.join([action.id for action in self.stack]),
            'finished_stack': ' '.join([action.id for action in self.finished_stack]),
            'path': ' '.join([node.id for node in self.path]),
            'current_path_idx': self.current_path_idx,
            'dialog_manager': self.dialog_manager.id,
            'em_id': self.em_id,
        }
        return conf

    def save_to_db(self):
        """
        Сохраняет в Redis:
            1) Свои параметры
            2) Параметры Actions из стэков
        :return:
        """
        dispatcher = RedisCursor()
        dispatcher.save_to_db(self.to_dict())

        self.tree.save_to_db()

        for action in self.stack:
            dispatcher.save_to_db(action.to_dict())
        for action in self.finished_stack:
            dispatcher.save_to_db(action.to_dict())

    def publish_timer_command(self, mssg: str):
        """
        Отправляет в MQ команды по таймерам
        TODO: Нормально ли то, что объект может публиковать в MQ?
        :param mssg:
        :return:
        """
        conn = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel: BlockingChannel = conn.channel()
        channel.queue_declare(queue='timer_command', durable=True)
        channel.basic_publish(exchange='',
                              routing_key='timer_command',
                              body=mssg,
                              properties=pika.BasicProperties(
                                  delivery_mode=2
                              ))
        conn.close()

    def publish_response(self, mssg: str, mssg_type: MessageType = MessageType.RESPONSE):
        """
        Отправляет ответы в MQ
        :param mssg_type:
        :param mssg:
        :return:
        """
        conn = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel: BlockingChannel = conn.channel()
        channel.queue_declare(queue='response_queue', durable=True)
        channel.basic_publish(exchange='',
                              routing_key='response_queue',
                              body='\t'.join([self.em_id, mssg_type.name, mssg]),
                              properties=pika.BasicProperties(
                                  delivery_mode=2
                              ))
        conn.close()

    def on_incoming_timer_event_callback(self, mssg: ServerMessage):
        assert mssg.em_id == self.em_id
        assert mssg.mssg_type == MessageType.TIMER
        action = self.action_by_timer_id(mssg.request[0][0])
        assert action is not None
        self.on_timer_elapsed(action)

    def action_by_timer_id(self, timer_id) -> Optional[Action]:
        """
        Ищет дейтсвие с заданным timer_id в стэках
        :param timer_id:
        :return:
        """
        for action in self.finished_stack:
            if action.timer_id == timer_id:
                return action
        for action in self.stack:
            if action.timer_id == timer_id:
                return action
        return None

    def initialize(self):
        """
        Должно вызываться сразу после создания объекта класса
        :return:
        """
        self.path = self.tree.mm_path(n_iterations=2000)
        time = TimeTable(self.tree.requirements())(self.path).time()
        resp = PhraseGenerator.speak("calculated.time", time=time)
        self.publish_response(resp)
        self.current_path_idx = 0
        self.stack.append(Action(self.path[self.current_path_idx], self))
        self.handle_top_action()

    def handle_intent(self, intent: Intent, params=None):
        """
        Обработчик интентов
        :param params:
        :param intent:
        :return:
        """
        if intent == Intent.NEXT_SIMPLE:
            self.handle_next_response()
        elif intent == Intent.REPEAT:
            self.handle_repeat_response()
        elif intent == Intent.CHOOSE_NEXT:
            self.handle_choosing_next()
        elif intent == Intent.CHANGE_NEXT:
            self.handle_changing_next(params)
        elif intent == Intent.NEGATIVE_SIMPLE:
            self.handle_negative()

    def handle_top_action(self):
        """
        Вызывается для обработки несовершенного действия на вершине стэка
        :return:

        """
        try:
            top_action = self.stack[-1]
            if top_action.node() == self.path[-1]:
                self.finished = True
        except IndexError:
            return

        # Проверка, что предшествующие технические действия выполнены
        # prev_action = self.last_waiting_action(top_action)
        # assert prev_action is None

        # Выдается реплика действия
        top_action.speak()

        # Запускается или возобновляется таймер действия
        if top_action.paused:
            top_action.unpause()
        else:
            top_action.start()

        # переход к следующему действию или ожидание ответа от человека
        if top_action.is_technical():
            # print()
            # self.publish_response("\n")
            self.handle_next_response()
        else:
            self.wait_for_response()

    def handle_next_response(self):
        if self.finished:
            resp = PhraseGenerator.speak("end")
            self.publish_response(resp)
            self.publish_response(mssg="", mssg_type=MessageType.FINISH)
            self.stop()
            return
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
                resp = PhraseGenerator.speak("stop.waiting", queue_name=return_to.queue_name())
                self.publish_response(resp)
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
                    if next_action.queue_name() != top_action.queue_name():
                        self.publish_response(PhraseGenerator.speak("switch.queue",
                                                                    queue_name=next_action.queue_name()))
                    self.stack.append(next_action)
                else:
                    # Если следующему действию предшествует незавершенное техническое действие
                    # Пытаемся переключиться на другое действие
                    node_switch_to = self.try_to_switch(prev_action)
                    if node_switch_to is None:
                        # Если переключиться некуда, остается ждать завершения технического действия,
                        # сдвинуть current_index на 1 назад и может быть ждать ответа
                        self.current_path_idx -= 1
                        self.publish_response(PhraseGenerator.speak("wait.technical",
                                                                    action=prev_action.node().name))
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

    def node_finished(self, node):
        # Проверяет, что действие есть в завершенном стэке и оно остановлено
        for action in self.finished_stack:
            if action.node() == node and action.elapsed:
                return True
        return False

    def try_to_switch(self, prev_action) -> Optional[Node]:
        """
        Пытается найти действие, которое можно выполнить раньше next_action с учетом его длительности
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

        # time = prev_action.timer.time_left()
        # time_diff = [abs(time - datetime.timedelta(seconds=node.time)) for node in possible_moves]
        # chosen_node = possible_moves[time_diff.index(min(time_diff))]
        chosen_node = random.sample(possible_moves, 1)[0]
        return chosen_node

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
                    and not action.elapsed \
                    and action in top_action.child_actions():
                prev_action = action
                break
        return prev_action

    def wait_for_response(self):
        """
        Ожидание реплики со стороны клиента
        :return:
        """
        # print("...")
        self.publish_response("...")

    def remind(self, action):
        if not action.is_technical():
            action.remind()
            self.wait_for_response()
        else:
            # print("НАПОМИНАНИЕ:", action.node().name)
            self.publish_response("НАПОМИНАНИЕ:" + action.node.name + '\n...')

    def handle_repeat_response(self, *args, **kargs):
        """
        Интент повторения реплики текущего действия
        :return:
        """
        try:
            top_action = self.stack[-1]
            top_action.speak()
        except IndexError:
            pass
        self.wait_for_response()

    def handle_choosing_next(self):
        """
        Интент смены предлагаемого действия
        :return:
        """
        if len(self.stack) == 0:
            self.wait_for_response()
            return
        self.stack[-1].pause()
        possible_moves = []
        # Проходим по всем действиям, не попавшим в stack и finished_stack
        for node in self.path[self.current_path_idx + 1:]:
            if len(node.inp) == 0 or all(self.node_finished(x) for x in node.inp):
                possible_moves.append(node)

        if len(possible_moves) == 0:
            self.publish_response(PhraseGenerator.speak("nowhere.to.switch"))
            self.wait_for_response()
            return
        self.publish_response(PhraseGenerator.speak("choose.next", options=", ".join(str(x) for x in possible_moves)))
        # Создаем форму с параметрами - названиями узлов, в которые можно перейти
        self.dialog_manager.push(ContextUnit(repr(possible_moves), unit_type=UnitType.CHOICE,
                                             params=[str(x) for x in possible_moves]))
        self.wait_for_response()

    def handle_changing_next(self, node_name):
        top_action = self.stack[-1]
        if node_name is None:
            if top_action.paused:
                top_action.restart()
            self.wait_for_response()
            return
        node_to_change = [x for x in self.path[self.current_path_idx + 1:] if x.name == node_name][0]
        temp = self.path[:self.current_path_idx] + [node_to_change]
        new_path = self.tree.mm_path(start=temp, n_iterations=2000)

        print("old path:")
        print(self.path)
        print("new path:")
        print(new_path, end='\n\n')

        time = TimeTable(self.tree.requirements())(new_path).time()
        self.publish_response(PhraseGenerator.speak("calculated.time", time=time))
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

    def handle_timeout_response(self, action: Action):
        """
        Обработчик таймаута у текущего действия
        :return:
        """
        if not action.is_technical() or len(action.out().inp) > 1:
            # TODO: непонятный момент
            action.stop()
            action.stop_children()
            self.remind(action)
        elif action.is_technical() and len(action.out().inp) == 1:
            try:
                current_action = self.stack[-1]
            except IndexError:
                # Если стэк был пустым, значит мы ждали завершения технического действия
                self.current_path_idx += 1
                current_action = Action(self.path[self.current_path_idx], self)
                self.stack.append(current_action)
                self.handle_top_action()
                return
            if action.queue_name() != current_action.queue_name():
                # Ставим в стэк над приостановленным действием следующее и меняем их порядок в self.path
                current_action.pause()
                current_action.stop_children()
                # print()
                self.publish_response("\n")
                self.publish_response(PhraseGenerator.speak("stop.and.switch", action=action.node().name))
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

    def on_action_spoken(self, unit):
        """
        Когда действие произнесло фразу, добавляем ее в стэк диалог менеджера
        :param unit:
        :return:
        """
        self.dialog_manager.push(unit)

    def handle_negative(self):
        self.publish_response(PhraseGenerator.speak("wait.confirmation"))
        self.wait_for_response()

    def stop(self):
        """
        Останваливает свою работу
        :return:
        """
        self.dialog_manager.stop()
