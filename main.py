from managers.context_manager import ContextManager
from base_structures.tree import Tree
from recipes import cutlets_puree
from redis_utils.redis_cursor import RedisCursor

if __name__ == '__main__':
    cursor = RedisCursor()

    final = cutlets_puree.final
    tree = Tree(final, switch_proba=0.5)
    tree.assign_queue_names(["котлеты", "пюре", "соус"])
    # tree.save_to_db()

    # tree_id = list(cursor.conn().scan_iter("T*"))[0].decode()
    # restored_tree = Restorer().restore_tree(tree_id)

    cm = ContextManager(tree, em_id='E4P1AQZI86B')
    cm.initialize()
    # Thread(target=cm.start_consuming_timer_events).start()
    # cm.dialog_manager.run()


