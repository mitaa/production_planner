# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .edit import EditValue, Bounds

from .recipe import (
    Recipe,
    Ingredient,
)
from .producer import EMPTY_PRODUCER

import math
from enum import Enum
from typing import Self


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


class EditPurityValue(EditValue):
    purity_map = list(reversed(Purity.__members__))

    def get_num(self):
        return self.purity_map.index(self.value.name) + 1

    def set_num(self, value):
        value = int(min(max(1, value), 3))
        self.value = Purity[self.purity_map[int(value - 1)]]


class EditClampValue(EditValue):
    def get_num(self):
        return self.value.count

    def set_num(self, value):
        self.value.count = value


# class EditProducerValue(EditValue):
#     def get_num(self):
#         return self.value.count

#     def set_num(self, value):
#         self.value.count = value


# class EditRecipeValue(EditValue):
#     def get_num(self):
#         return self.value.producer

#     def set_num(self, value):
#         self.value.count = value


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
        self.clamp = EditClampValue(clamp) if clamp else None
        self.count = EditValue(count, bounds=Bounds(0, 999))
        self.clock_rate = EditValue(clock_rate, bounds=Bounds(0, 250))
        self.mk = EditValue(mk, bounds=Bounds(1, 3))
        self.purity = EditPurityValue(purity if producer.is_miner else Purity.NA, bounds=Bounds(1, 3))
        self.uirow = None
        self.ui_elems = []
        self.energy = 0
        self.energy_module = 0
        self.ingredients = {}
        self.update()

    def duplicate_partially(self) -> Self:
        return Node(self.producer,
                    self.recipe,
                    mk=self.mk.value)

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
            self.purity = self.purity_cache.get(self.producer.name, EditPurityValue(Purity.NORMAL))
        else:
            self.purity = EditPurityValue(Purity.NA)
        self.energy = 0
        self.update()

    def update(self):
        self.energy = 0
        self.ingredients = {}
        rate_mult = 60 / self.recipe.cycle_rate

        if self.clamp and self.count.value:

            for ingredient in self.recipe.inputs:
                if ingredient.name == self.clamp.value.name:
                    # self.clock_rate.value = ((abs(int(clamped.count.value)) * 100) / (rate_mult / self.count.value)) / ingredient.count.value
                    self.clock_rate.value = 5 * self.recipe.cycle_rate * abs(self.clamp.value.count) / (3 * ingredient.count * self.count.value)
                    break
            for ingredient in self.recipe.outputs:
                if ingredient.name == self.clamp.value.name:
                    if self.producer.is_miner:
                        self.clock_rate.value = 5 * self.recipe.cycle_rate * self.purity.value.value * abs(self.clamp.value.count) / (3 * pow(2, self.mk.value) * ingredient.count * self.count.value)
                    else:
                        self.clock_rate.value = 5 * self.recipe.cycle_rate * abs(self.clamp.value.count) / (3 * ingredient.count * self.count.value)

            if self.clock_rate.value > 250:
                self.clock_rate.value = 250

        ingredient_mult = rate_mult * (self.clock_rate.value * self.count.value) / 100
        for inp in self.recipe.inputs:
            total = inp.count * ingredient_mult * -1
            self.ingredients[inp.name] = total

        for out in self.recipe.outputs:
            if self.producer.is_miner:
                total = (out.count / self.purity.value.value) * (pow(2, self.mk.value)) * ingredient_mult
                self.ingredients[out.name] = total
            else:
                total = out.count * ingredient_mult
                self.ingredients[out.name] = total

        if self.producer.is_pow_gen:
            pass  # TODO
        elif self.is_module:
            self.energy = self.energy_module * self.count.value
        else:
            self.energy = self.producer.base_power * math.pow((self.clock_rate.value / 100), 1.321928) * self.count.value

    @property
    def is_module(self):
        return self.producer.is_module

