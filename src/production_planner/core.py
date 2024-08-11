# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import math
from enum import Enum
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Self

from textual.app import App
from textual import log
import yaml
import platformdirs

from . import jsonshelve
from textual.widgets import DataTable

APP = None


def static(fn):
    return fn()


def ensure_key(store, key, default):
    if key in store:
        actual = store[key]
        if type(actual) is dict and type(default) is dict:
            ensure_keys(actual, key_def_pairings=default)
            store[key] = actual
    else:
        store[key] = default


def ensure_keys(store, key_def_pairings={}):
    for k, v in key_def_pairings.items():
        ensure_key(store, k, v)


DPATH_DATA = Path(platformdirs.user_data_dir("production_planner", "mitaa"))
FPATH_CONFIG = os.path.join(DPATH_DATA, ".config.json")
os.makedirs(DPATH_DATA, exist_ok=True)
CONFIG = jsonshelve.FlatShelf(FPATH_CONFIG, dump_kwargs={"indent": 4})

ensure_keys(CONFIG, {
    "last_file": ".cached.yaml"
})


def get_path(obj, path):
    paths = path.split(".", maxsplit=1)
    primpath = paths[0]
    subpaths = paths[1:]
    if not subpaths:
        return getattr(obj, path)
    else:
        return get_path(getattr(obj, primpath), subpaths[0])


def set_path(obj, path, value):
    paths = path.split(".", maxsplit=1)
    primpath = paths[0]
    subpaths = paths[1:]
    if not subpaths:
        return setattr(obj, path, value)
    else:
        return set_path(getattr(obj, primpath), subpaths[0], value)


@dataclass
class Ingredient:
    name: str
    count: int

    def __str__(self):
        return f"({self.count}x {self.name})"

    def __hash__(self):
        return hash((self.name, self.count))


class Recipe(yaml.YAMLObject):
    yaml_tag = u"!recipe"

    recipe_to_producer_map = {}

    def __init__(self, name, cycle_rate, inputs: [(int, str)], outputs: [(int, str)]):
        self.name = name
        self.cycle_rate = cycle_rate
        self.inputs = list(Ingredient(name, count) for count, name in inputs)
        self.outputs = list(Ingredient(name, count) for count, name in outputs)

    def __str__(self):
        return f"{self.name}/{self.cycle_rate} {', '.join(map(str, self.inputs))} <> {', '.join(map(str, self.outputs))}"

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return type(self) is type(other) and self.name == other.name and self.cycle_rate == other.cycle_rate and self.inputs == other.inputs and self.outputs == other.outputs

    @property
    def producer(self):
        if self in self.recipe_to_producer_map:
            return self.recipe_to_producer_map[self]
        else:
            return None

    def __hash__(self):
        return hash((self.name, self.cycle_rate, tuple(self.inputs), tuple(self.outputs)))

    @classmethod
    def empty(cls, name=""):
        return cls(name, 60, [], [])

    @classmethod
    def from_dict(cls, ingredients: {str: int}, name="", cycle_rate=60) -> Self:
        inputs = []
        outputs = []
        for ingredient, quantity in sorted(ingredients.items()):
            if quantity < 0:
                inputs += [(abs(quantity), ingredient)]
            else:
                outputs += [(quantity, ingredient)]
        return cls(name, cycle_rate, inputs, outputs)


class Producer:
    def __init__(self, name, *, is_miner, is_pow_gen, max_mk, base_power, recipes, abstract=False):
        self.abstract = abstract
        self.name = name
        self.is_miner = is_miner
        self.is_pow_gen = is_pow_gen
        self.max_mk = max_mk
        self.base_power = base_power
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
            if not self.abstract:
                recipe.recipe_to_producer_map[recipe] = self

    def __str__(self):
        buf = self.name
        flags = [self.is_miner, self.is_pow_gen]
        attrs = ["Miner", "Power Generator"]
        attrs = [attr for idx, attr in enumerate(attrs) if flags[idx]]
        if attrs:
            buf += f" ({', '.join(attrs)})"
        return buf

    @property
    def is_module(self):
        return self.name in ["Module", "Blueprint"]


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
    def __str__(self):
        match self:
            case Purity.NA:
                return ""
            case _:
                return self.name


empty_producer = Producer(
        "",
        abstract=True,
        is_miner=False,
        is_pow_gen=False,
        max_mk=0,
        base_power=0,
        recipes={"":     [60, [], []],}
)

module_producer = Producer(
        "Module",
        abstract=True,
        is_miner=False,
        is_pow_gen=False,
        max_mk=0,
        base_power=0,
        recipes={"": [60, [], []], }
)
PRODUCERS = [module_producer]
data_fpath = os.path.join(os.path.split(os.path.abspath(__file__))[0], "production_buildings.json")
with open(data_fpath) as fp:
    data = json.load(fp)

