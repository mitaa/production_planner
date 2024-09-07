# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from ._cells import Cell

from rich.style import Style


class IngredientCell(Cell):
    name = ""
    default_na = 0
    read_only = True
    style_balance = True
    justify = "right"

    def access_guard(self):
        return self.vispath in self.data.node_main.ingredients

    def text_postprocess(self, text: str, style: Style) -> (str, Style):
        if text == "0":
            return ("", style)
        else:
            return (text, style)

    def get(self):
        if self.access_guard():
            value = self.data.node_main.ingredients[self.vispath]
            truncated_value = int(value)
            if value - truncated_value < 0.01:
                return truncated_value
            else:
                return round(value, 2)
        else:
            return self.default_na
