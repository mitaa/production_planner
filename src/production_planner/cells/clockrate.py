# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.


from ._cells import NumericEditaleCell, Bounds


class ClockRateCell(NumericEditaleCell):
    name = "Clockrate"
    vispath = "node_main.clock_rate"
    bounds = Bounds(0, 250)

    def access_guard(self):
        return not self.data.node_main.producer.is_module and super().access_guard()
