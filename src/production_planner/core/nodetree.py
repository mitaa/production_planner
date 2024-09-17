# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .link import ModuleFile
from .recipe import Recipe
from .module import MODULE_PRODUCER
from .producer import SUMMARY_PRODUCER
from .node import Node

from typing import Self

from textual import log

import yaml


class SummaryNode(Node):
    def __init__(self, nodes):
        self.row_idx = 0
        super().__init__(SUMMARY_PRODUCER, self.update_summary(nodes), is_dummy=True)

    def producer_reset(self):
        ...

    def update_summary(self, nodes: [Node]) -> Recipe:
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


class NodeInstance:
    # FIXME: this is shared between all instances but this must not be true for unrelated NodeTrees
    row_to_node_index = []

    def __init__(self, node: Node, children: [Self] = None, parent: [Self] = None, shown=True, expanded=True, row_idx=None, level=0):
        self.tree_modules = set()

        self.parent = parent
        self.node_main = node

        if children is None:
            children = []

        for child in children:
            child.parent = self
        self.node_children = children
        self.shown = shown
        self.expanded = expanded
        self.indent_str = " " * max(0, level - 2)
        self.row_idx = row_idx
        self.level = level
        self.from_module = False

    def show_hide(self, shown=None):
        # Note: always show the top row (summary balance)
        if self.parent:
            self.shown = shown or (not self.shown)
            if self.shown:
                self.parent.show_hide(shown=True)

    def swap_vis_space(self, shown=None):
        self.show_hide(shown=None)

        if not self.parent and self.shown:
            for child in self.node_children:
                child.swap_vis_space(shown=True)

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
        if node is self:
            self.node_children = []
        else:
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
            self.node_main.update_summary([cinstance.node_main for cinstance in self.node_children])

        if level < 2:
            NodeInstance.row_to_node_index += [self] * len(nodes)

        return nodes

    def update_summaries(self):
        for child in self.node_children:
            child.update_summaries()

        if not isinstance(self.node_main, SummaryNode):
            return

        self.node_main.update_summary([cinstance.node_main for cinstance in self.node_children])

    def update_parents(self):
        for child in self.node_children:
            child.parent = self
            child.update_parents()

    def set_module(self, module_file: ModuleFile):
        if not self.node_main.is_module:
            return

        # FIXME: guard against recursive modules here..
        if module_file:
            self.node_children.clear()
            tree = MODULE_PRODUCER.update_module(module_file)
            if not tree:
                return

            self.add_children([tree])

            if self.node_children:
                # FIXME: sum with nested modules isn't always correct
                self.node_main.energy_module = self.node_children[0].node_main.energy

    def collect_modules(self, level=0):
        if level == 0:
            self.tree_modules.clear()

        if self.node_main.is_module:
            self.tree_modules.add(self.node_main.recipe.name)

        for child in self.node_children:
            child.collect_modules(level + 1)

    def mark_from_module(self):
        self.from_module = True
        for child in self.node_children:
            child.mark_from_module()

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

    @property
    def recipe(self) -> Recipe:
        assert isinstance(self.children[0], SummaryNode)
        return self.children[0].node_main.recipe

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
        from . import APP
        module_stack = module_stack or []

        def reload_module(instance) -> str | bool | None:
            if instance.node_main.is_module:
                module = instance.node_main.recipe.name
                log(f"reloading module: {module}")
                self.tree_modules.add(module)
                if module in module_stack:
                    log("Error: Recursive Modules!")
                    APP.notify(f"Error; Resursive Modules: ({'>'.join(module_stack)})",
                               severity="error",
                               timeout=10)
                    idx = module_stack.index(module)
                    substack = module_stack[idx:] + [module]
                    log("\n".join(substack))
                    return None
                instance.set_module(ModuleFile(module))
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
