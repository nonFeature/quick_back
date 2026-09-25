from java.util import Locale

STRINGS = {
    "ru": {
        "settings_header": "Quick Back",
        "target_mode": "Куда возвращаться",
        "target_mode_home": "Главный экран (список чатов)",
        "target_mode_section": "Корень текущего раздела",
        "hold_threshold": "Время удержания жеста",
        "hold_threshold_ms": "{} мс",
        "vibration": "Вибрация при срабатывании",
        "vibration_sub": "Тактильный отклик в момент достижения времени удержания",
    },
    "en": {
        "settings_header": "Quick Back",
        "target_mode": "Return destination",
        "target_mode_home": "Home screen (chats list)",
        "target_mode_section": "Current section root",
        "hold_threshold": "Hold duration",
        "hold_threshold_ms": "{} ms",
        "vibration": "Vibration on trigger",
        "vibration_sub": "Haptic feedback when the hold duration is reached",
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
