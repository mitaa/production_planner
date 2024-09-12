# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .. import press_before

from production_planner import Planner

import pytest


@pytest.mark.parametrize("keys", (["s", "enter", "enter"],))
def test_save_with_module(snap_compare, keys):
    assert snap_compare(Planner(testrun=True), terminal_size=(150, 30), run_before=press_before(keys))
