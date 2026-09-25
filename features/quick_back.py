import time

from base_plugin import MethodHook
from hook_utils import find_class, get_private_field, set_private_field

from data.constants import (
    CONF_HOLD_THRESHOLD,
    CONF_TARGET_MODE,
    CONF_VIBRATION,
    DEFAULT_HOLD_THRESHOLD_MS,
    DEFAULT_TARGET_MODE,
    TARGET_MODE_SECTION,
)
from utils.fragment import post_ui
from utils.helpers import quick_back_core

_QB_HOOK_REFS = []
_QB_INSTALLED = False
_QB_BACK_START_TS = None
_QB_THRESHOLD_RUNNABLE = None
_QB_VIBRATED = False
_QB_SNAPSHOT = None
_QB_SWAP_TS = None
_QB_DIRTY = False
_QB_INTERMEDIATE = []
_QB_TARGET_FRAGMENT = None
_QB_PREPARE_MOVING = None
_QB_MISSING = object()
_QB_FIELDS = {}


def _qb_log(plugin, msg):
    try:
        plugin.log(f"[Quick Back] {msg}")
    except Exception as e:
        print(f"[Quick Back] log failed: {e}")


def _qb_waveform(*values):
    from java import jlong

    return jlong[values]


def _qb_vibration_enabled(plugin):
    try:
        return bool(plugin.get_setting(CONF_VIBRATION, True))
    except Exception:
        return True


def _qb_vibrate(plugin):
    if not _qb_vibration_enabled(plugin):
        return
    try:
        from android.os import Build

        VibratorUtils = find_class("com.exteragram.messenger.utils.system.VibratorUtils")
        if VibratorUtils:
            from android.os import VibrationEffect

            if int(Build.VERSION.SDK_INT) >= 29:
                effect = VibrationEffect.createPredefined(int(VibrationEffect.EFFECT_HEAVY_CLICK))
                VibratorUtils.vibrateEffect(effect)
            else:
                VibratorUtils.vibrate(40)
            _qb_log(plugin, "gesture threshold reached, vibration played")
            return
    except Exception as e:
        _qb_log(plugin, f"extera vibration error: {e}")
    try:
        from android.os import Build, VibrationEffect
        from org.telegram.messenger import ApplicationLoader

        context = ApplicationLoader.applicationContext
        vibrator = context.getSystemService("vibrator")
        if vibrator is None:
            return
        if int(Build.VERSION.SDK_INT) >= 26:
            vibrator.vibrate(VibrationEffect.createWaveform(_qb_waveform(0, 35, 70, 35), -1))
        else:
            vibrator.vibrate(40)
    except Exception as e:
        _qb_log(plugin, f"vibration error: {e}")


def _qb_threshold_sec(plugin):
    try:
        from data.constants import DEFAULT_HOLD_THRESHOLD_INDEX, THRESHOLD_CHOICES

        raw = int(plugin.get_setting(CONF_HOLD_THRESHOLD, DEFAULT_HOLD_THRESHOLD_INDEX) or DEFAULT_HOLD_THRESHOLD_INDEX)
        if 0 <= raw < len(THRESHOLD_CHOICES):
            ms = THRESHOLD_CHOICES[raw]
        else:
            ms = raw
        return max(0.15, ms / 1000.0)
    except Exception as e:
        _qb_log(plugin, f"threshold setting read failed: {e}")
        return DEFAULT_HOLD_THRESHOLD_MS / 1000.0


def _is_archive(candidate):
    if candidate is None:
        return False
    try:
        DialogsActivity = find_class("org.telegram.ui.DialogsActivity")
        if DialogsActivity is not None and isinstance(candidate, DialogsActivity):
            return bool(candidate.isArchive())
    except Exception:
        pass
    return False


def _find_first_chat(stack, start, end):
    try:
        ChatActivity = find_class("org.telegram.ui.ChatActivity")
        if ChatActivity is None:
            return -1, None
        for i in range(start, end):
            fragment = stack.get(i)
            if fragment is not None and isinstance(fragment, ChatActivity):
                return i, fragment
    except Exception:
        pass
    return -1, None


