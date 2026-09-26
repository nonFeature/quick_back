from hook_utils import find_class

from ui.settings import CONF_VIBRATION


def qb_waveform(*values):
    from java import jlong

    return jlong[values]


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

        VibratorUtils = find_class("com.exteragram.messenger.utils.system.VibratorUtils")
        if VibratorUtils:
            from android.os import VibrationEffect

            if mode == 1:
                if int(Build.VERSION.SDK_INT) >= 29:
                    VibratorUtils.vibrateEffect(VibrationEffect.createPredefined(int(VibrationEffect.EFFECT_CLICK)))
                else:
                    VibratorUtils.vibrate(20)
            elif mode == 2:
                if int(Build.VERSION.SDK_INT) >= 29:
                    VibratorUtils.vibrateEffect(VibrationEffect.createPredefined(int(VibrationEffect.EFFECT_HEAVY_CLICK)))
                else:
                    VibratorUtils.vibrate(40)
            elif mode == 3:
                VibratorUtils.vibrate(80)
            return
    except Exception:
        pass

    try:
        from android.os import Build, VibrationEffect
        from org.telegram.messenger import ApplicationLoader

        context = ApplicationLoader.applicationContext
        vibrator = context.getSystemService("vibrator")
        if vibrator is None:
            return

        if mode == 1:
            if int(Build.VERSION.SDK_INT) >= 29:
                vibrator.vibrate(VibrationEffect.createPredefined(int(VibrationEffect.EFFECT_CLICK)))
            else:
                vibrator.vibrate(20)
        elif mode == 2:
            if int(Build.VERSION.SDK_INT) >= 29:
                vibrator.vibrate(VibrationEffect.createPredefined(int(VibrationEffect.EFFECT_HEAVY_CLICK)))
            else:
                vibrator.vibrate(40)
        elif mode == 3:
            vibrator.vibrate(80)
    except Exception:
        pass
