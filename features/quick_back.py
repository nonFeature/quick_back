import time

from base_plugin import MethodHook
from hook_utils import find_class, get_private_field

from features.animation import qb_animate_target_view, qb_reset_animated_view
from features.stack import (
    qb_apply_order,
    qb_bool_field,
    qb_cache_prepare_moving,
    qb_gesture_active,
    qb_hold_target,
    qb_prepare_moving,
    qb_stack_dump,
    qb_target_behind_top,
    qb_transition_background,
)
from features.vibration import play_vibration
from ui.settings import CONF_HOLD_THRESHOLD, THRESHOLD_CHOICES
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


def _qb_log(plugin, msg):
    try:
        plugin.log(f"[Quick Back] {msg}")
    except Exception as e:
        print(f"[Quick Back] log failed: {e}")


def _qb_threshold_sec(plugin):
    try:
        raw = int(plugin.get_setting(CONF_HOLD_THRESHOLD, 1) or 1)
        if 0 <= raw < len(THRESHOLD_CHOICES):
            ms = THRESHOLD_CHOICES[raw]
        else:
            ms = raw
        return max(0.15, ms / 1000.0)
    except Exception as e:
        _qb_log(plugin, f"threshold setting read failed: {e}")
        return 0.6


def _qb_swap_background(plugin, layout, ts):
    global _QB_SWAP_TS, _QB_DIRTY, _QB_SNAPSHOT, _QB_INTERMEDIATE, _QB_TARGET_FRAGMENT
    try:
        if not qb_gesture_active(layout):
            _qb_log(plugin, "swap skipped: no predictive gesture in flight")
            return False

        target_info = qb_hold_target(plugin, layout)
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
        snapshot, intermediate = qb_target_behind_top(layout, stack, size, target_index, target_fragment)
        if snapshot is None:
            _qb_revert(plugin, layout, "reorder refused")
            return False

        _QB_SNAPSHOT = snapshot
        _QB_INTERMEDIATE = intermediate
        _QB_TARGET_FRAGMENT = target_fragment

        if not qb_prepare_moving(layout):
            _qb_revert(plugin, layout, "prepareForMoving refused")
            return False

        qb_transition_background(layout)
        try:
            container_back = get_private_field(layout, "containerViewBack")
            if container_back is not None:
                count = int(container_back.getChildCount())
                if count > 0:
                    target_view = container_back.getChildAt(count - 1)
                    qb_animate_target_view(plugin, target_view)
                container_back.invalidate()
            get_private_field(layout, "containerView").invalidate()
        except Exception as e:
            _qb_log(plugin, f"container invalidate failed: {e}")

        _QB_SWAP_TS = ts
        frag_name = target_fragment.getClass().getSimpleName()
        _qb_log(plugin, f"threshold reached: back retargeted to {frag_name} (idx {target_index}) | {qb_stack_dump(layout)}")
        return True
    except Exception as e:
        _qb_log(plugin, f"swap background error: {e}")
        _qb_revert(plugin, layout, "swap exception")
        return False


def _qb_revert(plugin, layout, reason):
    global _QB_SNAPSHOT, _QB_SWAP_TS, _QB_DIRTY, _QB_INTERMEDIATE, _QB_TARGET_FRAGMENT
    qb_reset_animated_view()
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
            qb_apply_order(layout, _QB_SNAPSHOT)
        _qb_log(plugin, f"reverted ({reason}) | {qb_stack_dump(layout)}")
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
            if _QB_BACK_START_TS != self.ts:
                _qb_log(self.plugin, f"threshold cancelled: start_ts changed ({_QB_BACK_START_TS!r} vs {self.ts!r})")
                return
            if _QB_VIBRATED:
                return
            _QB_VIBRATED = True
            play_vibration(self.plugin)
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
            layout = param.thisObject
            res = param.getResult()
            in_prog = qb_bool_field(layout, "predictiveBackInProgress")
            stack_dump = qb_stack_dump(layout)
            _qb_log(self.plugin, f"onBackStarted: result={res!r}, in_progress={in_prog!r}, stack={stack_dump}")

            if res is False:
                _qb_log(self.plugin, "ignored: onBackStarted returned False")
                return

            stack = layout.getFragmentStack()
            size = int(stack.size()) if stack is not None else 0
            if size < 3:
                _qb_log(self.plugin, f"ignored: stack depth ({size}) < 3, no intermediate screens to skip")
                return

            if not qb_gesture_active(layout):
                _qb_log(self.plugin, "ignored: predictiveBackInProgress is False")
                return

            target_info = qb_hold_target(self.plugin, layout)
            if target_info is None:
                _qb_log(self.plugin, f"ignored: no eligible target in stack ({stack_dump})")
                return

            _, _, target_index, target_fragment = target_info
            target_name = target_fragment.getClass().getSimpleName()
            threshold = _qb_threshold_sec(self.plugin)
            _QB_BACK_START_TS = time.monotonic()
            _QB_VIBRATED = False

            _qb_log(
                self.plugin,
                f"tracking hold gesture -> target={target_name} (idx {target_index}), threshold={threshold:.2f}s",
            )
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
        _qb_log(
            self.plugin,
            f"onBackCancelled (tracking={'active' if _QB_BACK_START_TS else 'none'}, dirty={_QB_DIRTY})",
        )
        _QB_BACK_START_TS = None
        _QB_VIBRATED = False
        _qb_revert(self.plugin, param.thisObject, "gesture cancelled")


