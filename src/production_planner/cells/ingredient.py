# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .. import core
from ._cells import (
    NumericEditaleCell,
    Bounds,
    CellValue,
)
from ..core import smartround
from ..core import SummaryNode
from ..core import Ingredient

from rich.style import Style


class IngredientCell(NumericEditaleCell):
    name = ""
    default_na = 0
    read_only = False
    style_balance = True
    justify = "right"

    def access_guard(self):
        return self.vispath in self.data.node_main.ingredients

    def text_postprocess(self, text: str, style: Style) -> (str, Style):
        if text == "0":
            return ("", style)
        else:
            return (text, style)

    def get(self) -> CellValue:
        if self.access_guard():
            if self.data.node_main.clamp and self.data.node_main.clamp.name == self.vispath:
                return CellValue(self.data.node_main.clamp.count, clamped=True)
            else:
                value = self.data.node_main.ingredients[self.vispath]
                return CellValue(smartround(value))
        else:
            return CellValue(self.default_na)

    @property
    def setpath(self):
        return "node_main.clamp"

    @setpath.setter
    def setpath(self, value):
        # gets assigned to in `Cell.__ini__` ...
        ...

    def set(self, value):
        if self.data.node_main.is_module or self.data.from_module or isinstance(self.data.node_main, SummaryNode):
            return

        if self.data.node_main.clamp and self.data.node_main.clamp.name != self.vispath:
            core.APP.notify("Can't clamp two or more values\nfor a single producer", severity="warning")
            return

        super().set(Ingredient(self.vispath, value))

    def edit_delete(self) -> bool:
        if not self.is_numeric_editable:
            return

        if self.data.node_main.clamp:
            self.data.node_main.clamp = None
            self.data.node_main.clock_rate = 100

        self.data.node_main.update()
        return False

    @property
    def bounds(self):
        ingredient = None

        for inp in self.data.node_main.recipe.inputs:
            if inp.name == self.vispath:
                ingredient = inp
                self.num_sign_is_pos = False
                break

        if not ingredient:
            for inp in self.data.node_main.recipe.outputs:
                if inp.name == self.vispath:
                    ingredient = inp
                    break

        if not ingredient:
            return Bounds(0, 0)

        rate_mult = 60 / self.data.node_main.recipe.cycle_rate
        ingredient_mult_max = rate_mult * self.data.node_main.count * 250 / 100
        max_rate = ingredient.count * ingredient_mult_max
        return Bounds(0, int(abs(max_rate)))
