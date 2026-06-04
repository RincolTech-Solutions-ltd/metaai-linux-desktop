import os
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gtk, WebKit2, Gdk, GLib
import settings

ICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
META_AI_URL = "https://www.meta.ai/"

# Force dark on any website — invert everything, then un-invert media so images stay correct
_DARK_CSS = """
html {
    filter: invert(93%) hue-rotate(180deg) !important;
    background: #fff !important;
}
img, video, canvas, svg, picture, iframe {
    filter: invert(100%) hue-rotate(180deg) !important;
}
"""

_DARK_JS_LIVE = """
(function(){
    var s = document.getElementById('__metaai_dark');
    if (!s) {
        s = document.createElement('style');
        s.id = '__metaai_dark';
        document.head.appendChild(s);
    }
    s.textContent = 'html{filter:invert(93%) hue-rotate(180deg)!important;background:#fff!important;}img,video,canvas,svg,picture,iframe{filter:invert(100%) hue-rotate(180deg)!important;}';
})();
"""

_LIGHT_JS_LIVE = """
(function(){
    var s = document.getElementById('__metaai_dark');
    if (s) s.remove();
})();
"""


class MetaAIWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="MetaAI")
        self.prefs = settings.load()
        self._setup_window()
        self._setup_webview()
        self._setup_toolbar()
        self._setup_layout()
        self._setup_shortcuts()
        self._restore_position()

    def _setup_window(self):
        self.set_default_size(self.prefs["window_width"], self.prefs["window_height"])
        self.set_icon_from_file(ICON_PATH) if os.path.exists(ICON_PATH) else None
        self.connect("delete-event", self._on_close)
        self.connect("configure-event", self._on_configure)

    def _setup_webview(self):
        ctx = WebKit2.WebContext.get_default()
        ctx.set_cache_model(WebKit2.CacheModel.WEB_BROWSER)

        cookie_mgr = ctx.get_cookie_manager()
        cookie_path = os.path.expanduser("~/.config/metaai-desktop/cookies.sqlite")
        cookie_mgr.set_persistent_storage(cookie_path, WebKit2.CookiePersistentStorage.SQLITE)

        self._cm = WebKit2.UserContentManager()
        self.webview = WebKit2.WebView.new_with_user_content_manager(self._cm)

        ws = self.webview.get_settings()
        ws.set_enable_javascript(True)
        ws.set_enable_media_stream(True)
        ws.set_enable_webaudio(True)
        ws.set_hardware_acceleration_policy(WebKit2.HardwareAccelerationPolicy.ALWAYS)

        self.webview.set_zoom_level(self.prefs["zoom_level"])

        # apply dark/light before first load
        self._apply_theme(self.prefs["dark_mode"])

        self.webview.load_uri(META_AI_URL)

    def _setup_toolbar(self):
        self.toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.toolbar.set_margin_start(6)
        self.toolbar.set_margin_end(6)
        self.toolbar.set_margin_top(4)
        self.toolbar.set_margin_bottom(4)

        btn_back = Gtk.Button.new_from_icon_name("go-previous-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        btn_back.connect("clicked", lambda _: self.webview.go_back())
        btn_back.set_tooltip_text("Back (Alt+←)")

        btn_fwd = Gtk.Button.new_from_icon_name("go-next-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        btn_fwd.connect("clicked", lambda _: self.webview.go_forward())
        btn_fwd.set_tooltip_text("Forward (Alt+→)")

        btn_reload = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        btn_reload.connect("clicked", lambda _: self.webview.reload())
        btn_reload.set_tooltip_text("Reload (Ctrl+R)")

        self.dark_btn = Gtk.ToggleButton()
        dark_icon = Gtk.Image.new_from_icon_name("weather-clear-night-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        self.dark_btn.add(dark_icon)
        self.dark_btn.set_active(self.prefs["dark_mode"])
        self.dark_btn.set_tooltip_text("Toggle dark mode")
        self.dark_btn.connect("toggled", self._on_dark_toggled)

        self.find_bar = Gtk.SearchEntry()
        self.find_bar.set_placeholder_text("Find in page…")
        self.find_bar.set_no_show_all(True)
        self.find_bar.connect("search-changed", self._on_find_changed)
        self.find_bar.connect("stop-search", self._on_find_stop)

        self.toolbar.pack_start(btn_back, False, False, 0)
        self.toolbar.pack_start(btn_fwd, False, False, 0)
        self.toolbar.pack_start(btn_reload, False, False, 0)
        self.toolbar.pack_end(self.dark_btn, False, False, 0)
        self.toolbar.pack_end(self.find_bar, False, False, 0)

    def _setup_layout(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(self.toolbar, False, False, 0)
        box.pack_start(self.webview, True, True, 0)
        self.add(box)

    def _setup_shortcuts(self):
        accel = Gtk.AccelGroup()
        self.add_accel_group(accel)

        def add(key, mod, cb):
            accel.connect(Gdk.keyval_from_name(key), mod, Gtk.AccelFlags.VISIBLE, cb)

        add("r", Gdk.ModifierType.CONTROL_MASK, lambda *_: self.webview.reload())
        add("F11", 0, lambda *_: self._toggle_fullscreen())
        add("plus", Gdk.ModifierType.CONTROL_MASK, lambda *_: self._zoom(0.1))
        add("equal", Gdk.ModifierType.CONTROL_MASK, lambda *_: self._zoom(0.1))
        add("minus", Gdk.ModifierType.CONTROL_MASK, lambda *_: self._zoom(-0.1))
        add("0", Gdk.ModifierType.CONTROL_MASK, lambda *_: self._zoom_reset())
        add("f", Gdk.ModifierType.CONTROL_MASK, lambda *_: self._toggle_find())
        add("Left", Gdk.ModifierType.MOD1_MASK, lambda *_: self.webview.go_back())
        add("Right", Gdk.ModifierType.MOD1_MASK, lambda *_: self.webview.go_forward())
        add("F5", 0, lambda *_: self.webview.reload())

    def _restore_position(self):
        if self.prefs["window_x"] >= 0 and self.prefs["window_y"] >= 0:
            self.move(self.prefs["window_x"], self.prefs["window_y"])

    def _on_configure(self, widget, event):
        w, h = self.get_size()
        x, y = self.get_position()
        self.prefs.update({"window_width": w, "window_height": h, "window_x": x, "window_y": y})
        return False

    def _on_close(self, *_):
        settings.save(self.prefs)
        self.hide()
        return True  # hide to tray instead of destroying

    def _apply_theme(self, dark: bool):
        """Called once at startup — sets the UserStyleSheet for all future page loads."""
        self._cm.remove_all_style_sheets()
        if dark:
            sheet = WebKit2.UserStyleSheet(
                _DARK_CSS,
                WebKit2.UserContentInjectedFrames.TOP_FRAME,
                WebKit2.UserStyleLevel.USER,
                None, None,
            )
            self._cm.add_style_sheet(sheet)

    def _run_js(self, script):
        try:
            self.webview.evaluate_javascript(script, -1, None, None, None, None, None)
        except Exception:
            self.webview.run_javascript(script, None, None, None)

    def _on_dark_toggled(self, btn):
        self.prefs["dark_mode"] = btn.get_active()
        self._apply_theme(self.prefs["dark_mode"])
        js = _DARK_JS_LIVE if self.prefs["dark_mode"] else _LIGHT_JS_LIVE
        self._run_js(js)

    def _toggle_fullscreen(self):
        if self.get_window().get_state() & Gdk.WindowState.FULLSCREEN:
            self.unfullscreen()
        else:
            self.fullscreen()

    def _zoom(self, delta):
        level = round(self.webview.get_zoom_level() + delta, 1)
        level = max(0.5, min(3.0, level))
        self.webview.set_zoom_level(level)
        self.prefs["zoom_level"] = level

    def _zoom_reset(self):
        self.webview.set_zoom_level(1.0)
        self.prefs["zoom_level"] = 1.0

    def _toggle_find(self):
        if self.find_bar.get_visible():
            self._on_find_stop()
        else:
            self.find_bar.show()
            self.find_bar.grab_focus()

    def _on_find_changed(self, entry):
        text = entry.get_text()
        fc = self.webview.get_find_controller()
        if text:
            fc.search(text, WebKit2.FindOptions.CASE_INSENSITIVE | WebKit2.FindOptions.WRAP_AROUND, 100)
        else:
            fc.search_finish()

    def _on_find_stop(self, *_):
        self.webview.get_find_controller().search_finish()
        self.find_bar.set_text("")
        self.find_bar.hide()
        self.webview.grab_focus()
