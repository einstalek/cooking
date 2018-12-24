from ContextManager import ContextManager
from Restorer import Restorer
from recipes import cutlets_puree
from RedisCursor import RedisCursor


if __name__ == '__main__':
    cursor = RedisCursor()

    # final = cutlets_puree.final
    # tree = Tree(final, switch_proba=0.5)
    # tree.assign_queue_names(["котлеты", "пюре", "соус"])
    # tree.save_to_db()

    tree_id = list(cursor.conn().scan_iter("T*"))[0].decode()
    restored_tree = Restorer().restore_tree(tree_id)

    cm = ContextManager(restored_tree)
    path = restored_tree.mm_path(n_iterations=500)
    cm.initialize()
    cm.dialog_manager.run()
