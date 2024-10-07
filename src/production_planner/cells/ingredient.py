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
from ..core import (
    smartround,
    get_path,
    set_path,
    SummaryNode,
    Ingredient,
)

from ..core.node import EditClampValue

from rich.style import Style


def strike(text):
    result = ''
    for c in text:
        result = result + c + '\u0336'
    return result


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
            value = smartround(self.data.node_main.ingredients[self.vispath])

            if self.data.node_main.clamp and self.data.node_main.clamp.value.name == self.vispath:
                clamp_count = self.data.node_main.clamp.value.count
                if abs(abs(value) - abs(clamp_count)) > 0.01:
                    # FIXME: DataTable doesn't seem to handle strikethrough very well (small part of the next row is shifted to this one)
                    return CellValue(value, text=f"{value} !", clamped=True)
                else:
                    return CellValue(value, clamped=True)
            else:
                return CellValue(value)
        else:
            return CellValue(self.default_na)

    @property
    def setpath(self):
        return "node_main.clamp"

    @setpath.setter
    def setpath(self, value):
        # gets assigned to in `Cell.__init__` ...
        ...

    def set_guard(self, fn: callable):
        if not self.access_guard() or self.data.node_main.is_module or self.data.from_module or isinstance(self.data.node_main, SummaryNode):
            return False

        if self.data.node_main.clamp and self.data.node_main.clamp.value.name != self.vispath:
            core.APP.notify("Can't clamp two or more values\nfor a single producer", severity="warning")
            return

        if self.read_only:  # FIXME: warn, rather than error
            raise TypeError("Cell is Read-Only !")

        edit_value = get_path(self.data, self.setpath or self.vispath)
        if not edit_value:
            edit_value = EditClampValue(Ingredient(self.vispath, smartround(self.data.node_main.ingredients[self.vispath])))
            set_path(self.data, self.setpath, edit_value)

        return fn(edit_value)

    def edit_delete(self) -> bool:
        if not self.is_numeric_editable:
            return

        if self.data.node_main.clamp:
            self.data.node_main.clamp = None
            self.data.node_main.clock_rate.value = 100

        self.data.node_main.update()
        return False
