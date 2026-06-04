import os

ICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "icon.png")


def build_tray(window):
    """Return a tray indicator if a supported library is available, else None."""
    try:
        import gi
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as AppIndicator3
    except Exception:
        try:
            gi.require_version("AppIndicator3", "0.1")
            from gi.repository import AppIndicator3
        except Exception:
            return None

    from gi.repository import Gtk

    indicator = AppIndicator3.Indicator.new(
        "metaai-desktop",
        ICON_PATH if os.path.exists(ICON_PATH) else "dialog-information",
        AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
    )
    indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

    menu = Gtk.Menu()

    item_show = Gtk.MenuItem(label="Show MetaAI")
    item_show.connect("activate", lambda _: window.present())
    menu.append(item_show)

    item_sep = Gtk.SeparatorMenuItem()
    menu.append(item_sep)

    item_quit = Gtk.MenuItem(label="Quit")
    item_quit.connect("activate", lambda _: Gtk.main_quit())
    menu.append(item_quit)

    menu.show_all()
    indicator.set_menu(menu)

    return indicator