def _qb_bool_field(target, name):
    field = _QB_FIELDS.get(name, _QB_MISSING)
    if field is _QB_MISSING:
        field = None
        try:
            cls = target.getClass()
            while cls is not None:
                try:
                    field = cls.getDeclaredField(name)
                    field.setAccessible(True)
                    break
                except Exception:
                    cls = cls.getSuperclass()
        except Exception as e:
            _qb_log(None, f"{name} lookup error: {e}")
        _QB_FIELDS[name] = field
    if field is None:
        return None
    try:
        return bool(field.get(target))
    except Exception as e:
        _qb_log(None, f"{name} read error: {e}")
        return None


def _qb_gesture_active(layout):
    in_progress = _qb_bool_field(layout, "predictiveBackInProgress")
    if in_progress is None:
        return True
    return in_progress


def _qb_stack_dump(layout):
    try:
        stack = layout.getFragmentStack()
        parts = []
        for i in range(int(stack.size())):
            fragment = stack.get(i)
            name = "null" if fragment is None else fragment.getClass().getSimpleName()
            parts.append(f"{i}:{name}")
        return " ".join(parts)
    except Exception as e:
        return f"<dump failed: {e}>"


def _find_main_fragment(layout):
    try:
        DialogsActivity = find_class("org.telegram.ui.DialogsActivity")
        MainTabsActivity = find_class("org.telegram.ui.MainTabsActivity")
        stack = layout.getFragmentStack()
        for i in range(stack.size() - 2, -1, -1):
            fragment = stack.get(i)
            if DialogsActivity is not None and isinstance(fragment, DialogsActivity):
                try:
                    if fragment.isMainDialogList() and not fragment.isArchive():
                        return i, fragment
                except Exception:
                    pass
            if MainTabsActivity is not None and isinstance(fragment, MainTabsActivity):
                try:
                    dialogs = fragment.getDialogsActivity()
                    if dialogs is not None and not dialogs.isArchive():
                        return i, fragment
                except Exception:
                    pass
    except Exception as e:
        _qb_log(None, f"find_main_fragment failed: {e}")
    return -1, None


def _qb_hold_target(plugin, layout):
    """Determines if the current stack and screen are eligible for quick back,

    and identifies the target fragment to jump to.
    """
    try:
        stack = layout.getFragmentStack()
        size = int(stack.size())
        if size < 3:
            return None

        top = stack.get(size - 1)
        # Exclude only if currently on the Archive screen itself
        if _is_archive(top):
            return None

        mode = int(plugin.get_setting(CONF_TARGET_MODE, DEFAULT_TARGET_MODE) or DEFAULT_TARGET_MODE)

        target_index = -1
        target_fragment = None

        if mode == TARGET_MODE_SECTION:
            # Section root mode:
            # If the screen right after main list is archive (e.g. Main -> Archive -> Chat -> Profile)
            if size > 2 and _is_archive(stack.get(1)):
                chat_index, chat_fragment = _find_first_chat(stack, start=2, end=size - 1)
                if chat_fragment is not None:
                    target_index, target_fragment = chat_index, chat_fragment
                else:
                    target_index, target_fragment = _find_main_fragment(layout)
            else:
                target_index = 1
                target_fragment = stack.get(1)
        else:
            # Home mode:
            target_index, target_fragment = _find_main_fragment(layout)

        if target_fragment is None or target_index < 0:
            target_index = 0
            target_fragment = stack.get(0)

        # If the target is already at or above size - 2, normal back gesture already lands on it
        if target_index >= size - 2:
            return None

        return stack, size, target_index, target_fragment
    except Exception as e:
        _qb_log(plugin, f"hold target check error: {e}")
        return None


def _qb_stack_snapshot(stack, size):
    try:
        return [stack.get(i) for i in range(size)]
    except Exception as e:
        _qb_log(None, f"stack snapshot failed: {e}")
        return None


