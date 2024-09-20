# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .. import (
    press_before,
    checkpoints,
)

from production_planner import Planner

import pytest


@pytest.mark.parametrize("keys", list(checkpoints((["down"] * 1 + ["f2"] * 2,
                                                   ["f3"],
                                                   ["down"] * 1 + ["f2"] * 2,
                                                   ["f3"],
                                                   ["down"] * 8 + ["f2"],)))
                                 + [["down"] + ["f2"] * 14 + ["f3"]])
def test_module_hide_show(snap_compare, keys):
    assert snap_compare(Planner(), terminal_size=(150, 30), run_before=press_before(keys))
