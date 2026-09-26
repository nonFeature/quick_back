from hook_utils import find_class, get_private_field, set_private_field
from ui.settings import CONF_TARGET_MODE

_QB_FIELDS = {}
_QB_MISSING = object()
_QB_PREPARE_MOVING = None


def qb_bool_field(target, name):
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
        except Exception:
            pass
        _QB_FIELDS[name] = field
    if field is None:
        return None
    try:
        return bool(field.get(target))
    except Exception:
        return None


def qb_gesture_active(layout):
    in_pred = qb_bool_field(layout, "predictiveBackInProgress")
    if in_pred:
        return True
    in_track = qb_bool_field(layout, "startedTracking")
    if in_track:
        return True
    if in_pred is None and in_track is None:
        return True
    return False


def qb_stack_dump(layout):
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


def _is_class(obj, *class_names):
    if obj is None:
        return False
    try:
        cls = obj.getClass()
        while cls is not None:
            name = cls.getName()
            simple = cls.getSimpleName()
            for c in class_names:
                if c == name or c == simple:
                    return True
            cls = cls.getSuperclass()
    except Exception:
        pass
    return False


def find_main_fragment(layout):
    try:
        stack = layout.getFragmentStack()
        if stack is None or stack.isEmpty():
            return -1, None
        size = int(stack.size())
        for i in range(size):
            fragment = stack.get(i)
            if fragment is None:
                continue
            if _is_class(fragment, "MainTabsActivity", "org.telegram.ui.MainTabsActivity"):
                return i, fragment
            if _is_class(fragment, "DialogsActivity", "org.telegram.ui.DialogsActivity"):
                return i, fragment
        return 0, stack.get(0)
    except Exception:
        pass
    return -1, None


def qb_hold_target(plugin, layout):
    try:
        stack = layout.getFragmentStack()
        size = int(stack.size())
        if size < 3:
            return None

        mode = int(plugin.get_setting(CONF_TARGET_MODE, 0) or 0)

        target_index = -1
        target_fragment = None

        if mode == 1:
            target_index = 1
            target_fragment = stack.get(1)
            if target_index >= size - 2:
                target_index, target_fragment = find_main_fragment(layout)
        else:
            target_index, target_fragment = find_main_fragment(layout)

        if target_fragment is None or target_index < 0:
            target_index = 0
            target_fragment = stack.get(0)

        if target_index >= size - 2:
            return None

        return stack, size, target_index, target_fragment
    except Exception as e:
        if plugin is not None:
            try:
                plugin.log(f"[Quick Back] hold target resolve error: {e}")
            except Exception:
                pass
        return None


def qb_stack_snapshot(stack, size):
    try:
        return [stack.get(i) for i in range(size)]
    except Exception:
        return None


def qb_apply_order(layout, fragments):
    try:
        stack = layout.getFragmentStack()
        stack.clear()
        for fragment in fragments:
            stack.add(fragment)
        return True
    except Exception:
        return False


def qb_target_behind_top(layout, stack, size, target_index, target_fragment):
    snapshot = qb_stack_snapshot(stack, size)
    if snapshot is None:
        return None, None

    screens_below = snapshot[0:target_index]
    target = snapshot[target_index]
    intermediate = snapshot[target_index + 1 : size - 1]
    top = snapshot[size - 1]

    ordered = screens_below + intermediate + [target, top]
    if not qb_apply_order(layout, ordered):
        return None, None

    try:
        if stack.get(int(stack.size()) - 2) != target_fragment:
            return None, None
    except Exception:
        return None, None

    return snapshot, intermediate


