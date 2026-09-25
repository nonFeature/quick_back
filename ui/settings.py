from data.constants import (
    CONF_HOLD_THRESHOLD,
    CONF_TARGET_MODE,
    CONF_VIBRATION,
    DEFAULT_HOLD_THRESHOLD_INDEX,
    DEFAULT_TARGET_MODE,
    THRESHOLD_CHOICES,
)
from i18n.locales import get_string
from ui.settings import Header, Selector, Switch


def build_settings(plugin):
    target_modes = [
        get_string("target_mode_home"),
        get_string("target_mode_section"),
    ]
    threshold_items = [get_string("hold_threshold_ms").format(ms) for ms in THRESHOLD_CHOICES]

    return [
        Header(text=get_string("settings_header")),
        Selector(
            key=CONF_TARGET_MODE,
            text=get_string("target_mode"),
            default=DEFAULT_TARGET_MODE,
            items=target_modes,
        ),
        Selector(
            key=CONF_HOLD_THRESHOLD,
            text=get_string("hold_threshold"),
            default=DEFAULT_HOLD_THRESHOLD_INDEX,
            items=threshold_items,
        ),
        Switch(
            key=CONF_VIBRATION,
            text=get_string("vibration"),
            subtext=get_string("vibration_sub"),
            default=True,
        ),
    ]
