# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from ._cells import (
    NumericEditaleCell,
    Bounds,
)


class MkCell(NumericEditaleCell):
    name = "Mk"
    vispath = "node_main.mk"
    bounds = Bounds(1, 3)

    def access_guard(self):
        return self.data.node_main.producer.is_miner and super().access_guard()
