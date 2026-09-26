from java.util import Locale

STRINGS = {
    "ru": {
        "gestures_header": "Способы срабатывания",
        "gesture_predictive": "Предиктивный жест",
        "gesture_swipe": "Свайп по экрану",
        "general_header": "Основные настройки",
        "target_mode": "Куда возвращаться",
        "target_mode_home": "Главный экран (список чатов)",
        "target_mode_section": "Корень текущего раздела",
        "hold_threshold": "Время удержания",
        "hold_threshold_ms": "{} мс",
        "vibration": "Вибрация",
        "vib_disabled": "Отключена",
        "vib_light": "Лёгкая",
        "vib_medium": "Обычная",
        "vib_strong": "Сильная",
        "animation": "Анимация",
        "anim_instant": "Мгновенно",
        "anim_fade": "Затухание",
        "anim_depth": "Масштаб",
        "anim_slide": "Сдвиг",
    },
    "en": {
        "gestures_header": "Trigger methods",
        "gesture_predictive": "Predictive back gesture",
        "gesture_swipe": "In-app screen swipe",
        "general_header": "General settings",
        "target_mode": "Return destination",
        "target_mode_home": "Home screen (chats list)",
        "target_mode_section": "Current section root",
        "hold_threshold": "Hold duration",
        "hold_threshold_ms": "{} ms",
        "vibration": "Vibration",
        "vib_disabled": "Disabled",
        "vib_light": "Light",
        "vib_medium": "Medium",
        "vib_strong": "Strong",
        "animation": "Animation",
        "anim_instant": "None",
        "anim_fade": "Fade",
        "anim_depth": "Scale",
        "anim_slide": "Slide",
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
