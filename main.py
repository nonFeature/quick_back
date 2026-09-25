from base_plugin import BasePlugin

from features.quick_back import install_quick_back, uninstall_quick_back
from ui.settings import build_settings


class Plugin(BasePlugin):
    def on_plugin_load(self):
        install_quick_back(self)
        self.log("[Quick Back] loaded")

    def on_plugin_unload(self):
        uninstall_quick_back(self)
        self.log("[Quick Back] unloaded")

    def has_settings(self):
        return True

    def create_settings(self):
        return build_settings(self)
