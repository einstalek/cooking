from TimeTable import TimeTable
from Tree import Node, Tree
from ContextManager import ContextManager
from Ingredient import Ingredient


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
    clean_pepper = Node("clean pepper", 5, ["h"], file="clean.yaml",
                        inp_ingredients=["болгарский перец"],
                        out_ingredient="помытый болгарский перец"
                        )
    mince_pepper = Node("mince pepper", 7, ["h"], file="mince.yaml",
                        out_ingredient="нарезанный перец",
                        how="на кольца"
                        )(clean_pepper)
    grate_cheese = Node("grate cheese", 8, ["h"], file="grate.yaml",
                        inp_ingredients=["сыр"],
                        out_ingredient="натертый сыр"
                        )
    mix_meat = Node("mix meat with pepper", 7, ["h"], file="mix.yaml",
                    out_ingredient="смесь из фарша"
                    )(mince_pepper, grate_cheese)
    lay_tray = Node("lay tray", 4, ["h"], file="lay_tray.yaml",
                    out_ingredient="котлеты"
                    )(mix_meat)
    put_on_tray = Node("put meat on tray", 10, ["h"], file="put_on_tray.yaml"
                       )(lay_tray)

    turn_on_oven = Node("turn on oven", 2, ["h", "o"], False, file="turn_on_oven.yaml",
                        regime="верхний нагрев")
    wait_oven_warming = Node("waiting oven", 15, ["o"], file="waiting.yaml",
                             what="нагрев духовки"
                             )(turn_on_oven)
    put_in_oven = Node("put meat into oven", 3, ["h", "o"], False, file="put.yaml",
                       what="противень с котлетами",
                       where="духовка",
                       out_ingredient="котлеты"
                       )(wait_oven_warming, put_on_tray)
    bake = Node("bake meat", 20, ["o"], technical=True, file="bake.yaml",
                out_ingredient="запеченые котлеты"
                )(put_in_oven)
    take_out_meat = Node("take out meat", 5, ["h", "o"], file="take_out.yaml",
                         where="из духовки",
                         )(bake)

    clean_pot = Node("clean potato", 7, ["h"], file="clean.yaml",
                     inp_ingredients=["картошка"],
                     out_ingredient="помытая картошка")
    mince_pot = Node("mince potato", 8, ["h"], file="mince.yaml",
                     out_ingredient="нарезанная картошка",
                     how="на кубики по 1 см"
                     )(clean_pot)
    put_in_water = Node("put potato into pan with water", 3, ["h", "p"], False, file="put_in_pan.yaml",
                        out_ingredient="картошка"
                        )(mince_pot)
    boil = Node("boil potato", 20, ["s", "p"], technical=True, file="boil.yaml",
                out_ingredient="картошка"
                )(put_in_water)
    take_out_pot = Node("take out potato", 5, ["h", "p", "s"], file="take_out.yaml",
                        out_ingredient="вареная картошка",
                        where="из кастрюли"
                        )(boil)
    squash = Node("squash potato", 5, ["h", "p"],  file="squash.yaml",
                  out_ingredient="пюре"
                  )(take_out_pot)

    mix_flour = Node("mix flour", 4, ["h", "s", "f"], False, file="mix_flour.yaml"
                     )
    add_cream = Node("add cream", 3, ["h", "s", "f"], file="add_cream.yaml"
                     )(mix_flour)

    final = Node("final", 5)(take_out_meat, squash, add_cream)
    tree = Tree(final, switch_proba=0.5)
    tree.assign_queue_names(["meat", "puree", "sauce"])

    cm = ContextManager(tree)
    cm.initialize()

