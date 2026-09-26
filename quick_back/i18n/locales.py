from java.util import Locale

STRINGS = {
    "ru": {
        "gestures_header": "Где срабатывать",
        "gesture_predictive": "Предиктивный жест «Назад»",
        "gesture_swipe": "ТГ-шный свайп",
        "general_header": "Поведение",
        "target_mode": "Куда бросать при зажатии",
        "target_mode_home": "На главную",
        "target_mode_section": "В начало раздела",
        "hold_threshold": "Пауза для срабатывания",
        "hold_threshold_ms": "{} мс",
        "vibration": "Вибрация при срабатывании",
        "vib_disabled": "Выключена",
        "vib_light": "Слабая",
        "vib_medium": "Средняя",
        "vib_strong": "Сильная",
        "animation": "Анимация появления",
        "anim_instant": "Без анимации",
        "anim_fade": "Растворение",
        "anim_depth": "Приближение",
        "anim_slide": "Выезд снизу",
        "hint_incompat_prefix": "Плагин будет срабатывать только через ТГ-шный свайп",
        "reason_android": "для предиктивного жеста «Назад» требуется Android 14+ (у тебя Android {}).",
        "reason_telegram": "текущая версия клиента не поддерживает предиктивный жест «Назад».",
        "reason_buttons": (
            "в системе включена навигация кнопками. Чтобы он реагировал и на предиктивный жест, включи жестовую навигацию в настройках Android."
        ),
        "reason_client": ("в клиенте отключён предиктивный жест «Назад». Включи его в настройках своего клиента, чтобы плагин реагировал и на него."),
    },
    "en": {
        "gestures_header": "Gestures",
        "gesture_predictive": "Predictive back gesture",
        "gesture_swipe": "Telegram in-app swipe",
        "general_header": "Behavior",
        "target_mode": "Hold destination",
        "target_mode_home": "To home",
        "target_mode_section": "To section start",
        "hold_threshold": "Trigger pause",
        "hold_threshold_ms": "{} ms",
        "vibration": "Vibration on trigger",
        "vib_disabled": "Disabled",
        "vib_light": "Light",
        "vib_medium": "Medium",
        "vib_strong": "Strong",
        "animation": "Appearance animation",
        "anim_instant": "None",
        "anim_fade": "Fade",
        "anim_depth": "Zoom",
        "anim_slide": "Slide up",
        "hint_incompat_prefix": "The plugin will only trigger via Telegram in-app swipe",
        "reason_android": "predictive back gesture requires Android 14+ (you have Android {}).",
        "reason_telegram": "current client version does not support predictive back gesture.",
        "reason_buttons": ("3-button navigation is enabled. To make it respond to predictive back gestures, enable gesture navigation in Android settings."),
        "reason_client": ("predictive back gesture is disabled in the client. Enable it in your client's settings to make the plugin respond to it."),
    },
}


def get_language():
    try:
        return "ru" if Locale.getDefault().getLanguage() == "ru" else "en"
    except Exception as e:
        print(f"[Quick Back] i18n language get failed: {e}")
        return "en"


def get_string(key):
    lang = get_language()
    return STRINGS.get(lang, STRINGS["en"]).get(key, STRINGS["en"].get(key, ""))
