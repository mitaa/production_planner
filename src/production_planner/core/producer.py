# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .recipe import Recipe

import json
from collections import OrderedDict


PRODUCERS = []
PRODUCER_NAMES = []
PRODUCER_MAP = {}

PRODUCER_ALIASES = {
    "Coal Generator": ["Coal-Powered Generator"],
    "Fuel Generator": ["Fuel-Powered Generator"],
    "Coal-Powered Generator": ["Coal Generator"],
    "Fuel-Powered Generator": ["Fuel Generator"],
}


class Producer:
    def __init__(self, name, *, is_miner, is_pow_gen, max_mk, base_power, recipes, description, is_abstract=False, is_primary=True):
        self.is_abstract = is_abstract
        self.is_primary = is_primary
        self.name = name
        self.is_miner = is_miner
        self.is_pow_gen = is_pow_gen
        self.max_mk = max_mk
        self.base_power = base_power
        self.description = description
        self.recipes = [Recipe(k, v[0], v[1], v[2]) for k, v in recipes.items()]

    @property
    def recipes(self):
        return self._recipes

    @recipes.setter
    def recipes(self, value):
        self._recipes = value
        self.update_recipe_map()

    def update_recipe_map(self):
        self.recipe_map = {}
        for recipe in self.recipes:
            self.recipe_map[recipe.name] = recipe
            if self.is_primary:
                recipe.recipe_to_producer_map[recipe] = self

    def __str__(self):
        if self.is_abstract:
            return f"<{self.name}>"
        else:
            return self.name

    def __repr__(self):
        return f"<Producer: {self.name}, recipes: {self.recipes}>"

    @property
    def is_module(self):
        return False


class Producers:
    def __init__(self):
        self.ingredients = set()
        self.producers = []
        self.output_ingredient_indices = Indexer()
        self.input_ingredient_indices = Indexer()
        self.output_ingredient_producers = Indexer()
        self.input_ingredient_producers = Indexer()
        self.output_ingredient_recipes = Indexer()
        self.input_ingredient_recipes = Indexer()
        self.recipe_indices = Indexer()

    def add(self, producer):
        for recip in producer.recipes:
            self.recipe_indices.add(recip.name, len(self.producers))
            for ingredient in recip.inputs:
                self.ingredients.add(ingredient.name)
                self.input_ingredient_indices.add(ingredient.name, len(self.producers))
                self.input_ingredient_producers.add(ingredient.name, producer.name)
                self.input_ingredient_recipes.add(ingredient.name, recip.name)

            for ingredient in recip.outputs:
                self.ingredients.add(ingredient.name)
                self.output_ingredient_indices.add(ingredient.name, len(self.producers))
                self.output_ingredient_producers.add(ingredient.name, producer.name)
                self.output_ingredient_recipes.add(ingredient.name, recip.name)
        self.producers += [producer]


class Indexer:
    def __init__(self):
        self.index = {}

    def add(self, k, v):
        self.index.setdefault(k, set())
        self.index[k].add(v)


EMPTY_PRODUCER = Producer(
    "",
    is_abstract=False,
    is_miner=False,
    is_pow_gen=False,
    max_mk=0,
    base_power=0,
    recipes={"":     [60, [], []], },
    description="",
)

SUMMARY_PRODUCER = Producer(
    "Summary",
    is_abstract=False,
    is_miner=False,
    is_pow_gen=False,
    max_mk=0,
    base_power=0,
    recipes={"":     [60, [], []], },
    description="",
)

# FIXME: file structure ?
from .module import MODULE_PRODUCER
PRODUCERS += [MODULE_PRODUCER]


def all_recipes_producer():
    recip_names = set()
    recipes = {}
    for producer in PRODUCERS:
        producer_recipe_map = dict({r.name: r for r in producer.recipes if r.name})
        if producer.is_module:
            continue
        duplicates = recip_names & set(producer_recipe_map.keys())
        # if duplicates:
        #     APP.notify(str(duplicates))
        recipes.update(producer_recipe_map)

    prod = Producer(
        "<ALL RECIPES>",
        is_abstract=True,
        is_primary=False,
        is_miner=False,
        is_pow_gen=False,
        max_mk=0,
        base_power=0,
        recipes={},
        description="",
    )
    prod.recipes = list(sorted(recipes.values(), key=lambda r: r.name))
    return prod


class ProducerEncoder(json.JSONEncoder):
    def default(self, producer):
        if isinstance(producer, Producer):
            recipes = OrderedDict()
            for recipe in producer.recipes:
                recipes.update(recipe.to_json_schema())

            return {
                producer.name: {
                    "description": producer.description,
                    "is_miner": producer.is_miner,
                    "is_pow_gen": producer.is_pow_gen,
                    "max_mk": producer.max_mk,
                    "base_power": producer.base_power,
                    "recipes": recipes,
                }
            }
        # Let the base class default method raise the TypeError
        return super().default(producer)
