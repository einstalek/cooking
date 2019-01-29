import string
from typing import List, Optional
from node import Node
from timer import Timer, TimerEvent, TimerMessage
from abc_manager import Manager
from context_unit import ContextUnit
import random
import re


class Action:
    def __init__(self, node: Optional[Node], cm: Optional[Manager]):
        self.id = 'A' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

        self.node = node
        self.timer_id = Timer.gen_id()
        if node is not None:
            node.parent = self
            self.secs = node.time
            self.timer_name = node.name
        self.cm = cm
        self.paused = None
        self.elapsed = False

    def to_dict(self):
        conf = {
            'id': self.id,
            'node': self.node.id,
            'timer_id': self.timer_id,
            'cm': self.cm.id,
            'paused': self.paused,
            'elapsed': self.elapsed,
        }
        return conf

    @staticmethod
    def from_dict(d):
        action = Action(node=None, cm=None)
        action.id = d['id']
        action.node = d['node']
        action.timer_id = d['timer_id']
        action.paused = True if d['paused'] == 'True' else False
        action.elapsed = True if d['elapsed'] == 'True' else False
        return action

    def timer_message(self, event: TimerEvent):
        return TimerMessage(self.timer_id, self.timer_name, self.secs, event)

    def inp(self) -> List[Node]:
        return self.node.inp

    def out(self) -> Node:
        return self.node.out

    def start(self):
        self.cm.server.on_timer_command(self.cm.em_id, self.timer_message(TimerEvent.START))

    def unpause(self):
        self.paused = False
        self.cm.server.on_timer_command(self.cm.em_id, self.timer_message(TimerEvent.UNPAUSE))

    def restart(self):
        self.cm.server.on_timer_command(self.cm.em_id, self.timer_message(TimerEvent.RESTART))

    def stop(self):
        if self.elapsed:
            return
        self.elapsed = True
        self.cm.server.on_timer_command(self.cm.em_id, self.timer_message(TimerEvent.STOP))

    def stop_children(self):
        for child in self.child_actions():
            child.stop()

    def pause(self):
        self.paused = True
        self.cm.server.on_timer_command(self.cm.em_id, self.timer_message(TimerEvent.PAUSE))

    def is_technical(self):
        return 'h' not in self.node.requirements

    def queue_name(self):
        return self.node.queue_name

    def child_actions(self):
        children = []

        def _get_children(action):
            for inp in action.inp():
                children.append(inp.parent)
                _get_children(inp.parent)

        _get_children(self)
        return children

    def __repr__(self):
        if self.node.file:
            return self.node.info["Name"]
        return self.node.name

    def __str__(self):
        return self.node.name + ' ' + self.id + ' ' + self.node.id

    def speak(self, add: str = None):
        if self.node.file is None:
            print(self.node.name)
        else:
            phrase = random.sample(self.node.info["Phrase"], 1)[0]
            warnings = self.node.info["Warning"]
            params = self.extract_params(phrase)
            reformatted = self.reformat(params, phrase)

            if warnings:
                warning = random.sample(warnings, 1)[0]
                reformatted += "\n" + warning

            if add:
                reformatted = add + '\n' + reformatted

            self.cm.publish_response(reformatted)
            self.cm.on_action_spoken(ContextUnit(reformatted, params))

    def remind(self):
        # TODO: напоминания не добавляются в стэк DM
        if self.node.file is None:
            self.cm.publish_response("isn't" + repr(self) + "done yet?")
        else:
            phrase = random.sample(self.node.info["Remind"], 1)[0]
            params = self.extract_params(phrase)
            self.cm.publish_response(self.reformat(params, phrase))

    @staticmethod
    def extract_params(phrase: str) -> List[str]:
        """
        Извлекает имена параметров из фразы
        :param phrase:
        :return:
        """
        search = re.findall("{\w*}", phrase)
        return [x[1:-1] for x in search]

    def reformat(self, params, phrase: str) -> str:
        """
        Для каждлого параметра из params берет значение из параметров, указанных в Node
        и вставляет их в phrase
        :param params:
        :param phrase:
        :return:
        """
        reformatted: str = phrase
        if "ingredients" in params and self.node().inp_ingredients:
            reformatted = reformatted.replace("{ingredients}", ", ".join([x.name for x in self.node().inp_ingredients]))
        if "time" in params:
            reformatted = reformatted.replace("{time}", str(self.node().time // 60))
        if self.node().params:
            for param in self.node().params:
                reformatted = reformatted.replace("{" + param + "}", self.node().params[param])
        return reformatted


