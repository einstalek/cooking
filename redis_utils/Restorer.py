from base_structures.Action import Action
from managers.ContextManager import ContextManager
from managers.ContextUnit import ContextUnit
from managers.DialogManager import DialogManager
from base_structures.Ingredient import Ingredient
from Node import Node
from redis_utils.RedisCursor import RedisCursor
from base_structures.Tree import Tree


class Restorer:
    def __init__(self):
        self.cursor = RedisCursor()

    def restore_tree(self, tree_id) -> Tree:
        """
        Восстанавливет дерево по tree_id
        :param tree_id:
        :return:
        """
        head_id = self.cursor.get(tree_id)['head']
        __obj = {}

        def read_children_nodes(node_id):
            """
            Реккурсивно восстанавливает узлы и ингридиенты в дереве
            :param node_id:
            :return:
            """
            node = Node.from_dict(self.cursor.get(node_id))
            node_inp_ids = self.cursor.get(node_id)['inp'].split()
            # Преобразование корня дерева
            if node_id not in __obj:
                __obj[node_id] = node
                # поле inp_ingredients корня
                if node.inp_ingredients:
                    inp_ingredients = []
                    for ingr_id in node.inp_ingredients:
                        ingr = Ingredient.from_dict(self.cursor.get(ingr_id))
                        inp_ingredients.append(ingr)
                        __obj[ingr_id] = ingr
                    node.inp_ingredients = inp_ingredients
            for inp_id in node_inp_ids:
                child = Node.from_dict(self.cursor.get(inp_id))
                # Заменяем out_ingredient на объект класса Ingredient
                if child.out_ingredient:
                    ingr = Ingredient.from_dict(self.cursor.get(child.out_ingredient))
                    child.out_ingredient = ingr
                    __obj[ingr.id] = ingr
                # Заменяем inp_ingredients на объекты класса Ingredient
                if child.inp_ingredients:
                    inp_ingredients = []
                    for ingr_id in child.inp_ingredients:
                        ingr = Ingredient.from_dict(self.cursor.get(ingr_id))
                        inp_ingredients.append(ingr)
                        __obj[ingr_id] = ingr
                    child.inp_ingredients = inp_ingredients
                __obj[inp_id] = child
                read_children_nodes(inp_id)

        def fix_links(head_id):
            """
            Реккурсивно восстанавливает ссылки между узлами в дереве
            :param head_id:
            :return:
            """
            head = __obj[head_id]
            for child_id in head.inp:
                child = __obj[child_id]
                head.inp = [x for x in head.inp if x != child_id]
                head.inp.append(child)
                child.out = head
                fix_links(child_id)

        read_children_nodes(head_id)
        fix_links(head_id)

        final = __obj[head_id]
        tree = Tree.from_dict(self.cursor.get(tree_id))
        tree.head = final

        return tree

    def restore_context_manager(self, cm_id):
        cm_params = self.cursor.get(cm_id)
        tree_id = cm_params['tree']
        tree = self.restore_tree(tree_id)

        em_id = cm_params['em_id']
        cm = ContextManager(tree, em_id, int(cm_params['n_iterations']))
        cm.id = cm_params['id']

        cm.path = []
        for node_id in cm_params['path'].split():
            cm.path.append([node for node in tree.nodes() if node.id == node_id][0])
        cm.current_path_idx = int(cm_params['current_path_idx'])

        # воссоздаем stack
        stack_ids = cm_params['stack'].split()
        finished_stack_ids = cm_params['finished_stack'].split()

        stack, finished_stack = [], []
        for _id in stack_ids:
            action = Action.from_dict(self.cursor.get(_id))
            action.cm = cm
            node = [node for node in cm.path if node.id == action.node][0]
            action.node = node
            action.secs = node.time
            action.timer_name = node.name
            node.parent = action
            stack.append(action)

        for _id in finished_stack_ids:
            action = Action.from_dict(self.cursor.get(_id))
            action.cm = cm
            node = [node for node in cm.path if node.id == action.node][0]
            action.node = node
            action.secs = node.time
            action.timer_name = node.name
            node.parent = action
            finished_stack.append(action)

        cm.stack = stack
        cm.finished_stack = finished_stack

        # проверяем, что в поле parent не осталось строк
        for node in cm.tree.nodes():
            if node.parent and isinstance(node.parent, str):
                try:
                    action = Action.from_dict(self.cursor.get(node.parent))
                except KeyError:
                    print(node.parent, node)
                    raise KeyError
                action.cm = cm
                action.node = node
                action.secs = node.time
                action.timer_name = node.name
                node.parent = action
        return cm

    def restore_dialog_manager(self, dm_id):
        """
        Восстанавливает DialogManager и его ContextManager
        :param dm_id:
        :return:
        """
        dm_params = self.cursor.get(dm_id)
        try:
            cm = self.restore_context_manager(dm_params['context_manager'])
        except KeyError:
            print(dm_params)
            raise KeyError
        dm = DialogManager(cm)
        dm.id = dm_params['id']

        stack_ids = dm_params['stack'].split()
        stack = []
        for _id in stack_ids:
            cu = ContextUnit.from_dict(self.cursor.get(_id))
            stack.append(cu)

        dm.stack = stack
        dm.context_manager = cm
        cm.dialog_manager = dm
        return dm

