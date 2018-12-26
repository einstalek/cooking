from ContextManager import ContextManager
from Ingredient import Ingredient
from Node import Node
from RedisCursor import RedisCursor
from Tree import Tree


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
        # TODO: разобраться с Actions
        cm_params = self.cursor.get(cm_id)
        tree_id = cm_params['tree']
        tree = self.restore_tree(tree_id)
        cm = ContextManager(tree, int(cm_params['n_iterations']))
        cm.id = cm_params['id']
        cm.path = []
        for node_id in cm_params['path'].split():
            cm.path.append([node for node in tree.nodes() if node.id == node_id][0])
        cm.current_path_idx = int(cm_params['current_path_idx'])
        return cm

    def restore_action(self):
        return None
