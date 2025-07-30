import base64
import logging
from typing import Optional

from gi.repository import Adw, GdkPixbuf, Gtk, GtkSource, Pango  # type: ignore

from speedoflight.constants import DEFAULT_MARGIN

_markdown_language = None
_markdown_style_scheme = None


def _get_markdown_resources():
    global _markdown_language, _markdown_style_scheme

    if _markdown_language is None:
        language_manager = GtkSource.LanguageManager.get_default()
        _markdown_language = language_manager.get_language("markdown")

    if _markdown_style_scheme is None:
        adw_style_manager = Adw.StyleManager.get_default()
        scheme = "Adwaita-dark" if adw_style_manager.get_dark() else "Adwaita"
        style_manager = GtkSource.StyleSchemeManager.get_default()
        _markdown_style_scheme = style_manager.get_scheme(scheme)

    return _markdown_language, _markdown_style_scheme


class ChatBaseWidget(Gtk.Box):
    def __init__(self) -> None:
        Gtk.Box.__init__(self)
        self._logger = logging.getLogger(__name__)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_margin_top(DEFAULT_MARGIN)
        self.set_margin_bottom(DEFAULT_MARGIN)
        self.set_margin_start(DEFAULT_MARGIN)
        self.set_margin_end(DEFAULT_MARGIN)

    def _get_default_label(self) -> Gtk.Label:
        label = Gtk.Label()
        label.set_wrap(True)
        label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        label.set_xalign(0.0)
        label.set_selectable(True)
        return label

    def _get_icon_name(self, icon_name: str, is_error: bool = False) -> str:
        return "dialog-error-symbolic" if is_error else icon_name

    def _add_plain_text(self, text: str, class_name: str) -> None:
        label = self._get_default_label()
        label.get_style_context().add_class(class_name)
        label.set_text(text)
        self.append(label)

    def _add_markdown_text(self, text: str) -> None:
        buffer = GtkSource.Buffer()
        buffer.set_text(text)
        markdown_language, markdown_style_scheme = _get_markdown_resources()
        if markdown_language:
            buffer.set_language(markdown_language)
        if markdown_style_scheme:
            buffer.set_style_scheme(markdown_style_scheme)

        view = GtkSource.View()
        view.set_buffer(buffer)
        view.set_editable(False)
        view.set_cursor_visible(False)
        view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        view.get_style_context().add_class("markdown-message")
        self.append(view)

    def _add_expandable_text(
        self,
        title: str,
        subtitle: str,
        content: str,
        class_name: str,
        icon_name: str,
        expanded: bool = False,
    ) -> None:
        row = Adw.ExpanderRow()
        row.set_title(title)
        row.set_subtitle(subtitle)
        row.set_expanded(expanded)

        icon = Gtk.Image()
        icon.set_from_icon_name(icon_name)
        icon.set_icon_size(Gtk.IconSize.NORMAL)
        row.add_prefix(icon)

        label = self._get_default_label()
        label.set_margin_top(DEFAULT_MARGIN)
        label.set_margin_bottom(DEFAULT_MARGIN)
        label.set_margin_start(DEFAULT_MARGIN)
        label.set_margin_end(DEFAULT_MARGIN)
        label.get_style_context().add_class(class_name)
        label.set_text(content)
        row.add_row(label)

        self.append(row)

    def _base64_to_pixbuf(
        self, base64_data: str, mime_type: str
    ) -> Optional[GdkPixbuf.Pixbuf]:
        try:
            # Extract format from MIME type (e.g., "image/png" -> "png")
            image_format = mime_type.split("/")[-1].lower()
            image_data = base64.b64decode(base64_data)
            loader = GdkPixbuf.PixbufLoader.new_with_type(image_format)
            loader.write(image_data)
            loader.close()
            return loader.get_pixbuf()
        except Exception as e:
            self._logger.error(f"Failed to decode base64 image: {e}")
            return None

    def _add_expandable_image(
        self,
        title: str,
        subtitle: str,
        data: str,
        mime_type: str,
        class_name: str,
        icon_name: str,
        expanded: bool = True,
    ) -> None:
        row = Adw.ExpanderRow()
        row.set_title(title)
        row.set_subtitle(subtitle)
        row.set_expanded(expanded)

        icon = Gtk.Image()
        icon.set_from_icon_name(icon_name)
        icon.set_icon_size(Gtk.IconSize.NORMAL)
        row.add_prefix(icon)

        pixbuf = self._base64_to_pixbuf(data, mime_type)
        if pixbuf:
            picture = Gtk.Picture()
            picture.set_pixbuf(pixbuf)
            picture.set_content_fit(Gtk.ContentFit.SCALE_DOWN)
            picture.set_can_shrink(True)
            # TODO: Resize if larger than the window width
            picture.set_size_request(pixbuf.get_width(), pixbuf.get_height())
            picture.set_margin_top(DEFAULT_MARGIN)
            picture.set_margin_bottom(DEFAULT_MARGIN)
            picture.set_margin_start(DEFAULT_MARGIN)
            picture.set_margin_end(DEFAULT_MARGIN)
            row.add_row(picture)
        else:
            label = self._get_default_label()
            label.set_margin_top(DEFAULT_MARGIN)
            label.set_margin_bottom(DEFAULT_MARGIN)
            label.set_margin_start(DEFAULT_MARGIN)
            label.set_margin_end(DEFAULT_MARGIN)
            label.get_style_context().add_class(class_name)
            label.set_text("Failed to load image.")
            row.add_row(label)

        self.append(row)
