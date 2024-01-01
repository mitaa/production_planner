# -*- coding:utf-8 -*-

import os
import math
from enum import Enum
from dataclasses import dataclass
import json
from pathlib import Path

import yaml
import appdirs


DPATH_DATA = Path(appdirs.user_data_dir("satisfactory_production_planner", "mitaa"))


def get_path(obj, path):
    paths = path.split(".", maxsplit=1)
    primpath = paths[0]
    subpaths = paths[1:]
    if not subpaths:
        return getattr(obj, path)
    else:
        return get_path(getattr(obj, primpath), ".".join(subpaths))

def set_path(obj, path, value):
    paths = path.split(".", maxsplit=1)
    primpath = paths[0]
    subpaths = paths[1:]
    if not subpaths:
        return setattr(obj, path, value)
    else:
        return set_path(getattr(obj, primpath), subpaths, value)


@dataclass
class Ingredient:
    name: str
    count: int

    def __str__(self):
        return f"({self.count}x {self.name})"


class Recipe(yaml.YAMLObject):
    yaml_tag = u"!recipe"
    def __init__(self, name, cycle_rate, inputs, outputs):
        self.name = name
        self.cycle_rate = cycle_rate
        self.inputs = list(Ingredient(name, count) for count, name in inputs)
        self.outputs = list(Ingredient(name, count) for count, name in outputs)

    def __str__(self):
        return f"{self.name}/{self.cycle_rate} < {', '.join(map(str, self.inputs))} > {', '.join(map(str, self.outputs))}"

    def __repr__(self):
        return str(self)

    @classmethod
    def empty(cls, name=""):
        return cls(name, 60, [], [])


class Producer:
    def __init__(self, name, *, is_miner, is_pow_gen, max_mk, base_power, recipes):
        self.name = name
        self.is_miner = is_miner
        self.is_pow_gen = is_pow_gen
        self.max_mk = max_mk
        self.base_power = base_power
        self.recipes = [Recipe(k, v[0], v[1], v[2]) for k, v in recipes.items()]
        self.recipe_map = dict()
        self.update_recipe_map()

    def update_recipe_map(self):
        self.recipe_map = {}
        for recipe in self.recipes:
            self.recipe_map[recipe.name] = recipe


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


class Purity(Enum):
    NA     = 0
    PURE   = 1
    NORMAL = 2
    IMPURE = 4


