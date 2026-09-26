from hook_utils import find_class, set_private_field

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
    in_progress = qb_bool_field(layout, "predictiveBackInProgress")
    if in_progress is None:
        return True
    return in_progress


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


def is_archive(candidate):
    if candidate is None:
        return False
    try:
        DialogsActivity = find_class("org.telegram.ui.DialogsActivity")
        if DialogsActivity is not None and isinstance(candidate, DialogsActivity):
            return bool(candidate.isArchive())
    except Exception:
        pass
    return False


def find_first_chat(stack, start, end):
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


def find_main_fragment(layout):
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
    except Exception:
        pass
    return -1, None


def qb_hold_target(plugin, layout):
    try:
        stack = layout.getFragmentStack()
        size = int(stack.size())
        if size < 3:
            return None

        top = stack.get(size - 1)
        if is_archive(top):
            return None

        mode = int(plugin.get_setting(CONF_TARGET_MODE, 0) or 0)

        target_index = -1
        target_fragment = None

        if mode == 1:
            if size > 2 and is_archive(stack.get(1)):
                chat_index, chat_fragment = find_first_chat(stack, start=2, end=size - 1)
                if chat_fragment is not None:
                    target_index, target_fragment = chat_index, chat_fragment
                else:
                    target_index, target_fragment = find_main_fragment(layout)
            else:
                target_index = 1
                target_fragment = stack.get(1)
        else:
            target_index, target_fragment = find_main_fragment(layout)

        if target_fragment is None or target_index < 0:
            target_index = 0
            target_fragment = stack.get(0)

        if target_index >= size - 2:
            return None

        return stack, size, target_index, target_fragment
    except Exception:
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
        method = ActionBarLayout.getClass().getDeclaredMethod("prepareForMoving")
        method.setAccessible(True)
        _QB_PREPARE_MOVING = method
        return True
    except Exception:
        return False


def qb_prepare_moving(layout):
    try:
        if _QB_PREPARE_MOVING is None:
            return False
        _QB_PREPARE_MOVING.invoke(layout)
        return True
    except Exception:
        return False


def qb_transition_background(layout):
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
    except Exception:
        return False
