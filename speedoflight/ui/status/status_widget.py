from gi.repository import Gtk  # type: ignore

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

    def set_status(self, status: str) -> None:
        self._status_label.set_text(status)

    def pulse_progress_bar(self) -> bool:
        self._progress_bar.pulse()
        return True

    def set_fraction(self, fraction: float) -> None:
        self._progress_bar.set_fraction(fraction)