def _qb_apply_order(layout, fragments):
    try:
        stack = layout.getFragmentStack()
        stack.clear()
        for fragment in fragments:
            stack.add(fragment)
        return True
    except Exception as e:
        _qb_log(None, f"stack reorder error: {e}")
        return False


def _qb_target_behind_top(layout, stack, size, target_index, target_fragment):
    global _QB_SNAPSHOT, _QB_INTERMEDIATE, _QB_TARGET_FRAGMENT
    snapshot = _qb_stack_snapshot(stack, size)
    if snapshot is None:
        _qb_log(None, "swap skipped: stack snapshot failed")
        return False

    screens_below = snapshot[0:target_index]
    target = snapshot[target_index]
    intermediate = snapshot[target_index + 1 : size - 1]
    top = snapshot[size - 1]

    ordered = screens_below + intermediate + [target, top]
    if not _qb_apply_order(layout, ordered):
        return False

    _QB_SNAPSHOT = snapshot
    _QB_INTERMEDIATE = intermediate
    _QB_TARGET_FRAGMENT = target

    try:
        if stack.get(int(stack.size()) - 2) != target_fragment:
            _qb_log(None, "swap skipped: target is not the fragment behind top")
            return False
    except Exception as e:
        _qb_log(None, f"swap verify error: {e}")
        return False
    return True


def _qb_cache_prepare_moving(plugin):
    global _QB_PREPARE_MOVING
    if _QB_PREPARE_MOVING is not None:
        return True
    try:
        ActionBarLayout = find_class("org.telegram.ui.ActionBar.ActionBarLayout")
        if not ActionBarLayout:
            return False
        method = ActionBarLayout.getClass().getDeclaredMethod("prepareForMoving")
        method.setAccessible(True)
        _QB_PREPARE_MOVING = method
        _qb_log(plugin, "prepareForMoving resolved")
        return True
    except Exception as e:
        _qb_log(plugin, f"prepareForMoving unavailable: {e}")
        return False


def _qb_prepare_moving(layout):
    try:
        if _QB_PREPARE_MOVING is None:
            return False
        _QB_PREPARE_MOVING.invoke(layout)
        return True
    except Exception as e:
        _qb_log(None, f"prepareForMoving error: {e}")
        return False


def _qb_transition_background(layout):
    try:
        Helper = find_class("com.exteragram.messenger.utils.ui.PredictiveBackAnimationHelper")
        if not Helper:
            return False
        background = Helper.getTransitionBackground(layout.getFragmentStack(), layout.getLastFragment())
        if background is None:
            return False
        set_private_field(layout, "predictiveBackBackgroundDrawable", background)
        try:
            set_private_field(layout, "springRouteBackgroundDrawable", background)
        except Exception:
            pass
        return True
    except Exception as e:
        _qb_log(None, f"transition background error: {e}")
        return False


def _qb_swap_background(plugin, layout, ts):
    global _QB_SWAP_TS, _QB_DIRTY
    try:
        if not _qb_gesture_active(layout):
            _qb_log(plugin, "swap skipped: no predictive gesture in flight")
            return False
        target_info = _qb_hold_target(plugin, layout)
        if target_info is None:
            _qb_log(plugin, "swap skipped: target not eligible")
            return False
        stack, size, target_index, target_fragment = target_info
        core = quick_back_core(plugin)
        if core is None:
            _qb_log(plugin, "swap skipped: core unavailable")
            return False
        if not core.clearBackContainer(layout):
            _qb_log(plugin, "swap skipped: back container unavailable")
            return False
        _QB_DIRTY = True
        if not _qb_target_behind_top(layout, stack, size, target_index, target_fragment):
            _qb_revert(plugin, layout, "reorder refused")
            return False
        if not _qb_prepare_moving(layout):
            _qb_revert(plugin, layout, "prepareForMoving refused")
            return False
        _qb_transition_background(layout)
        try:
            get_private_field(layout, "containerViewBack").invalidate()
            get_private_field(layout, "containerView").invalidate()
        except Exception as e:
            _qb_log(plugin, f"container invalidate failed: {e}")
        _QB_SWAP_TS = ts
        frag_name = target_fragment.getClass().getSimpleName()
        _qb_log(plugin, f"threshold reached: back retargeted to {frag_name} (idx {target_index}) | {_qb_stack_dump(layout)}")
        return True
    except Exception as e:
        _qb_log(plugin, f"swap background error: {e}")
        _qb_revert(plugin, layout, "swap exception")
        return False


