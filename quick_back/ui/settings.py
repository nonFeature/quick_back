from i18n.locales import get_string
from ui.settings import Header, Selector, Switch

CONF_GESTURE_PREDICTIVE = "gesture_predictive"
CONF_GESTURE_SWIPE = "gesture_swipe"
CONF_TARGET_MODE = "target_mode"
CONF_HOLD_THRESHOLD = "threshold"
CONF_VIBRATION = "vibration"
CONF_ANIMATION = "animation"

THRESHOLD_CHOICES = [400, 600, 800, 1000]

__all__ = [
    "CONF_ANIMATION",
    "CONF_GESTURE_PREDICTIVE",
    "CONF_GESTURE_SWIPE",
    "CONF_HOLD_THRESHOLD",
    "CONF_TARGET_MODE",
    "CONF_VIBRATION",
    "THRESHOLD_CHOICES",
    "build_settings",
]


def build_settings(plugin):
    from features.vibration import play_vibration

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
    animation_items = [
        get_string("anim_instant"),
        get_string("anim_fade"),
        get_string("anim_depth"),
        get_string("anim_slide"),
        get_string("anim_elastic"),
    ]

    return [
        Header(text=get_string("gestures_header")),
        Switch(
            key=CONF_GESTURE_PREDICTIVE,
            text=get_string("gesture_predictive"),
            subtext=get_string("gesture_predictive_sub"),
            default=True,
        ),
        Switch(
            key=CONF_GESTURE_SWIPE,
            text=get_string("gesture_swipe"),
            subtext=get_string("gesture_swipe_sub"),
            default=True,
        ),
        Header(text=get_string("general_header")),
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
        Selector(
            key=CONF_ANIMATION,
            text=get_string("animation"),
            default=0,
            items=animation_items,
        ),
    ]