def qb_cache_prepare_moving(plugin=None):
    global _QB_PREPARE_MOVING
    if _QB_PREPARE_MOVING is not None:
        return True
    try:
        ActionBarLayout = find_class("org.telegram.ui.ActionBar.ActionBarLayout")
        if not ActionBarLayout:
            return False
        cls = ActionBarLayout.getClass() if hasattr(ActionBarLayout, "getClass") else ActionBarLayout
        while cls is not None:
            try:
                for m in cls.getDeclaredMethods():
                    if m.getName() == "prepareForMoving":
                        m.setAccessible(True)
                        _QB_PREPARE_MOVING = m
                        return True
            except Exception:
                pass
            try:
                cls = cls.getSuperclass()
            except Exception:
                break
    except Exception as e:
        if plugin is not None:
            try:
                plugin.log(f"[Quick Back] cache prepareForMoving failed: {e}")
            except Exception:
                pass
    return False


def _manual_prepare_moving(layout):
    try:
        stack = layout.getFragmentStack()
        if stack is None:
            return False
        size = int(stack.size())
        if size < 2:
            return False
        fragment = stack.get(size - 2)
        if fragment is None:
            return False

        if hasattr(fragment, "prepareFragmentToSlide"):
            try:
                fragment.prepareFragmentToSlide(True, False)
            except Exception:
                pass

        view = getattr(fragment, "fragmentView", None)
        if view is None:
            try:
                act = getattr(layout, "parentActivity", None)
                if act is None:
                    act = get_private_field(layout, "parentActivity")
                if act is not None:
                    view = fragment.createView(act)
            except Exception as e:
                print(f"[Quick Back] manual createView error: {e}")

        if view is not None:
            parent = view.getParent()
            if parent is not None:
                if hasattr(fragment, "onRemoveFromParent"):
                    try:
                        fragment.onRemoveFromParent()
                    except Exception:
                        pass
                parent.removeView(view)

            back = get_private_field(layout, "containerViewBack")
            if back is not None:
                back_parent = back.getParent()
                if back_parent is None:
                    layout.addView(back, 0)
                back.addView(view)
                back.setVisibility(0)
                return True
    except Exception as e:
        print(f"[Quick Back] manual prepare moving error: {e}")
    return False


def qb_prepare_moving(layout):
    if _QB_PREPARE_MOVING is not None:
        try:
            param_count = len(_QB_PREPARE_MOVING.getParameterTypes())
            if param_count == 0:
                _QB_PREPARE_MOVING.invoke(layout)
            elif param_count == 1:
                _QB_PREPARE_MOVING.invoke(layout, True)
            return True
        except Exception as e:
            print(f"[Quick Back] cached prepareForMoving invoke error: {e}")

    if hasattr(layout, "prepareForMoving"):
        try:
            layout.prepareForMoving()
            return True
        except Exception as e:
            print(f"[Quick Back] direct layout.prepareForMoving() error: {e}")

    try:
        cls = layout.getClass()
        while cls is not None:
            for m in cls.getDeclaredMethods():
                if m.getName() == "prepareForMoving":
                    m.setAccessible(True)
                    param_count = len(m.getParameterTypes())
                    if param_count == 0:
                        m.invoke(layout)
                    elif param_count == 1:
                        m.invoke(layout, True)
                    return True
            cls = cls.getSuperclass()
    except Exception as e:
        print(f"[Quick Back] dynamic prepareForMoving search error: {e}")

    return _manual_prepare_moving(layout)


def qb_transition_background(layout):
    for helper_name in (
        "com.exteragram.messenger.utils.ui.PredictiveBackAnimationHelper",
        "org.telegram.ui.ActionBar.PredictiveBackAnimationHelper",
        "org.telegram.ui.PredictiveBackAnimationHelper",
    ):
        try:
            Helper = find_class(helper_name)
            if not Helper:
                continue
            background = Helper.getTransitionBackground(layout.getFragmentStack(), layout.getLastFragment())
            if background is not None:
                set_private_field(layout, "predictiveBackBackgroundDrawable", background)
                try:
                    set_private_field(layout, "springRouteBackgroundDrawable", background)
                except Exception:
                    pass
                return True
        except Exception:
            continue
    return False