for k, v in data.items():
    producer = Producer(k, **v)
    PRODUCERS += [producer]

PRODUCERS += [empty_producer]
PRODUCER_NAMES = [producer.name for producer in PRODUCERS]


@static
def all_recipes_producer():
    recip_names = set()
    recipes = {}
    for producer in PRODUCERS:
        producer_recipe_map = dict({r.name: r for r in producer.recipes if r.name})
        if producer.is_module:
            continue
        duplicates = recip_names & set(producer_recipe_map.keys())
        if duplicates:
            self.app.notify(str(duplicates))
        recipes.update(producer_recipe_map)

    prod = Producer(
        "<ALL RECIPES>",
        abstract=True,
        is_miner=False,
        is_pow_gen=False,
        max_mk=0,
        base_power=0,
        recipes={},
    )
    prod.recipes = list(sorted(recipes.values(), key=lambda r: r.name))
    return prod


PRODUCER_MAP = {p.name: p for p in ([all_recipes_producer] + PRODUCERS)}
PRODUCER_MAP["Blueprint"] = PRODUCER_MAP["Module"]


class Node:
    yaml_tag = "!Node"
    module_listings = {}

    # defaults to be shadowed (avoiding AttributeError's)
    producer = empty_producer

    def __init__(self, producer, recipe, count=1, clock_rate=100, mk=1, purity=Purity.NORMAL, is_dummy=False):
        # a dummy is a read-only, non-interactable, row - for example expanded from a module
        # (can't shift it, can't delete it)
        self.is_dummy = is_dummy
        # remembers the last selected recipe for each producer
        self.recipe_cache = {}
        self.purity_cache = {}
        self.module_children = []
        self.producer = producer
        self.recipe = recipe
        self.count = count
        self.clock_rate = clock_rate
        self.mk = mk
        self.purity = purity if producer.is_miner else Purity.NA
        self.uirow = None
        self.ui_elems = []
        self.energy = 0
        self.energy_module = 0
        self.ingredients = {}
        self.update()

    @property
    def recipe(self):
        return self._recipe

    @recipe.setter
    def recipe(self, value):
        if not hasattr(self, "recipe_cache"):
            # remembers the last selected recipe for each producer
            self.recipe_cache = {}
        self._recipe = value
        self.recipe_cache[self.producer.name] = value

    @property
    def purity(self):
        return self._purity

    @purity.setter
    def purity(self, value):
        if not hasattr(self, "purity_cache"):
            # remembers the last selected purity for each producer
            self.purity_cache = {}
        self._purity = value
        self.purity_cache[self.producer.name] = value

    def producer_reset(self):
        if not self.recipe or self.recipe not in self.producer.recipe_map.values():
            default = self.producer.recipes[0] if self.producer.recipes else Recipe.empty()
            self.recipe = self.recipe_cache.get(self.producer.name, default)

        if self.producer.is_miner:
            self.purity = self.purity_cache.get(self.producer.name, Purity.NORMAL)
        else:
            self.purity = Purity.NA
        self.energy = 0
        self.update()

    def update_module_listings(self):
        if not self.producer.is_module:
            return
        self.producer.recipes = [Recipe.empty()]
        names = list(os.scandir(DPATH_DATA))
        fnames = [entry.name for entry in names if entry.is_file() if not entry.name.startswith(".")]
        for fname in fnames:
            self.update_module_listing(fname)
        self.producer.update_recipe_map()

    def update_module_listing(self, fname) -> bool:
        if not self.producer.is_module:
            return
        if not fname.lower().endswith(".yaml"):
            fname += ".yaml"

        if not (DPATH_DATA / fname).is_file():
            return False

        tree = load_data(DPATH_DATA / fname)
        if tree is None:
            raise ValueError("Unexpected Data Format")

        tree.update_summaries()
        module_recipe = tree.node_main.recipe
        module_nodes = []

        module_recipe.name = os.path.splitext(fname)[0]
        # WARNING: we're not shadowing the class variable here - it should stay that way!
        self.module_listings[fname] = (module_recipe, tree)
        idx_delete = None
        idx_insert = len(self.producer.recipes)
        for idx, recipe in enumerate(self.producer.recipes):
            if recipe.name == module_recipe.name:
                idx_delete = idx_insert = idx
        if idx_delete is not None:
            del self.producer.recipes[idx_delete]
        self.producer.recipes.insert(idx_insert, module_recipe)
        return True

    def update(self):
        self.energy = 0
        self.ingredients = {}
        rate_mult = 60 / self.recipe.cycle_rate

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
        elif self.is_module:
            self.energy = self.energy_module * self.count
        else:
            self.energy = round(self.producer.base_power * math.pow((self.clock_rate/100), 1.321928) * self.count)

    @property
    def is_module(self):
        return self.producer.is_module


