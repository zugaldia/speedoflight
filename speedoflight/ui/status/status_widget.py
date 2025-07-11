from gi.repository import GLib, Gtk  # type: ignore

from speedoflight.constants import DEFAULT_MARGIN, DEFAULT_SPACING


class StatusWidget(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=DEFAULT_SPACING,
        )
        self.set_margin_top(DEFAULT_MARGIN)
        self.set_margin_bottom(DEFAULT_MARGIN)
        self.set_margin_start(DEFAULT_MARGIN)
        self.set_margin_end(DEFAULT_MARGIN)

        self._status_label = Gtk.Label(label="Loading...")
        self._status_label.set_hexpand(True)
        self._status_label.set_halign(Gtk.Align.START)
        self.append(self._status_label)

        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_size_request(100, -1)
        self._progress_bar.set_show_text(False)
        self.append(self._progress_bar)

        self._pulse_timeout_id = None

    def set_status(self, status: str) -> None:
        self._status_label.set_text(status)

    def set_activity_mode(self, active: bool) -> None:
        if active:
            if self._pulse_timeout_id is None:
                self._pulse_timeout_id = GLib.timeout_add(150, self._pulse_progress_bar)
        else:
            if self._pulse_timeout_id is not None:
                GLib.source_remove(self._pulse_timeout_id)
                self._pulse_timeout_id = None
            self._progress_bar.set_fraction(0.0)

    def _pulse_progress_bar(self) -> bool:
        self._progress_bar.pulse()
        return True
