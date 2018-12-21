from Tree import Tree
from ContextManager import ContextManager
from recipes import cutlets_puree


if __name__ == '__main__':
    final = cutlets_puree.final
    tree = Tree(final, switch_proba=0.5)
    tree.assign_queue_names(["котлеты", "пюре", "соус"])

    cm = ContextManager(tree)
    cm.initialize()
