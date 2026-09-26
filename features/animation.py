from hook_utils import find_class

from ui.settings import CONF_ANIMATION

_QB_ANIMATED_VIEW = None


def _anim_log(plugin, msg):
    if plugin is not None:
        try:
            plugin.log(f"[Quick Back] {msg}")
        except Exception as e:
            print(f"[Quick Back] anim log failed: {e}")


def qb_reset_animated_view():
    global _QB_ANIMATED_VIEW
    if _QB_ANIMATED_VIEW is not None:
        try:
            _QB_ANIMATED_VIEW.animate().cancel()
            _QB_ANIMATED_VIEW.setAlpha(1.0)
            _QB_ANIMATED_VIEW.setScaleX(1.0)
            _QB_ANIMATED_VIEW.setScaleY(1.0)
            _QB_ANIMATED_VIEW.setTranslationY(0.0)
        except Exception:
            pass
        _QB_ANIMATED_VIEW = None


def qb_animate_target_view(plugin, view):
    global _QB_ANIMATED_VIEW
    if view is None:
        return
    try:
        mode = int(plugin.get_setting(CONF_ANIMATION, 0) or 0)
    except Exception:
        mode = 0

    if mode == 0:
        return

    qb_reset_animated_view()
    _QB_ANIMATED_VIEW = view

    DecelerateInterpolator = find_class("android.view.animation.DecelerateInterpolator")
    OvershootInterpolator = find_class("android.view.animation.OvershootInterpolator")

    decelerate = None
    if DecelerateInterpolator is not None:
        try:
            decelerate = DecelerateInterpolator()
        except Exception:
            decelerate = None

    try:
        if mode == 1:
            # 1. Fade / Crossfade
            view.setAlpha(0.0)
            anim = view.animate().alpha(1.0).setDuration(180)
            if decelerate is not None:
                anim.setInterpolator(decelerate)
            anim.start()

        elif mode == 2:
            # 2. Depth Zoom
            view.setAlpha(0.0)
            view.setScaleX(0.88)
            view.setScaleY(0.88)
            anim = view.animate().alpha(1.0).scaleX(1.0).scaleY(1.0).setDuration(220)
            if decelerate is not None:
                anim.setInterpolator(decelerate)
            anim.start()

        elif mode == 3:
            # 3. Slide Up
            try:
                AndroidUtilities = find_class("org.telegram.messenger.AndroidUtilities")
                dp_offset = float(AndroidUtilities.dp(40))
            except Exception:
                dp_offset = 100.0

            view.setAlpha(0.0)
            view.setTranslationY(dp_offset)
            anim = view.animate().alpha(1.0).translationY(0.0).setDuration(200)
            if decelerate is not None:
                anim.setInterpolator(decelerate)
            anim.start()

        elif mode == 4:
            # 4. Elastic Pop
            view.setAlpha(0.0)
            view.setScaleX(0.85)
            view.setScaleY(0.85)
            anim = view.animate().alpha(1.0).scaleX(1.0).scaleY(1.0).setDuration(260)

            overshoot = None
            if OvershootInterpolator is not None:
                try:
                    from java import jfloat

                    overshoot = OvershootInterpolator(jfloat(1.5))
                except Exception:
                    try:
                        overshoot = OvershootInterpolator()
                    except Exception:
                        overshoot = None

            if overshoot is not None:
                anim.setInterpolator(overshoot)
            elif decelerate is not None:
                anim.setInterpolator(decelerate)
            anim.start()

        _anim_log(plugin, f"transition animation started (mode {mode})")
    except Exception as e:
        _anim_log(plugin, f"target view animation error: {e}")
        qb_reset_animated_view()
