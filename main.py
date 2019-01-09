from threading import Thread

from ContextManager import ContextManager
from Restorer import Restorer
from Tree import Tree
from recipes import cutlets_puree
from RedisCursor import RedisCursor
from redis_utils.HardwareEmulator import HardwareEmulator
from redis_utils.WebServer import WebServer

if __name__ == '__main__':
    cursor = RedisCursor()

    final = cutlets_puree.final
    tree = Tree(final, switch_proba=0.5)
    tree.assign_queue_names(["котлеты", "пюре", "соус"])
    # tree.save_to_db()

    # tree_id = list(cursor.conn().scan_iter("T*"))[0].decode()
    # restored_tree = Restorer().restore_tree(tree_id)

    cm = ContextManager(tree, em_id='E4P1AQZI86B')
    Thread(target=cm.on_incoming_timer_event).start()
    cm.initialize()
    cm.dialog_manager.run()
