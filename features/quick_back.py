import time

from base_plugin import MethodHook
from hook_utils import find_class, get_private_field

from features.animation import qb_animate_target_view, qb_reset_animated_view
from features.stack import (
    qb_apply_order,
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
            if _QB_BACK_START_TS != self.ts or _QB_VIBRATED:
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
            if not param.getResult():
                return
            layout = param.thisObject
            if qb_hold_target(self.plugin, layout) is None:
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
        qb_reset_animated_view()
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
            if held < threshold or not qb_gesture_active(layout):
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
