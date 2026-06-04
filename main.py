#!/usr/bin/env python3
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

# must be set before any window is created — controls WM_CLASS
GLib.set_prgname("metaai-desktop")
GLib.set_application_name("MetaAI")

from window import MetaAIWindow
import tray


def main():
    win = MetaAIWindow()
    tray.build_tray(win)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
