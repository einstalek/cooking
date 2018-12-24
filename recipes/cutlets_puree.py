from Node import Node


clean_pepper = Node("чистка перца", 5, ["h"], file="clean.yaml",
                        inp_ingredients=["болгарский перец"],
                        out_ingredient="помытый болгарский перец"
                        )

mince_pepper = Node("нарезание перца", 7, ["h"], file="mince.yaml",
                    out_ingredient="нарезанный перец",
                    how="на кольца"
                    )(clean_pepper)

grate_cheese = Node("натирание сыра", 8, ["h"], file="grate.yaml",
                    inp_ingredients=["сыр"],
                    out_ingredient="натертый сыр"
                    )

mix_meat = Node("смешать фарш с перцем и сыром", 7, ["h"], file="mix.yaml",
                out_ingredient="смесь из фарша"
                )(mince_pepper, grate_cheese)

lay_tray = Node("застилание поднос", 4, ["h"], file="lay_tray.yaml",
                out_ingredient="котлеты"
                )(mix_meat)

put_on_tray = Node("выкладывание на поднос", 10, ["h"], file="put_on_tray.yaml"
                   )(lay_tray)

turn_on_oven = Node("включение духовки", 3, ["h", "o"], switchable=False, file="turn_on_oven.yaml",
                    regime="верхний нагрев")

wait_oven_warming = Node("ожидание нагрева духовки", 15, ["o"], file="waiting.yaml",
                         what="нагрев духовки"
                         )(turn_on_oven)

put_in_oven = Node("отправление котлет в духовку", 3, ["h", "o"], switchable=False, file="put.yaml",
                   what="противень с котлетами",
                   where="духовка",
                   out_ingredient="котлеты"
                   )(wait_oven_warming, put_on_tray)

bake = Node("запекание котлет", 20, ["o"], technical=True, file="bake.yaml",
            out_ingredient="запеченые котлеты"
            )(put_in_oven)

take_out_meat = Node("вынимание котлет", 5, ["h", "o"], file="take_out.yaml",
                     where="из духовки",
                     )(bake)

clean_pot = Node("чистка картошки", 7, ["h"], file="clean.yaml",
                 inp_ingredients=["картошка"],
                 out_ingredient="помытая картошка")

mince_pot = Node("нарезание картошки", 8, ["h"], file="mince.yaml",
                 out_ingredient="нарезанная картошка",
                 how="на кубики по 1 см"
                 )(clean_pot)

put_in_water = Node("выкладывание картошки в кастрюлю", 3, ["h", "p"], switchable=False, file="put_in_pan.yaml",
                    out_ingredient="картошка"
                    )(mince_pot)

boil = Node("варка картошки", 20, ["s", "p"], technical=True, file="boil.yaml",
            out_ingredient="картошка"
            )(put_in_water)

take_out_pot = Node("вытаскивание картошки", 5, ["h", "p", "s"], file="take_out.yaml",
                    out_ingredient="вареная картошка",
                    where="из кастрюли"
                    )(boil)

squash = Node("толчение картошки", 5, ["h", "p"],  file="squash.yaml",
              out_ingredient="пюре"
              )(take_out_pot)

mix_flour = Node("перемешивание муки", 4, ["h", "s", "f"], switchable=False, file="mix_flour.yaml"
                 )

add_cream = Node("добавление сливок", 3, ["h", "s", "f"], file="add_cream.yaml"
                 )(mix_flour)

final = Node("final", 5)(take_out_meat, squash, add_cream)


