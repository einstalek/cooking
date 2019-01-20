from base_structures.Node import Node

clean_eggs = Node("промывка куриных яиц", 5, ["h"], switchable=False, file="clean.yaml",
                  inp_ingredients=["куринце яйца"],
                  out_ingredient="помытые куриные яйца")

mince_eggs = Node("взбивка яиц", 10, ["h"], file="mince.yaml",
                  out_ingredient="взбитые яйца")(clean_eggs)

warm_pan = Node("нагреть сковороду", 20, ["o"], technical=True, file="turn_on_oven.yaml")

put_eggs_on_pan = Node("вылить яйца на сковороду", 5, ["h", "o", "p"], file="put_in_pan.yaml",
                       out_ingredient="омлет")(warm_pan, mince_eggs)

bake_eggs = Node("запекание яиц", 20, ["o", "p"], technical=True, file="bake.yaml",
                 out_ingredient="омлет")(put_eggs_on_pan)

take_out_eggs = Node("доставание омлета", 5, ["h", "o", "p"], file="take_out.yaml",
                     out_ingredient="омлет")(bake_eggs)

clean_tmin = Node("помыть тмин", 10, ["h"], file="clean.yaml",
                  out_ingredient="помытый тмин")
cut_tmin = Node("тмин", 10, ["h"], file="mince.yaml",
                out_ingredient="тмин")(clean_tmin)

final = Node("омлет", 5)(take_out_eggs, cut_tmin)


