"""A small widget toolkit for building game UIs with PYDEX.

Widgets are screen-space rectangles composed from the existing drawable
primitives (filled rects, lines, and cached ``Text`` objects), so they
work on every backend and inside any :class:`~pydex_ge.core.Game`.  They
take their *input* from the frame's :class:`~pydex_ge.input.Input` object,
which the hosting scene forwards to the :class:`UIRoot`.

The toolkit is deliberately small: a scrollable panel (``ListBox``) and
an editable text field (``TextInput``) on top of a positionable panel /
label / button / vbox core.  Direct manipulation (e.g. an editor
viewport that follows the mouse every frame) is done by overriding
``poll()``.
"""

from __future__ import annotations

from ..exceptions import ConfigurationError
from ..graphics import Text


def _coord(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{name} must be an integer, got {value!r}.")
    return value


def _non_negative(value: object, name: str) -> int:
    value = _coord(value, name)
    if value < 0:
        raise ConfigurationError(f"{name} must be >= 0, got {value!r}.")
    return value


# Grayscale aliases used by the default themes.  Explicit tuples keep the
# widget layer independent from the engine's color normalization.
GRAY_BG = (38, 38, 38)
GRAY_SURFACE = (54, 54, 54)
GRAY_BORDER = (90, 90, 90)
GRAY_HOVER = (70, 70, 70)
GRAY_SELECTED = (60, 100, 160)
WHITE = (235, 235, 235)
DIM = (150, 150, 150)


class Widget:
    """Base class for every UI widget.

    A widget owns an on-screen rectangle (``x``, ``y``, ``width``,
    ``height``), an optional list of child widgets, and a ``z`` ordering
    value.  Interaction is delivered by the :class:`UIRoot`:

    * ``on_click(x, y)``  -- fired on a mouse press over the widget.
    * ``poll(input, mx, my)`` -- called every frame while the pointer
      is over the widget (for hover and drag logic).
    * ``handle_keys(input)`` -- called every frame while the widget is
      focused.

    Subclasses override these hooks; base implements only the tree and
    drawing plumbing.
    """

    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        width: int = 0,
        height: int = 0,
        visible: bool = True,
        enabled: bool = True,
    ) -> None:
        self._x = _coord(x, "x")
        self._y = _coord(y, "y")
        self._width = _non_negative(width, "width")
        self._height = _non_negative(height, "height")
        self.visible = bool(visible)
        self.enabled = bool(enabled)
        self._parent: Widget | None = None
        self.children: list[Widget] = []
        self.z = 0
        self.hit_testable: bool = True

    # -- geometry ---------------------------------------------------------

    @property
    def x(self) -> int:
        return self._x

    @x.setter
    def x(self, value: int) -> None:
        self._x = _coord(value, "x")

    @property
    def y(self) -> int:
        return self._y

    @y.setter
    def y(self, value: int) -> None:
        self._y = _coord(value, "y")

    @property
    def width(self) -> int:
        return self._width

    @width.setter
    def width(self, value: int) -> None:
        self._width = _non_negative(value, "width")

    @property
    def height(self) -> int:
        return self._height

    @height.setter
    def height(self, value: int) -> None:
        self._height = _non_negative(value, "height")

    @property
    def rect(self) -> tuple[int, int, int, int]:
        """The widget bounds as ``(x, y, width, height)``."""
        return (self.x, self.y, self.width, self.height)

    def move(self, dx: int, dy: int) -> None:
        """Shift the widget by ``(dx, dy)``."""
        self.x = self.x + _coord(dx, "dx")
        self.y = self.y + _coord(dy, "dy")

    def contains(self, px: int, py: int) -> bool:
        """Whether the screen point ``(px, py)`` falls inside the widget."""
        return (
            self.x <= px < self.x + self.width
            and self.y <= py < self.y + self.height
        )

    # -- tree -------------------------------------------------------------

    @property
    def parent(self) -> Widget | None:
        return self._parent

    def add(self, *widgets: Widget) -> Widget:
        """Add child widget(s); returns the last one added."""
        last = None
        for widget in widgets:
            if not isinstance(widget, Widget):
                raise ConfigurationError(
                    f"Children of a Widget must be Widgets, got {widget!r}."
                )
            if widget._parent is not None:
                widget._parent.remove(widget)
            widget._parent = self
            self.children.append(widget)
            last = widget
        return last

    def remove(self, widget: Widget) -> bool:
        """Detach ``widget`` if present; returns whether it was removed."""
        if widget in self.children:
            self.children.remove(widget)
            widget._parent = None
            return True
        return False

    def clear(self) -> None:
        """Detach all children."""
        for child in list(self.children):
            child._parent = None
        self.children.clear()

    def __iter__(self):
        return iter(self.children)

    def __len__(self) -> int:
        return len(self.children)

    # -- layout -----------------------------------------------------------

    def layout(self) -> None:
        """Position children; called after the tree changes."""
        for child in self.children:
            child.layout()

    # -- interaction ------------------------------------------------------

    def on_click(self, x: int, y: int) -> None:
        """Handle a mouse press inside the widget (default: ignore)."""
        return None

    def poll(self, input, mx: int, my: int) -> None:
        """Per-frame hook while the pointer is over the widget."""
        return None

    def unhover(self) -> None:
        """Called when the pointer stops being over the widget."""
        return None

    def top_widget_at(self, mx: int, my: int) -> Widget | None:
        """Deepest visible child under ``(mx, my)`` (not self), or None.

        Children are checked in the same order they are drawn (last added
        on top), so the topmost widget wins the pointer.  Decoration
        children (``hit_testable`` False) never claim the pointer, so a
        Button's inner Label cannot swallow its clicks.
        """
        for widget in reversed(sorted(self.children, key=lambda w: w.z)):
            if not widget.visible or not widget.enabled:
                continue
            if widget.contains(mx, my):
                if not widget.hit_testable:
                    inner = widget.top_widget_at(mx, my)
                    if inner is not None:
                        return inner
                    continue
                inner = widget.top_widget_at(mx, my)
                return widget if inner is None else inner
        return None

    def handle_keys(self, input) -> None:
        """Per-frame hook while the widget is focused."""
        return None

    def grabs_focus(self) -> bool:
        """Whether clicking this widget makes it the focused widget."""
        return False

    # -- rendering --------------------------------------------------------

    def draw(self, renderer) -> None:
        """Draw the widget and its children (bottom-up by ``z``)."""
        for child in sorted(self.children, key=lambda w: w.z):
            if child.visible:
                child.draw(renderer)

    def __repr__(self) -> str:
        name = type(self).__name__
        return (
            f"<{name} rect=({self.x}, {self.y}, "
            f"{self.width}, {self.height})>"
        )


