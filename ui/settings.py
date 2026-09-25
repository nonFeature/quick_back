from i18n.locales import get_string
from ui.settings import Selector

CONF_TARGET_MODE = "quick_back_target_mode"
CONF_HOLD_THRESHOLD = "quick_back_threshold"
CONF_VIBRATION = "quick_back_vibration"

THRESHOLD_CHOICES = [400, 600, 800, 1000]


def build_settings(plugin):
    from features.quick_back import play_vibration

    target_modes = [
        get_string("target_mode_home"),
        get_string("target_mode_section"),
    ]
    threshold_items = [get_string("hold_threshold_ms").format(ms) for ms in THRESHOLD_CHOICES]
    vibration_items = [
        get_string("vib_disabled"),
        get_string("vib_light"),
        get_string("vib_medium"),
        get_string("vib_strong"),
    ]

    return [
        Selector(
            key=CONF_TARGET_MODE,
            text=get_string("target_mode"),
            default=0,
            items=target_modes,
        ),
        Selector(
            key=CONF_HOLD_THRESHOLD,
            text=get_string("hold_threshold"),
            default=1,
            items=threshold_items,
        ),
        Selector(
            key=CONF_VIBRATION,
            text=get_string("vibration"),
            default=2,
            items=vibration_items,
            on_change=lambda value: play_vibration(plugin, value),
        ),
    ]
