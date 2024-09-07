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
            return self.data.node_main.ingredients[self.vispath]
        else:
            return self.default_na
