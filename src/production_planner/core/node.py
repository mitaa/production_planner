# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .recipe import Recipe, Ingredient
from .producer import EMPTY_PRODUCER

import math
from enum import Enum


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


class Node:
    yaml_tag = "!Node"

    # defaults to be shadowed (avoiding AttributeError's)
    producer = EMPTY_PRODUCER

    def __init__(self, producer, recipe, count=1, clock_rate=100, mk=1, purity=Purity.NORMAL, clamp=None, is_dummy=False):
        # a dummy is a read-only, non-interactable, row - for example expanded from a module
        # (can't shift it, can't delete it)
        self.is_dummy = is_dummy
        # remembers the last selected recipe for each producer
        self.recipe_cache = {}
        self.purity_cache = {}
        self.module_children = []
        self.producer = producer
        self.recipe = recipe
        self.clamp = clamp
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
        if value:
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

    def update(self):
        self.energy = 0
        self.ingredients = {}
        rate_mult = 60 / self.recipe.cycle_rate

        if self.clamp:
            for ingredient in self.recipe.inputs:
                if ingredient.name == self.clamp.name:
                    # self.clock_rate = ((abs(int(clamped.count)) * 100) / (rate_mult / self.count)) / ingredient.count
                    self.clock_rate = 5 * self.recipe.cycle_rate * abs(self.clamp.count) / (3 * ingredient.count * self.count)
                    break
            for ingredient in self.recipe.outputs:
                if ingredient.name == self.clamp.name:
                    if self.producer.is_miner:
                        self.clock_rate = 5 * self.recipe.cycle_rate * self.purity.value * abs(self.clamp.count) / (3 * pow(2, self.mk) * ingredient.count * self.count)
                    else:
                        self.clock_rate = 5 * self.recipe.cycle_rate * abs(self.clamp.count) / (3 * ingredient.count * self.count)

                    if self.clock_rate > 250:
                        self.clock_rate = 250

        ingredient_mult = rate_mult * (self.clock_rate * self.count) / 100
        for inp in self.recipe.inputs:
            total = inp.count * ingredient_mult * -1
            self.ingredients[inp.name] = total
            if self.clamp and self.clamp.name == inp.name and self.clamp.count != total:
                self.clamp.count = total

        for out in self.recipe.outputs:
            if self.producer.is_miner:
                total = (out.count / self.purity.value) * (pow(2, self.mk)) * ingredient_mult
                self.ingredients[out.name] = total
            else:
                total = out.count * ingredient_mult
                self.ingredients[out.name] = total
            if self.clamp and self.clamp.name == out.name and abs(self.clamp.count - total) > 0.01:
                from ..core import smartround
                self.clamp.count = smartround(total)

        if self.producer.is_pow_gen:
            pass  # TODO
        elif self.is_module:
            self.energy = self.energy_module * self.count
        else:
            self.energy = self.producer.base_power * math.pow((self.clock_rate / 100), 1.321928) * self.count

    @property
    def is_module(self):
        return self.producer.is_module

