# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from production_planner import Planner


async def test_startup():
    app = Planner()
    async with app.run_test() as pilot:
        pass


def test_startup_screen(snap_compare):
    app = Planner()
    assert snap_compare(app, terminal_size=(150, 30), press=[])


def test_load_screen(snap_compare):
    app = Planner()
    assert snap_compare(app, terminal_size=(150, 30), press=["t", "down", "enter"])


def test_save_screen(snap_compare):
    app = Planner()
    assert snap_compare(app, terminal_size=(150, 30), press=["t", "enter"])


def test_producer_screen(snap_compare):
    app = Planner()
    assert snap_compare(app, terminal_size=(150, 30), press=["down", "enter"])


def test_recipe_screen(snap_compare):
    app = Planner()
    assert snap_compare(app, terminal_size=(150, 30), press=["down", "right", "enter"])


def test_purity_screen(snap_compare):
    app = Planner()
    assert snap_compare(app, terminal_size=(150, 30), press=["down"] + (["right"] * 4) + ["enter"])
