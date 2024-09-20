# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .link import ModuleFile
from .recipe import (
    Ingredient,
    Recipe,
)
from .producer import PRODUCER_MAP
from .module import MODULE_PRODUCER
from .node import (
    Purity,
    Node,
)
from .nodetree import (
    SummaryNode,
    NodeInstance,
    NodeTree,
)

import yaml


def node_representer(dumper, data):
    buf = {
        "producer": data.producer.name,
        "recipe": data.recipe.name,
        "count": data.count,
        "clock_rate": data.clock_rate,
        "mk": data.mk,
        "purity": data.purity.value,
    }
    if data.clamp:
        buf.update({
            "clamp": {
                data.clamp.name: data.clamp.count
            }
        })
    return dumper.represent_mapping(u"!node", buf)


SEEN_MODULES = set()


def node_constructor(loader, node):
    global SEEN_MODULES
    data = loader.construct_mapping(node, deep=True)
    prod = PRODUCER_MAP[data["producer"]]

    clamp = None
    if "clamp" in data:
        _clamp = list(data["clamp"].items())
        clamp = Ingredient(*_clamp[0])

    node = Node(producer   = prod,
                recipe     = Recipe.empty(),
                count      = data["count"],
                clock_rate = data["clock_rate"],
                mk         = data["mk"],
                purity     = Purity(data["purity"]),
                clamp      = clamp)
    if prod.is_module:
        if not data["recipe"] in SEEN_MODULES:
            SEEN_MODULES.add(data["recipe"])
            module_file = ModuleFile(data["recipe"])

            MODULE_PRODUCER.update_module(module_file)
            prod.update_recipe_map()
        if data["recipe"] in prod.recipe_map:
            node.recipe = prod.recipe_map[data["recipe"]]
        else:
            node.recipe = Recipe.empty("! " + data["recipe"])
    else:
        recipe_name = data["recipe"].removeprefix("!").strip()
        if recipe_name in prod.recipe_map:
            node.recipe = prod.recipe_map[recipe_name]
        else:
            alternate = "Alternate: " + recipe_name
            if alternate in prod.recipe_map:
                node.recipe = prod.recipe_map["Alternate: " + recipe_name]
            else:
                node.recipe = Recipe(f"! { recipe_name }", 60, [], [], False)
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
