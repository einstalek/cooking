import datetime
import random
from typing import List, Optional

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika import exceptions as pika_exceptions

import custom_exceptions
from action import Action
from context_unit import ContextUnit, UnitType
from intent_parser import Intent
from node import Node
from text_utils.phrase_generator import PhraseGenerator
from redis_cursor import RedisCursor

from time_table import TimeTable
from abc_manager import Manager
from dialog_manager import DialogManager
from server_message import MessageType


class ContextManager(Manager):
    """
    Класс, ответственный за переключения между действиями
    Так же принимает Intent от DialogManager-а при реагирует на него
    """

    def __init__(self, tree, em_id, n_iterations=100):
        """
        WARNING: добавляя новое поле, его нужно добавить в to_dict и в Restorer
        :param tree:
        :param em_id:
        :param n_iterations:
        """
        super().__init__()
        self.n_iterations = n_iterations
        self.tree = tree
        self.stack: List[Action] = []
        self.finished_stack: List[Action] = []
        self.path: List[Node] = None
        self.current_path_idx: int = None
        self.dialog_manager = DialogManager(self)
        self.em_id = em_id
        self.finished = False
        self.queues_visited = set()
        self.server = None

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
            'finished': str(self.finished),
            'queues_visited': '>'.join(self.queues_visited) if len(self.queues_visited) > 0 else ''
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

    def publish_response(self, mssg: str, mssg_type: MessageType = MessageType.RESPONSE):
        """
        Отправляет ответы в MQ
        :param mssg_type:
        :param mssg:
        :return:
        """
        try:
            conn = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        except pika_exceptions.ConnectionClosed:
            raise custom_exceptions.MqConnectionError

        self.log("PUBLISHING RESPONSE", mssg)
        channel: BlockingChannel = conn.channel()
        channel.queue_declare(queue='response_queue', durable=True)
        channel.basic_publish(exchange='',
                              routing_key='response_queue',
                              body='\t'.join([self.em_id, mssg_type.name, mssg]),
                              properties=pika.BasicProperties(
                                  delivery_mode=2
                              ))
        conn.close()

    def on_incoming_timer_event_callback(self, em_id, timer_id):
        assert em_id == self.em_id
        action = self.action_by_timer_id(timer_id)
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
        self.path = self.tree.mm_path(n_iterations=100)
        time = TimeTable(self.tree.requirements())(self.path).time()
        resp = PhraseGenerator.speak("overview",
                                     queue_names=', '.join(self.tree.queue_names),
                                     number=len(self.tree.queue_names))
        resp += "\n" + PhraseGenerator.speak("calculated.time", time=time // 60)
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
        prev_action = self.last_waiting_action(top_action)
        if prev_action is not None:
            mssg = "trying to execute", top_action, "while", prev_action, "is not finished"
            self.log(mssg)
            prev_action.stop()
            prev_action.stop_children()

        # Если к ветке приступили только что, озвучиваем ее входные ингридиенты
        # TODO: Fix this
        resp = None
        if top_action.queue_name() not in self.queues_visited:
            self.queues_visited.add(top_action.queue_name())
            requirements = ', '.join([str(x) for x in self.tree.queue_ingredients(top_action.queue_name())])
            resp = PhraseGenerator.speak("start.new.queue",
                                         queue_name=top_action.queue_name(),
                                         requirements=requirements,
                                         )

        top_action.speak(add=resp)

        # Запускается или возобновляется таймер действия
        if top_action.paused:
            top_action.unpause()
        else:
            top_action.start()

        # переход к следующему действию или ожидание ответа от человека
        if top_action.is_technical():
            resp = PhraseGenerator.speak("started.timer",
                                         time=top_action.secs // 60)
            self.publish_response(resp)
            self.handle_next_response()
        else:
            pass

    def handle_next_response(self):
        if self.finished:
            resp = PhraseGenerator.speak("end")
            self.publish_response(resp)
            self.publish_response(mssg="", mssg_type=MessageType.FINISH)
            return
        try:
            top_action = self.stack[-1]
        except IndexError:
            if len(self.path) == self.current_path_idx:
                pass
            else:
                # Узлы обошли не все, но когда человек дал команду 'дальше', стэк был пустой
                # потому, что было ожидание какого-то технического действия
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
                temp_node = self.path[self.current_path_idx]
                next_action = Action(temp_node, self)
                prev_action = self.last_waiting_action(next_action)
                if prev_action is None:
                    # Если все нормально, двигаемся дальше по path
                    if next_action.queue_name() != top_action.queue_name():
                        self.publish_response(PhraseGenerator.speak("switch.queue",
                                                                    queue_name=next_action.queue_name()))
                    self.stack.append(next_action)
                else:
                    temp_node.parent = None
                    # Если следующему действию предшествует незавершенное техническое действие
                    # Пытаемся переключиться на другое действие
                    node_switch_to = self.try_to_switch(prev_action)
                    if node_switch_to is None:
                        # Если переключиться некуда, остается ждать завершения технического действия,
                        # сдвинуть current_index на 1 назад и может быть ждать ответа
                        self.current_path_idx -= 1
                        self.publish_response(PhraseGenerator.speak("wait.technical",
                                                                    action=prev_action.node().name))
                        return
                    else:
                        # Если есть куда перейти, пересчтываем path и добавляем другое действие на верх стэка
                        self.path = self.tree.mm_path(start=self.path[:self.current_path_idx] + [node_switch_to],
                                                      n_iterations=100)
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

        # выбираем случайный из возможных узлов для перехода
        time_dist = self.tree.time_queue_dist()
        node_priority = {node: time_dist[node.queue_name] for node in possible_moves}
        possible_moves = [node for node in possible_moves if node_priority[node] == max(node_priority.values())]
        chosen_node = random.sample(possible_moves, 1)[0]
        return chosen_node

    def last_waiting_action(self, top_action) -> Optional[Action]:
        """
        Если в finished_stack есть незавершенное техническое действие
        которое предшествует top_action, то вернет его
        :param top_action:
        :return:
        """
        # TODO: нужна ли проверка на паузу
        prev_action = None
        for action in self.finished_stack:
            if top_action.queue_name() == action.queue_name() \
                    and not action.elapsed \
                    and not action.paused \
                    and action in top_action.child_actions():
                prev_action = action
                break
        return prev_action

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

    def handle_choosing_next(self):
        """
        Интент смены предлагаемого действия
        :return:
        """
        if len(self.stack) == 0:
            return
        self.stack[-1].pause()
        possible_moves = []
        # Проходим по всем действиям, не попавшим в stack и finished_stack
        for node in self.path[self.current_path_idx + 1:]:
            if len(node.inp) == 0 or all(self.node_finished(x) for x in node.inp):
                possible_moves.append(node)

        if len(possible_moves) == 0:
            self.publish_response(PhraseGenerator.speak("nowhere.to.switch"))
            return

        queues = set([node.queue_name for node in possible_moves])
        self.publish_response(PhraseGenerator.speak("choose.next", options=", ".join(str(x) for x in queues)))
        # Создаем форму с параметрами - названиями очередей, в которые можно перейти
        self.dialog_manager.push(ContextUnit(repr(queues), unit_type=UnitType.CHOICE,
                                             params=[str(x) for x in queues]))

    def handle_changing_next(self, queue_name):
        top_action = self.stack[-1]
        if queue_name is None:
            if top_action.paused:
                top_action.restart()
            return

        # Проходим по всем действиям, не попавшим в stack и finished_stack
        possible_moves = []
        for node in self.path[self.current_path_idx + 1:]:
            if (len(node.inp) == 0 or all(self.node_finished(x) for x in node.inp)) \
                    and node.queue_name == queue_name:
                possible_moves.append(node)

        node_to_change = random.sample([x for x in possible_moves], 1)[0]

        temp = self.path[:self.current_path_idx] + [node_to_change]
        new_path = self.tree.mm_path(start=temp, n_iterations=100)
        time = TimeTable(self.tree.requirements())(self.path).time()
        recalculated_time = TimeTable(self.tree.requirements())(new_path).time()
        time_diff = recalculated_time - time
        if time_diff > 0:
            self.publish_response(PhraseGenerator.speak("recalculated.time.more", time_diff=time_diff // 60))
        elif time_diff < 0:
            self.publish_response(PhraseGenerator.speak("recalculated.time.less", time_diff=time_diff // 60))
        else:
            self.publish_response(PhraseGenerator.speak("recalculated.time.eq"))

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
            # Действие вроде техническое, но сразу переходить после него не обязательно
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
                current_action.stop_children()
                PhraseGenerator.speak("stop.waiting", queue_name=action.queue_name())
                self.handle_top_action()
                return
            if action.queue_name() != current_action.queue_name():
                # Ставим в стэк над приостановленным действием следующее и меняем их порядок в self.path
                # TODO: обработать неразрывные действия
                current_action.pause()
                current_action.stop_children()
                self.publish_response("\n\n" + PhraseGenerator.speak("stop.and.switch", action=action.node().name))
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

    def remind(self, action):
        if not action.is_technical():
            action.remind()
        else:
            self.publish_response("НАПОМИНАНИЕ: " + action.node.name)

    def on_action_spoken(self, unit):
        """
        Когда действие произнесло фразу, добавляем ее в стэк диалог менеджера
        :param unit:
        :return:
        """
        self.dialog_manager.push(unit)

    def handle_negative(self):
        self.publish_response(PhraseGenerator.speak("wait.confirmation"))

    def stop(self):
        """
        Останваливает свою работу
        :return:
        """
        self.dialog_manager.stop()

    @staticmethod
    def log(*args):
        print(datetime.datetime.now(), ":", *args)