def node_representer(dumper, data):
    return dumper.represent_mapping(u"!node", {
        "producer": data.producer.name,
        "recipe": data.recipe.name,
        "count": data.count,
        "clock_rate": data.clock_rate,
        "mk": data.mk,
        "purity": data.purity.value
    })


SEEN_MODULES = set()


def node_constructor(loader, node):
    global SEEN_MODULES
    data = loader.construct_mapping(node)
    prod = PRODUCER_MAP[data["producer"]]
    node = Node(producer   = prod,
                recipe     = Recipe.empty(),
                count      = data["count"],
                clock_rate = data["clock_rate"],
                mk         = data["mk"],
                purity     = Purity(data["purity"]))
    if prod.is_module:
        if not data["recipe"] in SEEN_MODULES:
            SEEN_MODULES.add(data["recipe"])
            node.update_module_listing(data["recipe"])
            prod.update_recipe_map()
        if data["recipe"] in prod.recipe_map:
            node.recipe = prod.recipe_map[data["recipe"]]
        else:
            node.recipe = Recipe.empty("! " + data["recipe"])
    else:
        node.recipe = prod.recipe_map[data["recipe"]]
    node.update()
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


class SummaryNode(Node):
    def __init__(self, nodes):
        self.row_idx = 0
        super().__init__(empty_producer, self.update_recipe(nodes), is_dummy=True)

    def producer_reset(self):
        ...

    def update_recipe(self, nodes: [Node]) -> Recipe:
        # TODO: also handle power consumption
        power = 0
        sums = {}
        for node in nodes:
            power += node.energy
            for ingredient, quantity in node.ingredients.items():
                sums[ingredient] = sums.get(ingredient, 0) + quantity
        # Cull ingredients with quantity == 0
        sums = {k: v for k, v in sums.items() if v}
        self.recipe = Recipe.from_dict(sums)
        self.energy = power
        return self.recipe


def summary_representer(dumper, data):
    return dumper.represent_yaml_object(u"!summary", data.recipe, Recipe)


def summary_constructor(loader, data):
    recipe = loader.construct_yaml_object(data)
    summary = SummaryNode([])
    summary.recipe = recipe
    # FIXME: this might not quite make sense since the child nodes for calculating the summary are missing ...
    return summary


yaml.add_representer(SummaryNode, summary_representer)
yaml.add_constructor(u'!summary', summary_constructor)


class NodeInstance:
    row_to_node_index = []
    blueprints = set()

    def __init__(self, node:Node, children:[Self]=None, parent:[Self]=None, shown=True, expanded=True, row_idx=None, level=0):
        self.parent = parent
        self.node_main = node
        if children is None:
            children = []

        for child in children:
            child.parent = self
        self.node_children = children
        self.shown = shown
        self.expanded = expanded
        # TODO: self.activated = activated
        self.row_idx = row_idx
        self.level = level

    def show_hide(self, shown=None):
        self.shown = shown or (not self.shown)
        if self.shown and self.parent:
            self.parent.show_hide(shown=True)

    def swap_vis_space(self):
        self.show_hide()
        for child in self.node_children:
            child.swap_vis_space()

    def add_children(self, instances: [Self], at_idx=None):
        root = self
        if at_idx is None:
            at_idx = len(self.node_children)
        elif isinstance(at_idx, NodeInstance):
            if at_idx.parent is None:
                at_idx = 0
                root = self
            else:
                root = at_idx.parent
                at_idx = root.node_children.index(at_idx) + 1

        for instance in instances:
            instance.parent = root
            root.node_children.insert(at_idx, instance)
            at_idx += 1

    def get_node(self, row_idx: int) -> None | Self:
        # Force row index to be in bounds
        row_idx = min(max(0, row_idx), len(self.row_to_node_index) - 1)
        node = self.row_to_node_index[row_idx] if self.row_to_node_index else None
        return node  # None if isinstance(node, NodeTree) else node

    def shift_child(self, child: Self, offset: int) -> bool:
        if offset == 0:
            return True

        if child not in self.node_children:
            return False
        idx = self.node_children.index(child)
        del self.node_children[idx]
        self.node_children.insert(max(0, idx + offset), child)

    def remove_node(self, row_idx: int):
        node = self.get_node(row_idx)
        if node is None:
            return
        self.node_children.remove(node)

    def get_nodes(self, level=0) -> [Self]:
        self.indent_str = " " * max(0, level - 2)
        if level == 0:
            NodeInstance.row_to_node_index = []

        if not self.shown:
            self.row_idx = NodeInstance.row_to_node_index[-1].row_idx if NodeInstance.row_to_node_index else 0
            return []
        else:
            self.level = level
            nodes = [self]
            self.row_idx = len(NodeInstance.row_to_node_index)

        if level < 1:
            NodeInstance.row_to_node_index += [self]

        if self.expanded:
            for cnode in self.node_children:
                cnodes = cnode.get_nodes(level=level + 1)
                nodes += cnodes

        if isinstance(self.node_main, SummaryNode):
            # Note: the innermost nodes get their recipe updated before the outer nodes
            #       because of the `get_nodes` calls above
            self.node_main.update_recipe([cinstance.node_main for cinstance in self.node_children])

        if level == 1:
            NodeInstance.row_to_node_index += [self] * len(nodes)

        return nodes

    def update_summaries(self):
        for child in self.node_children:
            child.update_summaries()

        if not isinstance(self.node_main, SummaryNode):
            return

        self.node_main.update_recipe([cinstance.node_main for cinstance in self.node_children])

    def update_parents(self):
        for child in self.node_children:
            child.parent = self
            child.update_parents()

    def set_module(self, module_name: str):
        if not self.node_main.is_module:
            return

        fname = f"{module_name}.yaml"
        if not self.node_main.update_module_listing(fname):
            return
        module_tree = self.node_main.module_listings[fname][1]
        self.node_children.clear()
        self.add_children([module_tree])
        if self.node_children:
            self.node_main.energy_module = self.node_children[0].node_main.energy

    def collect_modules(self, level=0):
        if level == 0:
            self.blueprints.clear()

        if self.node_main.is_module:
            self.blueprints.add(self.node_main.recipe.name)

        for child in self.node_children:
            child.collect_modules(level + 1)

    def __getitem__(self, row_idx):
        self.get_node(row_idx)

    def __delitem__(self, row_idx):
        self.remove_node(row_idx)

    def __str__(self) -> str:
        # FIXME
        buf = "├ " if self.node_children else "└"
        buf += self.node_main.producer.name
        for child in self.node_children:
            lines = str(child).splitlines()
            for line in lines:
                buf += f"\n {line}"
        return buf