def _qb_revert(plugin, layout, reason):
    global _QB_SNAPSHOT, _QB_SWAP_TS, _QB_DIRTY, _QB_INTERMEDIATE, _QB_TARGET_FRAGMENT
    if not _QB_DIRTY:
        return
    _QB_DIRTY = False
    _QB_SWAP_TS = None
    _QB_INTERMEDIATE = []
    _QB_TARGET_FRAGMENT = None
    try:
        core = quick_back_core(plugin)
        if core is None or not core.restoreViews(layout):
            _qb_log(plugin, f"revert ({reason}): back container not restored")
        if _QB_SNAPSHOT is not None:
            _qb_apply_order(layout, _QB_SNAPSHOT)
        _qb_log(plugin, f"reverted ({reason}) | {_qb_stack_dump(layout)}")
    except Exception as e:
        _qb_log(plugin, f"revert ({reason}) error: {e}")
    finally:
        _QB_SNAPSHOT = None


class _QbThresholdRunnable:
    def __init__(self, plugin, ts, layout):
        self.plugin = plugin
        self.ts = ts
        self.layout = layout

    def run(self):
        global _QB_VIBRATED
        try:
            if _QB_BACK_START_TS != self.ts or _QB_VIBRATED:
                return
            _QB_VIBRATED = True
            _qb_vibrate(self.plugin)
            _qb_swap_background(self.plugin, self.layout, self.ts)
        except Exception as e:
            _qb_log(self.plugin, f"threshold runnable error: {e}")


class _QbOnBackStartedHook(MethodHook):
    def __init__(self, plugin):
        self.plugin = plugin

    def before_hooked_method(self, param):
        if _QB_DIRTY:
            _qb_revert(self.plugin, param.thisObject, "previous gesture never resolved")

    def after_hooked_method(self, param):
        global _QB_BACK_START_TS, _QB_VIBRATED, _QB_THRESHOLD_RUNNABLE
        try:
            _QB_BACK_START_TS = None
            if not param.getResult():
                return
            layout = param.thisObject
            if _qb_hold_target(self.plugin, layout) is None:
                return

            _QB_BACK_START_TS = time.monotonic()
            _QB_VIBRATED = False

            threshold = _qb_threshold_sec(self.plugin)
            runnable = _QbThresholdRunnable(self.plugin, _QB_BACK_START_TS, layout)
            _QB_THRESHOLD_RUNNABLE = runnable
            post_ui(runnable.run, int(threshold * 1000))
        except Exception as e:
            _qb_log(self.plugin, f"onBackStarted hook error: {e}")
            _QB_BACK_START_TS = None


class _QbOnBackCancelledHook(MethodHook):
    def __init__(self, plugin):
        self.plugin = plugin

    def after_hooked_method(self, param):
        global _QB_BACK_START_TS, _QB_VIBRATED
        _QB_BACK_START_TS = None
        _QB_VIBRATED = False
        _qb_revert(self.plugin, param.thisObject, "gesture cancelled")