class Panel(Widget):
    """A plain filled rectangle, optionally with a border."""

    def __init__(
        self,
        *,
        background: tuple[int, int, int] | None = GRAY_BG,
        border: tuple[int, int, int] | None = None,
        border_thickness: int = 1,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        if background is not None:
            background = _rgb(background)
        self.background = background
        self.border = _rgb(border) if border is not None else None
        self.border_thickness = _positive(border_thickness, "border_thickness")

    def draw(self, renderer) -> None:
        if self.background is not None:
            renderer.draw.rect(
                self.x, self.y, self.width, self.height, self.background
            )
        if self.border is not None:
            renderer.draw.rect(
                self.x,
                self.y,
                self.width,
                self.height,
                self.border,
                filled=False,
            )
        super().draw(renderer)


class Label(Widget):
    """A single line of text (with an optional background)."""

    def __init__(
        self,
        text: str = "",
        *,
        font=None,
        color: tuple[int, int, int] = WHITE,
        align: str = "left",
        valign: str = "top",
        padding: int = 0,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        if not isinstance(text, str):
            raise ConfigurationError(f"Label text must be a string, got {text!r}.")
        align, valign = _alignment(align, valign)
        self.text = text
        self.font = font
        self.color = _rgb(color)
        self.align = align
        self.valign = valign
        self.padding = _non_negative(padding, "padding")
        self._text_object: Text | None = None
        self.hit_testable = False

    def _text_key(self) -> tuple:
        return (self.text, self.color)

    def draw(self, renderer) -> None:
        if self.font is not None and self.text:
            if self._text_object is None or self._text_key() != (
                self._text_object.text,
                self._text_object.color,
            ):
                self._text_object = Text(
                    self.text, font=self.font, color=self.color
                )
            text = self._text_object
            text_w, text_h = self.font.measure(self.text)
            available_w = max(0, self.width - 2 * self.padding)
            available_h = max(0, self.height - 2 * self.padding)
            if self.align == "left":
                x = self.x + self.padding
            elif self.align == "center":
                x = self.x + (self.width - min(text_w, available_w)) // 2
            else:
                x = self.x + self.width - min(text_w, available_w) - self.padding
            if self.valign == "top":
                y = self.y + self.padding
            elif self.valign == "middle":
                y = self.y + (self.height - min(text_h, available_h)) // 2
            else:
                y = self.y + self.height - min(text_h, available_h) - self.padding
            text.x, text.y = x, y
            renderer.draw_text(text)
        super().draw(renderer)


class Button(Panel):
    """A clickable panel that highlights on hover."""

    def __init__(
        self,
        text: str = "",
        *,
        on_click=None,
        background: tuple[int, int, int] = GRAY_SURFACE,
        hover: tuple[int, int, int] = GRAY_HOVER,
        border: tuple[int, int, int] = GRAY_BORDER,
        font=None,
        text_color: tuple[int, int, int] = WHITE,
        **kwargs,
    ) -> None:
        if text and "width" not in kwargs and font is not None:
            kwargs.setdefault("width", font.measure(text)[0] + 20)
        super().__init__(background=background, border=border, **kwargs)
        self.text = text
        self.hover = _rgb(hover)
        self._callback = on_click
        self.font = font
        self.text_color = _rgb(text_color)
        self.hovered = False
        self.label = self.add(
            Label(
                text,
                font=font,
                color=text_color,
                align="center",
                valign="middle",
                width=self.width,
                height=self.height,
            )
        )

    def poll(self, input, mx: int, my: int) -> None:
        self.hovered = True

    def unhover(self) -> None:
        self.hovered = False

    def on_click(self, x: int, y: int) -> None:
        if self._callback is not None:
            self._callback()

    def draw(self, renderer) -> None:
        self.label.x, self.label.y = self.x, self.y
        self.label.width, self.label.height = self.width, self.height
        if self.hovered:
            renderer.draw.rect(
                self.x, self.y, self.width, self.height, self.hover
            )
            renderer.draw.rect(
                self.x, self.y, self.width, self.height, self.border, filled=False
            )
            super(Panel, self).draw(renderer)
            return
        super().draw(renderer)


class TextInput(Panel):
    """A single-line editable text field.

    Editing state is pure Python (``value``/``caret``) so it can be
    exercised in unit tests without a window.  Use it by clicking the
    field (it grabs focus), then typing; ``TEXT_INPUT`` events carry
    already-shifted characters from the OS.
    """

    def __init__(
        self,
        value: str = "",
        *,
        placeholder: str = "",
        max_length: int | None = None,
        on_change=None,
        on_submit=None,
        font=None,
        text_color: tuple[int, int, int] = WHITE,
        placeholder_color: tuple[int, int, int] = DIM,
        caret_color: tuple[int, int, int] = WHITE,
        background: tuple[int, int, int] = GRAY_SURFACE,
        border: tuple[int, int, int] = GRAY_BORDER,
        **kwargs,
    ) -> None:
        super().__init__(background=background, border=border, **kwargs)
        if not isinstance(value, str):
            raise ConfigurationError(
                f"TextInput value must be a string, got {value!r}."
            )
        if max_length is not None and (
            isinstance(max_length, bool) or not isinstance(max_length, int) or max_length < 0
        ):
            raise ConfigurationError("max_length must be a non-negative integer.")
        self.value = value
        self.caret = len(value)
        self._sel_anchor: int | None = None
        self.placeholder = placeholder if isinstance(placeholder, str) else ""
        self.max_length = max_length
        self.on_change = on_change
        self.on_submit = on_submit
        self.font = font
        self.text_color = _rgb(text_color)
        self.placeholder_color = _rgb(placeholder_color)
        self.caret_color = _rgb(caret_color)
        self.focused = False
        # The value label is positioned and painted inside ``draw``, so it is
        # kept OUT of ``children``; otherwise the base ``Widget.draw`` would
        # also render it with stale text before we reset it each frame.
        self.label = Label(font=font, width=self.width, height=self.height)

    def _text_width(self, text: str) -> int:
        if not text or self.font is None:
            return 0
        return self.font.measure(text)[0]

    def _caret_x(self) -> int:
        return self.x + 6 + self._text_width(self.value[: self.caret])

    def grabs_focus(self) -> bool:
        return True

    def on_click(self, x: int, y: int) -> None:
        if self.font is None or not self.value:
            self.caret = len(self.value)
            self._sel_anchor = 0 if self.value else None
            return
        self.caret = len(self.value)
        self._sel_anchor = 0

    def handle_keys(self, input) -> None:
        if not self.enabled:
            return
        before = self.value
        caret = self.caret
        anchor = self._sel_anchor
        for chunk in input.text_events:
            for char in chunk:
                if char in ("\r", "\n"):
                    if self.on_submit is not None:
                        self.on_submit(self.value)
                    continue
                if char in ("\t", "\x00"):
                    continue
                if anchor is not None and anchor != caret:
                    lo, hi = sorted((anchor, caret))
                    self.value = self.value[:lo] + char + self.value[hi:]
                    caret = lo + 1
                    anchor = None
                    continue
                if self.max_length is not None and len(self.value) >= self.max_length:
                    break
                self.value = self.value[:caret] + char + self.value[caret:]
                caret += 1
        if input.is_key_pressed("left"):
            if anchor is not None and anchor < caret:
                caret = anchor
            else:
                caret = max(0, caret - 1)
            anchor = None
        elif input.is_key_pressed("right"):
            if anchor is not None and anchor > caret:
                caret = anchor
            else:
                caret = min(len(self.value), caret + 1)
            anchor = None
        elif input.is_key_pressed("home"):
            caret = 0
            anchor = None
        elif input.is_key_pressed("end"):
            caret = len(self.value)
            anchor = None
        elif input.is_key_pressed("backspace"):
            if anchor is not None and anchor != caret:
                lo, hi = sorted((anchor, caret))
                self.value = self.value[:lo] + self.value[hi:]
                caret = lo
                anchor = None
            elif caret > 0:
                self.value = self.value[: caret - 1] + self.value[caret:]
                caret -= 1
        elif input.is_key_pressed("delete"):
            if anchor is not None and anchor != caret:
                lo, hi = sorted((anchor, caret))
                self.value = self.value[:lo] + self.value[hi:]
                caret = lo
                anchor = None
            elif caret < len(self.value):
                self.value = self.value[:caret] + self.value[caret + 1 :]
        self.caret = min(caret, len(self.value))
        self._sel_anchor = anchor
        if self.value != before and self.on_change is not None:
            self.on_change(self.value)

    def draw(self, renderer) -> None:
        super().draw(renderer)
        self.label.x, self.label.y = self.x + 6, self.y + 6
        self.label.width, self.label.height = max(0, self.width - 12), max(1, self.height - 12)
        if self.value:
            self.label.color = self.text_color
            self.label.text = self.value
        elif self.placeholder:
            self.label.color = self.placeholder_color
            self.label.text = self.placeholder
        else:
            self.label.text = ""
        self.label.draw(renderer)
        if self.focused:
            renderer.draw.line(
                self._caret_x(),
                self.y + 4,
                self._caret_x(),
                self.y + self.height - 4,
                self.caret_color,
            )


class ListBox(Panel):
    """A vertical list of selectable rows (with clipping scroll)."""

    def __init__(
        self,
        items=None,
        *,
        item_height: int = 22,
        padding: int = 4,
        on_select=None,
        font=None,
        background: tuple[int, int, int] = GRAY_BG,
        border: tuple[int, int, int] = GRAY_BORDER,
        selected_color: tuple[int, int, int] = GRAY_SELECTED,
        **kwargs,
    ) -> None:
        super().__init__(background=background, border=border, **kwargs)
        self.item_height = _positive(item_height, "item_height")
        self.padding = _non_negative(padding, "padding")
        self.on_select = on_select
        self.font = font
        self.selected_color = _rgb(selected_color)
        self._items: list[tuple[object, str]] = []
        self.selected: object | None = None
        self.scroll = 0
        if items:
            for item in items:
                self.append(item)
        # Same as TextInput: the row label is painted per-row inside ``draw``,
        # so it must not be a child (the base draw would paint stale text).
        self.label = Label(font=font)

    def append(self, item) -> None:
        """Append ``item`` (a string, or an ``(id, label)`` pair)."""
        if isinstance(item, (tuple, list)) and len(item) == 2:
            item_id, label = item
            if not isinstance(label, str):
                raise ConfigurationError(f"ListBox labels must be strings, got {label!r}.")
        else:
            item_id, label = item, str(item)
        self._items.append((item_id, label))

    def clear(self) -> None:
        """Clear the items and selection."""
        super().clear()
        self._items.clear()
        self.selected = None
        self.scroll = 0

    def __len__(self) -> int:
        return len(self._items)

    @property
    def visible_rows(self) -> int:
        """How many rows fit in the viewport."""
        if self.item_height <= 0:
            return 0
        return max(1, (self.height - 2 * self.padding) // self.item_height)

    def _row_index_at(self, x: int, y: int) -> int | None:
        row = (y - self.y - self.padding) // self.item_height
        index = self.scroll + row
        if 0 <= index < len(self._items):
            return index
        return None

    def on_click(self, x: int, y: int) -> None:
        try:
            index = self._row_index_at(x, y)
        except ZeroDivisionError:
            return
        if index is None:
            self.selected = None
            return
        item_id = self._items[index][0]
        self.selected = item_id
        if self.on_select is not None:
            self.on_select(item_id)

    def draw(self, renderer) -> None:
        super().draw(renderer)
        first = max(0, self.scroll)
        last = min(len(self._items), first + self.visible_rows)
        for index in range(first, last):
            item_id, label_text = self._items[index]
            row_y = self.y + self.padding + (index - first) * self.item_height
            if self.selected is item_id or self.selected == item_id:
                renderer.draw.rect(
                    self.x + self.padding,
                    row_y,
                    max(1, self.width - 2 * self.padding),
                    self.item_height,
                    self.selected_color,
                )
            self.label.text = label_text
            self.label.x = self.x + self.padding + 4
            self.label.y = row_y + (self.item_height - self.font.measure(label_text)[1]) // 2 if self.font else row_y
            self.label.width = max(0, self.width - 2 * self.padding - 4)
            self.label.height = max(1, self.item_height)
            self.label.draw(renderer)


class VBox(Widget):
    """Stacks children top-to-bottom with spacing."""

    def __init__(
        self,
        *,
        spacing: int = 4,
        padding: int = 4,
        fill_width: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.spacing = _non_negative(spacing, "spacing")
        self.padding = _non_negative(padding, "padding")
        self.fill_width = bool(fill_width)

    def add(self, widget: Widget) -> Widget:
        super().add(widget)
        if self.fill_width and self.width:
            widget.width = self.width - 2 * self.padding
        return widget

    def layout(self) -> None:
        y = self.y + self.padding
        visible = []
        for child in self.children:
            if not child.visible:
                continue
            visible.append(child)
            if self.fill_width and self.width:
                child.width = self.width - 2 * self.padding
            child.y = y
            child.x = self.x + self.padding
            y += child.height + self.spacing
            child.layout()
        if self.height == 0 and visible:
            self.height = (
                sum(child.height for child in visible)
                + self.spacing * (len(visible) - 1)
                + 2 * self.padding
            )


class UIRoot(Widget):
    """Top-level widget that forwards a frame's ``Input`` to the tree.

    Owns the *focused* widget and dispatches clicks to the topmost
    widget under the pointer.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._focused: Widget | None = None
        self._hovered: Widget | None = None

    @property
    def focused(self) -> Widget | None:
        return self._focused

    def focus(self, widget: Widget | None) -> None:
        """Set/clear the focused widget."""
        self._focused = widget

    def blur(self) -> None:
        self._focused = None

    def top_widget_at(self, mx: int, my: int) -> Widget | None:
        """Deepest visible widget under ``(mx, my)``, or None."""
        return super().top_widget_at(mx, my)

    def handle_input(self, input) -> bool:
        """Drive the tree with a frame's ``Input``; returns True if handled."""
        mx, my = input.mouse_position
        hovered = self.top_widget_at(mx, my)
        if hovered is not None and not hovered.enabled:
            hovered = None
        previous = self._hovered
        self._hovered = hovered
        if previous is not None and previous is not hovered:
            previous.unhover()
        if hovered is not None:
            hovered.poll(input, mx, my)
        if input.is_button_pressed("left"):
            target = hovered
            if target is None:
                self.blur()
            else:
                self.focus(target if target.grabs_focus() else None)
                target.on_click(mx, my)
        focused = self._focused
        if focused is not None and (not focused.enabled or not focused.visible):
            self.blur()
            focused = None
        if focused is not None:
            focused.handle_keys(input)
        return hovered is not None


def _rgb(color: tuple[int, int, int]) -> tuple[int, int, int]:
    if isinstance(color, bool) or not isinstance(color, (tuple, list)) or len(color) not in (3, 4):
        raise ConfigurationError(f"Color must be an RGB(A) tuple, got {color!r}.")
    channels = []
    for index, channel in enumerate(color):
        if isinstance(channel, bool) or not isinstance(channel, int) or not 0 <= channel <= 255:
            raise ConfigurationError(
                f"Color channel {index} must be an int in 0-255, got {channel!r}."
            )
        channels.append(channel)
    return (channels[0], channels[1], channels[2])


def _positive(value: object, name: str) -> int:
    value = _coord(value, name)
    if value <= 0:
        raise ConfigurationError(f"{name} must be >= 1, got {value!r}.")
    return value


def _alignment(align: str, valign: str) -> tuple[str, str]:
    if align not in ("left", "center", "right"):
        raise ConfigurationError(
            f"align must be 'left', 'center' or 'right', got {align!r}."
        )
    if valign not in ("top", "middle", "bottom"):
        raise ConfigurationError(
            f"valign must be 'top', 'middle' or 'bottom', got {valign!r}."
        )
    return align, valign


__all__ = [
    "Widget",
    "Panel",
    "Label",
    "Button",
    "TextInput",
    "ListBox",
    "VBox",
    "UIRoot",
    "GRAY_BG",
    "GRAY_SURFACE",
    "GRAY_BORDER",
    "GRAY_HOVER",
    "GRAY_SELECTED",
    "WHITE",
    "DIM",
]