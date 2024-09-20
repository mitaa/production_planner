#! /bin/env python
# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from textual.app import RenderResult
from textual.events import Mount
from textual import widgets
from textual.widget import Widget
from textual.widgets._header import HeaderClockSpace, HeaderIcon, HeaderTitle

from rich.text import Text


class HiddenLabel(Widget):
    """Display a hidden item count on the right of the header."""

    DEFAULT_CSS = """
    HiddenLabel {
        dock: right;
        padding: 0 1;
        content-align: left middle;
        width: 18;
        background: $foreground-darken-1 0%;
        color: $text;
        text-opacity: 85%;
        content-align: left middle;
    }
    """

    # def _on_mount(self, _: Mount) -> None:
    #     self.set_interval(1, callback=self.refresh, name="update header clock")

    def render(self) -> RenderResult:
        """Render the header clock.

        Returns:
            The rendered clock.
        """
        count = self.app.hidden_item_count
        if count:
            return Text(f"{self.app.hidden_item_count} hidden items")
        else:
            return ""


class Header(widgets.Header):
    def compose(self):
        yield HeaderIcon().data_bind(widgets.Header.icon)
        yield HeaderTitle()
        yield HiddenLabel()

    def _on_mount(self, _: Mount) -> None:
        async def update_hidden_label() -> None:
            label = self.query_one(HiddenLabel)
            label.refresh()

        self.watch(self.app, "hidden_item_count", update_hidden_label)
