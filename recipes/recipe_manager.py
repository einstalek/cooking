from base_structures.tree import Tree
from recipes import simple_recipe, cutlets_puree
import re


class RecipeManager:
    def __init__(self):
        self.recipes = [
            simple_recipe,
            cutlets_puree
        ]

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
    def activate(self, recipe):
        tree = Tree(recipe.final, 0.005)
        tree.assign_queue_names(recipe.queue_names)
        return tree


if __name__ == "__main__":
    recipe = RecipeManager().match("котлеты и бешамель")
    print(recipe.final)
