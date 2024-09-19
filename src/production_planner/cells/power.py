# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from ._cells import Cell, CellValue
from ..core import get_path

import math


class PowerCell(Cell):
    name = "-Power"
    vispath = "node_main.energy"
    read_only = True
    justify = "right"

    def get(self) -> CellValue:
        if self.access_guard():
            value = get_path(self.data, self.vispath)
            return CellValue(math.ceil(value))
        else:
            return CellValue(self.default_na)
