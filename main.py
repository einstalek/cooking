from TimeTable import TimeTable
from Tree import Node, Tree
from DialogManager import DialogManager
import time


def fastest_path(tree, start_path=None, n_iterations=1000):
    requirements = tree.requirements()
    min_path, min_time, min_table = None, 110, None
    for i in range(n_iterations):
        path = tree.path(start_path)
        table = TimeTable(requirements, 200)(path)
        if table.time() < min_time:
            min_time = table.time()
            min_path = path
            min_table = table
    return min_path, min_table


if __name__ == '__main__':
    clean_pepper = Node("clean pepper", 5, ["h"])
    mince_pepper = Node("mince pepper", 7, ["h"])(clean_pepper)
    grate_cheese = Node("grate cheese", 8, ["h"])
    mix_meat = Node("mix meat with pepper", 7, ["h"])(mince_pepper, grate_cheese)
    lay_tray = Node("lay tray", 4, ["h"])(mix_meat)
    put_on_tray = Node("put meat on tray", 10, ["h"])(lay_tray)

    turn_on_oven = Node("turn on oven", 2, ["h", "o"], False)
    wait_oven_warming = Node("waiting oven", 15, ["o"])(turn_on_oven)
    put_in_oven = Node("put meat into oven", 3, ["h", "o"], False)(wait_oven_warming, put_on_tray)
    bake = Node("bake meat", 20, ["o"], technical=True)(put_in_oven)
    take_out_meat = Node("take out meat", 5, ["h", "o"])(bake)

    clean_pot = Node("clean potato", 7, ["h"])
    mince_pot = Node("mince potato", 8, ["h"])(clean_pot)
    put_in_water = Node("put potato into pan with water", 3, ["h", "p"], False)(mince_pot)
    boil = Node("boil potato", 20, ["s", "p"], technical=True)(put_in_water)
    take_out_pot = Node("take out potato", 5, ["h", "p", "s"])(boil)
    squash = Node("squash potato", 5, ["h", "p"])(take_out_pot)

    mix_flour = Node("mix flour", 4, ["h", "s", "f"], False)
    add_cream = Node("add cream", 3, ["h", "s", "f"])(mix_flour)

    final = Node("final", 5)(take_out_meat, squash, add_cream)
    tree = Tree(final, switch_proba=0.5)
    tree.assign_queue_names(["meat", "puree", "sauce"])

    # t1 = time.time()
    # pop, mean_err = tree.evolve(count=100, epochs=300, mutate=0.1)
    # print("OVERALL TIME:", time.time() - t1)
    # best = tree.select(pop)[0]
    # print(best)
    # print(tree.fitness(best))
    # with open("error.txt", "w") as f:
    #     for x in mean_err:
    #         f.write("%.5f\n" % x)
    # table = TimeTable(tree.requirements())(best)
    # print('time:', table.time())

    dm = DialogManager(tree)
    dm.initialize()
