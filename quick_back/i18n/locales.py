from java.util import Locale

STRINGS = {
    "ru": {
        "gestures_header": "Жесты",
        "gesture_predictive": "Системный свайп «Назад»",
        "gesture_swipe": "Свайп внутри приложения",
        "general_header": "Основное",
        "target_mode": "Куда прыгать",
        "target_mode_home": "К списку чатов",
        "target_mode_section": "В начало ветки",
        "hold_threshold": "Сколько удерживать",
        "hold_threshold_ms": "{} мс",
        "vibration": "Отклик",
        "vib_disabled": "Выключен",
        "vib_light": "Слабый",
        "vib_medium": "Средний",
        "vib_strong": "Сильный",
        "animation": "Анимация перехода",
        "anim_instant": "Без анимации",
        "anim_fade": "Растворение",
        "anim_depth": "Приближение",
        "anim_slide": "Выезд снизу",
    },
    "en": {
        "gestures_header": "Gestures",
        "gesture_predictive": "System predictive back",
        "gesture_swipe": "In-app back swipe",
        "general_header": "General",
        "target_mode": "Jump destination",
        "target_mode_home": "To chats list",
        "target_mode_section": "To section top",
        "hold_threshold": "Hold delay",
        "hold_threshold_ms": "{} ms",
        "vibration": "Haptic feedback",
        "vib_disabled": "Off",
        "vib_light": "Light",
        "vib_medium": "Medium",
        "vib_strong": "Strong",
        "animation": "Transition effect",
        "anim_instant": "None",
        "anim_fade": "Fade",
        "anim_depth": "Zoom",
        "anim_slide": "Slide up",
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