class _QbOnBackInvokedHook(MethodHook):
    def __init__(self, plugin):
        self.plugin = plugin

    def before_hooked_method(self, param):
        global _QB_BACK_START_TS, _QB_VIBRATED, _QB_SNAPSHOT, _QB_SWAP_TS, _QB_DIRTY, _QB_INTERMEDIATE, _QB_TARGET_FRAGMENT
        qb_reset_animated_view()
        try:
            start = _QB_BACK_START_TS
            layout = param.thisObject
            _qb_log(
                self.plugin,
                f"onBackInvoked: tracking={'active' if start else 'none'}, dirty={_QB_DIRTY}",
            )
            if start is None or _QB_SWAP_TS != start:
                if _QB_DIRTY:
                    _qb_log(self.plugin, "back invoked for another gesture, reverting")
                    _qb_revert(self.plugin, layout, "stale swap")
                return

            held = time.monotonic() - start
            threshold = _qb_threshold_sec(self.plugin)
            if held < threshold or not qb_gesture_active(layout):
                _qb_log(self.plugin, f"back released after {held:.2f}s < threshold {threshold:.2f}s, no jump")
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
                f"back held for {held:.2f}s >= {threshold:.2f}s, {removed} skipped screen(s) dropped | {qb_stack_dump(layout)}",
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


def _qb_diagnose_env(plugin):
    try:
        Build = find_class("android.os.Build$VERSION")
        sdk = int(getattr(Build, "SDK_INT", 0)) if Build else 0

        extera_info = "unknown"
        ExteraConfig = find_class("com.exteragram.messenger.ExteraConfig")
        if ExteraConfig is not None:
            try:
                field = ExteraConfig.getClass().getDeclaredField("predictiveBackAnimation")
                field.setAccessible(True)
                val = bool(field.get(None))
                extera_info = f"predictiveBackAnimation={val}"
            except Exception:
                try:
                    method = ExteraConfig.getClass().getDeclaredMethod("getPredictiveBackIntensity")
                    method.setAccessible(True)
                    val = float(method.invoke(None))
                    extera_info = f"predictiveBackIntensity={val}"
                except Exception:
                    pass

        _qb_log(plugin, f"env: Android SDK {sdk}, extera={extera_info}")
        if sdk < 34:
            _qb_log(
                plugin,
                f"ATTENTION: Android SDK is {sdk} < 34! Predictive back requires Android 14+ (API 34).",
            )
        elif "predictiveBackAnimation=False" in extera_info or "predictiveBackIntensity=0" in extera_info:
            _qb_log(
                plugin,
                "ATTENTION: Predictive back animation is DISABLED in exteraGram settings! Enable it in exteraGram settings and restart the app.",
            )
    except Exception as e:
        _qb_log(plugin, f"diagnose env failed: {e}")


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

        qb_cache_prepare_moving(plugin)
        _QB_INSTALLED = True
        _qb_log(plugin, f"quick back hooks installed ({len(_QB_HOOK_REFS)})")
        _qb_diagnose_env(plugin)
    except Exception as e:
        _qb_log(plugin, f"install error: {e}")


def uninstall_quick_back(plugin):
    global _QB_INSTALLED, _QB_BACK_START_TS, _QB_THRESHOLD_RUNNABLE, _QB_SNAPSHOT, _QB_SWAP_TS, _QB_DIRTY, _QB_INTERMEDIATE, _QB_TARGET_FRAGMENT
    qb_reset_animated_view()
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
