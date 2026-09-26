from hook_utils import find_class
from ui.settings import CONF_VIBRATION


def _play_effect(vibrator, effect, VibratorUtils=None):
    if effect is not None:
        if VibratorUtils is not None:
            try:
                VibratorUtils.vibrateEffect(effect)
                return True
            except Exception:
                pass
        try:
            vibrator.cancel()
            vibrator.vibrate(effect)
            return True
        except Exception:
            pass
    return False


def _play_raw(vibrator, ms, VibratorUtils=None):
    if VibratorUtils is not None:
        try:
            VibratorUtils.vibrate(int(ms))
            return True
        except Exception:
            pass
    try:
        vibrator.cancel()
        vibrator.vibrate(int(ms))
        return True
    except Exception:
        pass
    return False


def play_vibration(plugin, mode=None):
    if mode is None:
        try:
            mode = int(plugin.get_setting(CONF_VIBRATION, 2) or 2)
        except Exception:
            mode = 2

    if mode == 0:
        return

    try:
        from android.os import Build
        from org.telegram.messenger import ApplicationLoader

        context = ApplicationLoader.applicationContext
        vibrator = context.getSystemService("vibrator")
        if vibrator is None:
            return

        try:
            if not vibrator.hasVibrator():
                return
        except Exception:
            pass

        has_amplitude = False
        sdk = int(Build.VERSION.SDK_INT)
        if sdk >= 26:
            try:
                has_amplitude = bool(vibrator.hasAmplitudeControl())
            except Exception:
                has_amplitude = False

        VibratorUtils = find_class("com.exteragram.messenger.utils.system.VibratorUtils")

        # Mode 1: Single light click (EFFECT_CLICK or ~15ms)
        if mode == 1:
            if sdk >= 29:
                try:
                    from android.os import VibrationEffect

                    effect = VibrationEffect.createPredefined(int(VibrationEffect.EFFECT_CLICK))
                    if _play_effect(vibrator, effect, VibratorUtils):
                        return
                except Exception:
                    pass

            if sdk >= 26:
                try:
                    from android.os import VibrationEffect

                    amp = 60 if has_amplitude else -1
                    effect = VibrationEffect.createOneShot(15, amp)
                    if _play_effect(vibrator, effect, VibratorUtils):
                        return
                except Exception:
                    pass

            _play_raw(vibrator, 15, VibratorUtils)
            return

        # Mode 2: Single medium pulse (~55ms, solid tactile tap)
        elif mode == 2:
            if sdk >= 26:
                try:
                    from android.os import VibrationEffect

                    amp = 160 if has_amplitude else -1
                    effect = VibrationEffect.createOneShot(55, amp)
                    if _play_effect(vibrator, effect, VibratorUtils):
                        return
                except Exception:
                    pass

            _play_raw(vibrator, 55, VibratorUtils)
            return

        # Mode 3: Single strong pulse (~160ms, heavy vibration)
        elif mode == 3:
            if sdk >= 26:
                try:
                    from android.os import VibrationEffect

                    amp = 255 if has_amplitude else -1
                    effect = VibrationEffect.createOneShot(160, amp)
                    if _play_effect(vibrator, effect, VibratorUtils):
                        return
                except Exception:
                    pass

            _play_raw(vibrator, 160, VibratorUtils)
            return

    except Exception as e:
        if plugin is not None:
            try:
                plugin.log(f"[Quick Back] vibration error: {e}")
            except Exception:
                pass
