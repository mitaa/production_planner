# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from . import nottest

from production_planner import Planner


# FIXME: failure seemingly not reproducible manually
@nottest
def test_load_file(snap_compare):
    async def run_before(pilot):
        for k in ["t", "l", "up", "enter"]:
            await pilot.press(k)
    assert snap_compare(Planner(testrun=True), terminal_size=(150, 30), run_before=run_before)
