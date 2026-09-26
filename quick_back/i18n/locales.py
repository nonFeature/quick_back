from java.util import Locale

STRINGS = {
    "ru": {
        "gestures_header": "Жесты",
        "gesture_predictive": "Системный жест «Назад»",
        "gesture_swipe": "ТГ-шный жест «Назад»",
        "general_header": "Поведение",
        "target_mode": "Куда бросать при зажатии",
        "target_mode_home": "В список всех чатов",
        "target_mode_section": "В открытый чат",
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
    },
    "en": {
        "gestures_header": "Gestures",
        "gesture_predictive": "System back gesture",
        "gesture_swipe": "Telegram back gesture",
        "general_header": "Behavior",
        "target_mode": "Hold destination",
        "target_mode_home": "To all chats list",
        "target_mode_section": "To current chat",
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
