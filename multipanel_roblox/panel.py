import curses
import time
from typing import Any, Optional


class PanelDashboard:
    def __init__(self, stdscr: Any, universes: list[dict]):
        self.stdscr = stdscr
        self.universes = universes
        self.active_idx = 0
        self.focus_pane = 0  # 0: left sidebar, 1: log viewer, 2: datastore explorer
        self.logs: list[str] = []
        self.keys: list[str] = []
        self.key_scroll_offset = 0
        self.log_scroll_offset = 0
        self.selected_key_idx = 0
        self.status_line = "[Tab] Pane | [j/k] Nav | [Enter] Inspect | [r] Refresh | [q] Quit"
        self._inspect_modal: Optional[str] = None

    def set_keys(self, keys: list[str]):
        self.keys = keys
        self.selected_key_idx = 0
        self.key_scroll_offset = 0

    def add_log(self, text: str):
        ts = time.strftime("%H:%M:%S")
        self.logs.append(f"[{ts}] {text}")
        if len(self.logs) > 1000:
            self.logs.pop(0)

    def show_modal(self, content: str):
        self._inspect_modal = content

    def close_modal(self):
        self._inspect_modal = None

    def handle_input(self, ch: int) -> Optional[str]:
        if self._inspect_modal is not None:
            if ch in (ord("q"), 27, ord(" "), 10):
                self.close_modal()
            return None

        if ch == ord("\t"):
            self.focus_pane = (self.focus_pane + 1) % 3
        elif ch in (curses.KEY_DOWN, ord("j")):
            if self.focus_pane == 0 and self.universes:
                self.active_idx = min(self.active_idx + 1, len(self.universes) - 1)
                return "universe_change"
            elif self.focus_pane == 2 and self.keys:
                self.selected_key_idx = min(self.selected_key_idx + 1, len(self.keys) - 1)
        elif ch in (curses.KEY_UP, ord("k")):
            if self.focus_pane == 0 and self.universes:
                self.active_idx = max(self.active_idx - 1, 0)
                return "universe_change"
            elif self.focus_pane == 2 and self.keys:
                self.selected_key_idx = max(self.selected_key_idx - 1, 0)
        elif ch == 10:  # Enter
            if self.focus_pane == 2 and self.keys:
                return "inspect_key"
        elif ch == ord("r"):
            return "refresh"
        elif ch == curses.KEY_RESIZE:
            # curses handles terminal size update internally
            curses.update_lines_cols()
        return None

    def render(self):
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()

        if h < 14 or w < 65:
            self.stdscr.addstr(0, 0, "Terminal too small. Need at least 65x14.")
            self.stdscr.refresh()
            return

        left_w = min(32, w // 3)
        right_w = w - left_w - 1
        mid_h = (h - 2) // 2

        # 0: Left Pane (Universes)
        self._draw_box(0, 0, h - 2, left_w, "Universes (1)", self.focus_pane == 0)
        for idx, u in enumerate(self.universes[: h - 5]):
            marker = "> " if idx == self.active_idx else "  "
            name = u.get("name", f"Universe {u.get('id')}")
            line_text = f"{marker}{name}"
            attr = curses.A_REVERSE if idx == self.active_idx else curses.A_NORMAL
            self._safe_addstr(idx + 1, 2, line_text, left_w - 4, attr)

        # 1: Top Right (Logs)
        self._draw_box(0, left_w + 1, mid_h, right_w, "Cloud Logs / Live Tail (2)", self.focus_pane == 1)
        visible_log_count = mid_h - 2
        log_slice = self.logs[-visible_log_count:] if visible_log_count > 0 else []
        for idx, line in enumerate(log_slice):
            self._safe_addstr(idx + 1, left_w + 3, line, right_w - 4)

        # 2: Bottom Right (Datastore)
        bot_y = mid_h
        bot_h = h - 2 - mid_h
        self._draw_box(bot_y, left_w + 1, bot_h, right_w, "Datastore Entries (3)", self.focus_pane == 2)
        
        max_entries = bot_h - 2
        if self.selected_key_idx >= self.key_scroll_offset + max_entries:
            self.key_scroll_offset = self.selected_key_idx - max_entries + 1
        elif self.selected_key_idx < self.key_scroll_offset:
            self.key_scroll_offset = self.selected_key_idx

        for slot, idx in enumerate(range(self.key_scroll_offset, min(len(self.keys), self.key_scroll_offset + max_entries))):
            key_name = self.keys[idx]
            is_sel = idx == self.selected_key_idx and self.focus_pane == 2
            prefix = "-> " if is_sel else "   "
            attr = curses.A_STANDOUT if is_sel else curses.A_NORMAL
            self._safe_addstr(bot_y + 1 + slot, left_w + 3, f"{prefix}{key_name}", right_w - 5, attr)

        # Modal popup
        if self._inspect_modal:
            self._draw_modal(h, w)

        # Status footer
        self._safe_addstr(h - 1, 0, self.status_line, w - 1, curses.A_DIM)
        self.stdscr.refresh()

    def _safe_addstr(self, y: int, x: int, text: str, max_len: int, attr: int = curses.A_NORMAL):
        try:
            self.stdscr.addstr(y, x, text[:max_len], attr)
        except curses.error:
            pass

    def _draw_box(self, y: int, x: int, h: int, w: int, title: str, focused: bool):
        attr = curses.A_BOLD if focused else curses.A_DIM
        try:
            self.stdscr.addstr(y, x, "+" + "-" * (w - 2) + "+", attr)
            for row in range(1, h - 1):
                self.stdscr.addstr(y + row, x, "|", attr)
                self.stdscr.addstr(y + row, x + w - 1, "|", attr)
            self.stdscr.addstr(y + h - 1, x, "+" + "-" * (w - 2) + "+", attr)
            t_label = f" {title} "
            if len(t_label) < w - 4:
                self.stdscr.addstr(y, x + 2, t_label, curses.A_BOLD if focused else curses.A_NORMAL)
        except curses.error:
            pass

    def _draw_modal(self, max_h: int, max_w: int):
        modal_w = min(70, max_w - 8)
        modal_h = min(20, max_h - 6)
        start_y = (max_h - modal_h) // 2
        start_x = (max_w - modal_w) // 2

        # Fill background
        for row in range(modal_h):
            self._safe_addstr(start_y + row, start_x, " " * modal_w, modal_w, curses.A_REVERSE)

        self._draw_box(start_y, start_x, modal_h, modal_w, "Entry Payload (press Esc or q)", True)
        lines = (self._inspect_modal or "").split("\n")
        for idx, l in enumerate(lines[: modal_h - 4]):
            self._safe_addstr(start_y + 2 + idx, start_x + 3, l, modal_w - 6, curses.A_NORMAL)
