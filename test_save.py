# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from . import nottest

from production_planner import Planner


# FIXME
@nottest
def test_save_file(snap_compare):
    async def run_before1(pilot):
        for k in ["+", "t", "s"]:
            await pilot.press(k)
        await pilot.pause(1)

        for k in ["tab", "down", "tab"] + ["backspace"] * 15 + list("testers") + ["enter"]:
            await pilot.press(k)

    async def run_before2(pilot):
        for k in ["down", "down", "down"]:
            await pilot.press(k)

    assert snap_compare(Planner(testrun=True), terminal_size=(150, 30))
    assert snap_compare(Planner(testrun=True), terminal_size=(150, 30), run_before=run_before1)
    assert snap_compare(Planner(testrun=True), terminal_size=(150, 30), run_before=run_before2)
