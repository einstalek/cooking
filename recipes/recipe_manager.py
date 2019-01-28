from tree import Tree
from recipes import eggs_tmin, cutlets_puree
import re


class RecipeManager:
    def __init__(self, *recipes):
        self.recipes = recipes

    def match(self, request: str):
        counts = {}
        for recipe in self.recipes:
            keywords = re.split("\W", recipe.final.name)
            words = re.split("\W", request)
            counts[recipe] = sum([w in keywords for w in words])

        if all(counts[k] == 0 for k in counts):
            return None
        return [k for k in counts if counts[k] == max(counts.values())][0]

    @staticmethod
    def activate(recipe):
        tree = Tree(recipe.final, 0.005)
        tree.assign_queue_names(recipe.queue_names)
        return tree


if __name__ == "__main__":
    manager = RecipeManager(eggs_tmin, cutlets_puree)
    recipe = manager.match("котлеты и бешамель")
    tree = Tree(recipe.final, 0.01)
    tree.assign_queue_names(recipe.queue_names)
    print(tree.random_path())
