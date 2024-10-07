# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.


from ._cells import (
    NumericEditaleCell,
    Bounds,
    CellValue,
)
from ..core import smartround


class ClockRateCell(NumericEditaleCell):
    name = "Clockrate"
    vispath = "node_main.clock_rate"

    def access_guard(self):
        return not self.data.node_main.producer.is_module and super().access_guard()

    def get(self) -> CellValue:
        value: CellValue = super().get()

        if value.value:
            # FIXME: value ** 3
            value.value = smartround(value.value.value)

        if self.data.node_main.clamp:
            value.text = f"<{value.value}>"
        return value
