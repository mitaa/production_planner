# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from . import CONFIG
from .recipe import Recipe
from .producer import Producer
from .link import ModuleFile

import os
from pathlib import Path
from typing import Optional


class _ModuleProducer(Producer):
    module_index = {}

    @property
    def is_module(self):
        return True

    @classmethod
    def register_module(cls, module_id, tree):
        # TODO: change from tuple to simple Nodetree, in combination with new tree.recipe property
        cls.module_index[module_id] = (tree.node_main.recipe, tree)

    @classmethod
    def get_module_tree(cls, module_id):
        return cls.module_index[module_id][1]

    def rescan_modules(self, subroot=None):
        if not subroot:
            self.recipes = [Recipe.empty()]
            root = CONFIG.dpath_data
        else:
            root = subroot

        for entry in os.scandir(root):
            if not entry.name.startswith("."):
                if entry.is_file() and Path(entry.name).suffix == ".yaml":
                    self.update_module(ModuleFile(entry.path))
                elif entry.is_dir():
                    self.rescan_modules(entry.path)

        if not subroot:
            self.update_recipe_map()

    def update_module(self, modulefile: ModuleFile) -> Optional:
        if not modulefile.fullpath.is_file():
            return None

        from .. import io
        tree = io.load_data(modulefile.fullpath)
        if tree is None:
            # FIXME
            from . import APP
            APP.notify(f"Failed loading module: {modulefile.id}")
            return None

        tree.update_summaries()
        tree.mark_from_module()

        tree.node_main.recipe.name = modulefile.id

        self.register_module(modulefile.id, tree)

        idx_delete = None
        idx_insert = len(self.recipes)
        # FIXME: refer to the actual MODULE PRODUCER
        # FIXME: move update module listing / register module into an appropriate location
        for idx, recipe in enumerate(self.recipes):
            if recipe.name == tree.node_main.recipe.name:
                idx_delete = idx_insert = idx
        if idx_delete is not None:
            del self.recipes[idx_delete]
        self.recipes.insert(idx_insert, tree.node_main.recipe)
        return tree


MODULE_PRODUCER = _ModuleProducer(
    "Module",
    is_abstract=True,
    is_miner=False,
    is_pow_gen=False,
    max_mk=0,
    base_power=0,
    recipes={"": [60, [], []], },
    description="A pseudo producer which allows to embed other files into this one."
)