class _QbOnBackInvokedHook(MethodHook):
    def __init__(self, plugin):
        self.plugin = plugin

    def before_hooked_method(self, param):
        global _QB_BACK_START_TS, _QB_VIBRATED, _QB_SNAPSHOT, _QB_SWAP_TS, _QB_DIRTY, _QB_INTERMEDIATE, _QB_TARGET_FRAGMENT
        try:
            start = _QB_BACK_START_TS
            if start is None or _QB_SWAP_TS != start:
                if _QB_DIRTY:
                    _qb_log(self.plugin, "back invoked for another gesture, reverting")
                    _qb_revert(self.plugin, param.thisObject, "stale swap")
                return

            held = time.monotonic() - start
            threshold = _qb_threshold_sec(self.plugin)
            layout = param.thisObject
            if held < threshold or not _qb_gesture_active(layout):
                _qb_log(self.plugin, f"back released after {held:.2f}s, no jump")
                _qb_revert(self.plugin, layout, "released early")
                return

            # Gesture held >= threshold and committed!
            # Drop all intermediate skipped screens between target and top.
            removed = 0
            for fragment in list(_QB_INTERMEDIATE):
                try:
                    layout.removeFragmentFromStack(fragment, False)
                    removed += 1
                except Exception as e:
                    _qb_log(self.plugin, f"remove intermediate screen error: {e}")

            _qb_log(
                self.plugin,
                f"back held for {held:.2f}s >= {threshold:.2f}s, {removed} skipped screen(s) dropped | {_qb_stack_dump(layout)}",
            )
            core = quick_back_core(self.plugin)
            if core is not None:
                core.dropSaved()
            _QB_SNAPSHOT = None
            _QB_SWAP_TS = None
            _QB_DIRTY = False
            _QB_VIBRATED = False
            _QB_INTERMEDIATE = []
            _QB_TARGET_FRAGMENT = None
        except Exception as e:
            _qb_log(self.plugin, f"onBackInvoked hook error: {e}")

    def after_hooked_method(self, param):
        global _QB_BACK_START_TS, _QB_VIBRATED, _QB_SWAP_TS
        _QB_BACK_START_TS = None
        _QB_VIBRATED = False
        _QB_SWAP_TS = None


def install_quick_back(plugin):
    global _QB_INSTALLED
    if _QB_INSTALLED:
        return
    try:
        ActionBarLayout = find_class("org.telegram.ui.ActionBar.ActionBarLayout")
        if not ActionBarLayout:
            _qb_log(plugin, "ActionBarLayout not found, quick back disabled")
            return

        for name, hook_cls in (
            ("onBackStarted", _QbOnBackStartedHook),
            ("onBackCancelled", _QbOnBackCancelledHook),
            ("onBackInvoked", _QbOnBackInvokedHook),
        ):
            for m in ActionBarLayout.getClass().getDeclaredMethods():
                try:
                    if m.getName() != name:
                        continue
                    m.setAccessible(True)
                    ref = plugin.hook_method(m, hook_cls(plugin))
                    if ref:
                        _QB_HOOK_REFS.append(ref)
                except Exception as e:
                    _qb_log(plugin, f"hook {name} failed: {e}")
                    continue

        _qb_cache_prepare_moving(plugin)
        _QB_INSTALLED = True
        _qb_log(plugin, f"quick back hooks installed ({len(_QB_HOOK_REFS)})")
    except Exception as e:
        _qb_log(plugin, f"install error: {e}")


def uninstall_quick_back(plugin):
    global _QB_INSTALLED, _QB_BACK_START_TS, _QB_THRESHOLD_RUNNABLE, _QB_SNAPSHOT, _QB_SWAP_TS, _QB_DIRTY, _QB_INTERMEDIATE, _QB_TARGET_FRAGMENT
    for ref in _QB_HOOK_REFS:
        try:
            plugin.unhook_method(ref)
        except Exception as e:
            _qb_log(plugin, f"unhook failed: {e}")
    _QB_HOOK_REFS.clear()
    _QB_INSTALLED = False
    _QB_BACK_START_TS = None
    _QB_THRESHOLD_RUNNABLE = None
    _QB_SNAPSHOT = None
    _QB_SWAP_TS = None
    _QB_DIRTY = False
    _QB_INTERMEDIATE = []
    _QB_TARGET_FRAGMENT = None
    _qb_log(plugin, "quick back hooks uninstalled")