class NodeTree(NodeInstance):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def from_nodeinstances(cls, instances: [NodeInstance]) -> Self:
        nodes = [instance.node_main for instance in instances]
        return cls(SummaryNode(nodes), instances)

    @classmethod
    def from_nodes(cls, nodes: [Node]) -> Self:
        return cls.from_nodeinstances([NodeInstance(node) for node in nodes])

    def __hash__(self):
        return hash(yaml.dump(self))

    def reload_modules(self, instances=None, module_stack=None):
        module_stack = module_stack or []
        def reload_module(instance) -> str | bool | None:
            if instance.node_main.is_module:
                module = instance.node_main.recipe.name
                log(f"reloading module: {module}")
                self.blueprints.add(module)
                if module in module_stack:
                    log("Error: Recursive Modules!")
                    APP.notify(f"Error; Resursive Modules: ({'>'.join(module_stack)})",
                               severity="error",
                               timeout=10)
                    idx = module_stack.index(module)
                    substack = module_stack[idx:] + [module]
                    log("\n".join(substack))
                    return None
                instance.set_module(module)
                return True
            else:
                return False

        if instances is None:
            instances = self.node_children

        for instance in instances:
            res = reload_module(instance)
            match res:
                case str():
                    self.reload_modules(instance.node_children, module_stack + res)
                case None:
                    log("Error reloading module")
                case _:
                    self.reload_modules(instance.node_children, module_stack)


def instance_representer(dumper, data):
    return dumper.represent_mapping(u"!instance", {
        "shown":    data.shown,
        "expanded": data.expanded,
        "main":     data.node_main,
        "children": data.node_children,
    })


def instance_constructor(loader, data):
    data = loader.construct_mapping(data)
    instance = NodeInstance(data["main"],
                            data["children"],
                            shown=data["shown"],
                            expanded=data["expanded"])
    return instance


def tree_representer(dumper, data):
    return dumper.represent_sequence(u"!tree", data.node_children)


def tree_constructor(loader, data):
    data = loader.construct_sequence(data)
    tree = NodeTree.from_nodeinstances(data)
    return tree


yaml.add_representer(NodeInstance, instance_representer)
yaml.add_constructor(u'!instance', instance_constructor)

yaml.add_representer(NodeTree, tree_representer)
yaml.add_constructor(u'!tree', tree_constructor)


def load_data(fpath) -> None | NodeTree:
    with open(fpath, "r") as fp:
        data = yaml.unsafe_load(fp)
        match data:
            case NodeTree():
                tree = data
            case[Node(), *_]:
                tree = NodeTree.from_nodes(data)
            case[Recipe(), NodeTree()]:
                _, tree = data
            case[Recipe(), *_]:
                _, data = data
                tree = NodeTree.from_nodes(data)
            case _:
                log(f"Could not parse file: `{fpath}`", timeout=10)
                return
    return tree
