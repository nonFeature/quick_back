from i18n.locales import get_string
from ui.settings import Selector


THRESHOLD_CHOICES = [400, 600, 800, 1000]


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
        Selector(
            key="target_mode",
            text=get_string("target_mode"),
            default=0,
            items=target_modes,
        ),
        Selector(
            key="threshold",
            text=get_string("hold_threshold"),
            default=1,
            items=threshold_items,
        ),
        Selector(
            key="vibration",
            text=get_string("vibration"),
            default=2,
            items=vibration_items,
            on_change=lambda value: play_vibration(plugin, value),
        ),
        Selector(
            key="animation",
            text=get_string("animation"),
            default=0,
            items=animation_items,
        ),
    ]