class Node:
    yaml_tag = "!Node"
    blueprint_listings = {}

    def __init__(self, producer, recipe, count=1, clock_rate=100, mk=1, purity=Purity.NORMAL, is_dummy=False):
        # a dummy is a read-only, non-interactable, row - for example expanded from a blueprint
        # (can't shift it, can't delete it)
        self.is_dummy = is_dummy
        self.blueprint_children = []
        self.producer = producer
        self.recipe = recipe
        self.count = count
        self.clock_rate = clock_rate
        self.mk = mk
        self.purity = purity if producer.is_miner else Purity.NA
        self.uirow = None
        self.ui_elems = []
        self.energy = 0
        self.ingredients = {}
        self.update()

    def producer_reset(self):
        self.recipe = self.producer.recipes[0] if self.producer.recipes else Recipe.empty()
        if self.producer.is_miner:
            if self.purity == Purity.NA:
                self.purity = Purity.NORMAL
        else:
            self.purity = Purity.NA
        self.energy = 0
        self.update()

    def update_blueprint_listings(self):
        if not self.producer.name == "Blueprint":
            return
        print("update")
        self.producer.recipes = [Recipe.empty()]
        names = list(os.scandir(DPATH_DATA))
        fnames = [entry.name for entry in names if entry.is_file() if not entry.name.startswith(".")]
        for fname in fnames:
            self.update_blueprint(fname)
        self.producer.update_recipe_map()

    def update_blueprint(self, fname):
        if not self.producer.name == "Blueprint":
            return
        if not fname.lower().endswith(".yaml"):
            fname += ".yaml"

        try:
            if not (DPATH_DATA / fname).is_file():
                return False
            with open(DPATH_DATA / fname, "r") as fp:
                data = yaml.unsafe_load(fp)
                bp_nodes = []
                bp_recipe = None
                if data:
                    if isinstance(data[0], Recipe):
                        bp_recipe, bp_nodes = data
                    elif isinstance(data[0], Node):
                        bp_nodes = data
                    else:
                        raise ValueError("Unexpected Data Format:\n" + str(data))

            if not isinstance(bp_recipe, Recipe):
                bp_recipe = Recipe(fname, 60, [], [])
            bp_recipe.name = os.path.splitext(fname)[0]
            # FIXME: deal with nested blueprints and circular references
            # WARNING: we're not shadowing the class variable here - it should stay that way!
            self.blueprint_listings[fname] = (bp_recipe, bp_nodes)
            self.producer.recipes += [bp_recipe]
        except Exception as e:
            print("nOOOO!")
            print(e)
        return True

    @property
    def blueprint_rows(self):
        if not self.producer.name == "Blueprint":
            return []

    def update(self):
        self.energy = 0
        self.ingredients = {}
        rate_mult = 60/self.recipe.cycle_rate

        ingredient_mult = rate_mult * (self.clock_rate * self.count) / 100
        for inp in self.recipe.inputs:
            self.ingredients[inp.name] = int(inp.count * ingredient_mult * -1)

        for out in self.recipe.outputs:
            if self.producer.is_miner:
                self.ingredients[out.name] = int((out.count/self.purity.value) * (pow(2, self.mk)) * ingredient_mult)
            else:
                self.ingredients[out.name] = int(out.count * ingredient_mult)

        if self.producer.is_pow_gen:
            pass # TODO
        else:
            self.enegry = round(self.producer.base_power * math.pow((self.clock_rate/100), 1.321928) * self.count)


blueprint_producer = Producer(
        "Blueprint",
        is_miner=False,
        is_pow_gen=False,
        max_mk=0,
        base_power=0,
        recipes={"":     [60, [], []],}
)
PRODUCERS = [blueprint_producer]
data_fpath = "satisfactory_production_buildings.json"
with open(data_fpath) as fp:
    data = json.load(fp)

for k, v in data.items():
    producer = Producer(k, **v)
    PRODUCERS += [producer]

PRODUCER_MAP = { p.name: p for p in PRODUCERS }

def node_representer(dumper, data):
    return dumper.represent_mapping(u"!node", {
        "producer":   data.producer.name,
        "recipe":     data.recipe.name,
        "count":      data.count,
        "clock_rate": data.clock_rate,
        "mk":         data.mk,
        "purity":     data.purity.value
    })


def node_constructor(loader, node):
    data = loader.construct_mapping(node)
    prod = PRODUCER_MAP[data["producer"]]
    node = Node(producer   = prod,
                recipe     = Recipe.empty(),
                count      = data["count"],
                clock_rate = data["clock_rate"],
                mk         = data["mk"],
                purity     = Purity(data["purity"]))
    if prod.name == "Blueprint":
        node.update_blueprint(data["recipe"])
        prod.update_recipe_map()
        if data["recipe"] in prod.recipe_map:
            node.recipe = prod.recipe_map[data["recipe"]]
        else:
            node.recipe = Recipe.empty("! " + data["recipe"])
    else:
        node.recipe = prod.recipe_map[data["recipe"]]
    return node

yaml.add_representer(Node, node_representer)
yaml.add_constructor(u'!node', node_constructor)


def ingredient_representer(dumper, ingredient):
    # FIXME: why does the yaml dumper reverse the list sequence.... WHY ???
    return dumper.represent_sequence(u"!ingredient", [ingredient.count, ingredient.name])


def ingredient_constructor(loader, data):
    data = loader.construct_sequence(data)
    return Ingredient(*data)

yaml.add_representer(Ingredient, ingredient_representer)
yaml.add_constructor(u'!ingredient', ingredient_constructor)


# bp = Node(blueprint_producer, blueprint_producer.recipes[0])
