from java.util import Locale

STRINGS = {
    "ru": {
        "target_mode": "Куда возвращаться",
        "target_mode_home": "Главный экран (список чатов)",
        "target_mode_section": "Корень текущего раздела",
        "hold_threshold": "Время удержания для срабатывания",
        "hold_threshold_ms": "{} мс",
        "vibration": "Вибрация при срабатывании",
        "vib_disabled": "Отключена",
        "vib_light": "Лёгкая",
        "vib_medium": "Обычная",
        "vib_strong": "Сильная",
        "animation": "Анимация",
        "anim_instant": "Без анимации",
        "anim_fade": "Затухание",
        "anim_depth": "Масштаб",
        "anim_slide": "Сдвиг",
        "anim_elastic": "Пружина",
    },
    "en": {
        "target_mode": "Return destination",
        "target_mode_home": "Home screen (chats list)",
        "target_mode_section": "Current section root",
        "hold_threshold": "Hold duration",
        "hold_threshold_ms": "{} ms",
        "vibration": "Vibration on trigger",
        "vib_disabled": "Disabled",
        "vib_light": "Light",
        "vib_medium": "Medium",
        "vib_strong": "Strong",
        "animation": "Animation",
        "anim_instant": "None",
        "anim_fade": "Fade",
        "anim_depth": "Scale",
        "anim_slide": "Slide",
        "anim_elastic": "Spring",
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
