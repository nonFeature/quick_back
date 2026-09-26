import re

from hook_utils import find_class, get_private_field

_CACHED_SDK = None
_CACHED_VERSION = None
_CACHED_PREDICTIVE_SUPPORTED = None


def get_android_sdk() -> int:
    global _CACHED_SDK
    if _CACHED_SDK is not None:
        return _CACHED_SDK
    try:
        Build = find_class("android.os.Build$VERSION")
        _CACHED_SDK = int(getattr(Build, "SDK_INT", 0)) if Build else 0
    except Exception:
        _CACHED_SDK = 0
    return _CACHED_SDK


def get_client_version() -> str:
    global _CACHED_VERSION
    if _CACHED_VERSION is not None:
        return _CACHED_VERSION
    try:
        BuildVars = find_class("org.telegram.messenger.BuildVars")
        if BuildVars:
            val = getattr(BuildVars, "BUILD_VERSION_STRING", None) or getattr(BuildVars, "BUILD_VERSION", None)
            if val is not None:
                _CACHED_VERSION = str(val)
                return _CACHED_VERSION
    except Exception:
        pass
    _CACHED_VERSION = "Unknown"
    return _CACHED_VERSION


def parse_version(version_str: str) -> tuple:
    try:
        nums = [int(n) for n in re.findall(r"\d+", version_str.split()[0])]
        while len(nums) < 3:
            nums.append(0)
        return tuple(nums[:3])
    except Exception:
        return (0, 0, 0)


def get_class_object(cls_or_obj):
    if cls_or_obj is None:
        return None
    try:
        if hasattr(cls_or_obj, "getClass"):
            c = cls_or_obj.getClass()
            if getattr(c, "getName", lambda: "")() != "java.lang.Class":
                return c
    except Exception:
        pass
    return cls_or_obj


def find_methods_by_name(cls_or_obj, method_name: str) -> list:
    results = []
    curr = get_class_object(cls_or_obj)
    visited = set()
    while curr is not None:
        try:
            curr_name = getattr(curr, "getName", lambda: None)()
            if curr_name in visited:
                break
            if curr_name:
                visited.add(curr_name)
        except Exception:
            pass

        try:
            for m in curr.getDeclaredMethods():
                if m.getName() == method_name:
                    results.append(m)
        except Exception:
            pass

        try:
            curr = curr.getSuperclass()
        except Exception:
            break

    return results


def find_field(cls_or_obj, field_name: str):
    curr = get_class_object(cls_or_obj)
    while curr is not None:
        try:
            f = curr.getDeclaredField(field_name)
            f.setAccessible(True)
            return f
        except Exception:
            pass
        try:
            curr = curr.getSuperclass()
        except Exception:
            break
    return None


def get_navigation_mode() -> int:
    try:
        ApplicationLoader = find_class("org.telegram.messenger.ApplicationLoader")
        context = getattr(ApplicationLoader, "applicationContext", None) if ApplicationLoader else None
        if context is None:
            return 2

        cr = context.getContentResolver()
        Settings_Secure = find_class("android.provider.Settings$Secure")
        Settings_Global = find_class("android.provider.Settings$Global")

        if Settings_Global is not None:
            try:
                miui_fsg = Settings_Global.getInt(cr, "force_fsg_nav_bar", -1)
                if miui_fsg == 1:
                    return 2
                elif miui_fsg == 0:
                    return 0
            except Exception:
                try:
                    miui_fsg = Settings_Global.getInt(cr, "force_fsg_nav_bar")
                    if miui_fsg == 1:
                        return 2
                    elif miui_fsg == 0:
                        return 0
                except Exception:
                    pass

        if Settings_Secure is not None:
            try:
                emui_nav = Settings_Secure.getInt(cr, "secure_gesture_navigation", -1)
                if emui_nav == 1:
                    return 2
                elif emui_nav == 0:
                    return 0
            except Exception:
                try:
                    emui_nav = Settings_Secure.getInt(cr, "secure_gesture_navigation")
                    if emui_nav == 1:
                        return 2
                    elif emui_nav == 0:
                        return 0
                except Exception:
                    pass

        if Settings_Secure is not None:
            try:
                vivo_nav = Settings_Secure.getInt(cr, "navigation_gesture_on", -1)
                if vivo_nav == 1:
                    return 2
                elif vivo_nav == 0:
                    return 0
            except Exception:
                try:
                    vivo_nav = Settings_Secure.getInt(cr, "navigation_gesture_on")
                    if vivo_nav == 1:
                        return 2
                    elif vivo_nav == 0:
                        return 0
                except Exception:
                    pass

        if Settings_Global is not None:
            try:
                sam_nav = Settings_Global.getInt(cr, "navigationbar_mode", -1)
                if sam_nav == 1:
                    return 2
                elif sam_nav == 0:
                    return 0
            except Exception:
                try:
                    sam_nav = Settings_Global.getInt(cr, "navigationbar_mode")
                    if sam_nav == 1:
                        return 2
                    elif sam_nav == 0:
                        return 0
                except Exception:
                    pass

        if Settings_Secure is not None:
            try:
                mode = Settings_Secure.getInt(cr, "navigation_mode", -1)
                if mode >= 0:
                    return int(mode)
            except Exception:
                try:
                    mode = Settings_Secure.getInt(cr, "navigation_mode")
                    return int(mode)
                except Exception:
                    pass

        try:
            Resources = find_class("android.content.res.Resources")
            if Resources is not None:
                sys_res = Resources.getSystem()
                res_id = int(sys_res.getIdentifier("config_navBarInteractionMode", "integer", "android"))
                if res_id > 0:
                    return int(sys_res.getInteger(res_id))
        except Exception:
            pass
    except Exception as e:
        print(f"[Quick Back] navigation mode error: {e}")

    return 2


def is_button_navigation() -> bool:
    return get_navigation_mode() in (0, 1)


def get_navigation_mode_name() -> str:
    mode = get_navigation_mode()
    if mode == 0:
        return "3-button"
    elif mode == 1:
        return "2-button"
    elif mode == 2:
        return "gestures"
    return f"unknown ({mode})"


_CACHED_PLATFORM_SUPPORTED = None


def is_predictive_back_platform_supported() -> bool:
    global _CACHED_PLATFORM_SUPPORTED
    if _CACHED_PLATFORM_SUPPORTED is not None:
        return _CACHED_PLATFORM_SUPPORTED

    sdk = get_android_sdk()
    if sdk < 34:
        _CACHED_PLATFORM_SUPPORTED = False
        return False

    ver_str = get_client_version()
    if ver_str != "Unknown":
        parsed = parse_version(ver_str)
        if parsed < (12, 2, 0):
            _CACHED_PLATFORM_SUPPORTED = False
            return False

    try:
        ActionBarLayout = find_class("org.telegram.ui.ActionBar.ActionBarLayout")
        if ActionBarLayout is not None:
            methods = find_methods_by_name(ActionBarLayout, "onBackStarted")
            if not methods:
                _CACHED_PLATFORM_SUPPORTED = False
                return False
    except Exception as e:
        print(f"[Quick Back] onBackStarted detection error: {e}")

    _CACHED_PLATFORM_SUPPORTED = True
    return True


def is_exteraless_predictive_disabled() -> bool:
    try:
        UtilsConfig = find_class("app.exteraless.utils.UtilsConfig")
        if UtilsConfig is not None:
            methods = find_methods_by_name(UtilsConfig, "predictiveBackIntensity")
            if methods:
                m = methods[0]
                m.setAccessible(True)
                val = float(m.invoke(None))
                if val <= 0.001:
                    return True

            field = find_field(UtilsConfig, "predictiveBackIntensity")
            if field is not None:
                item = field.get(None)
                if item is not None:
                    int_methods = find_methods_by_name(item, "Int")
                    if int_methods:
                        int_m = int_methods[0]
                        int_m.setAccessible(True)
                        if int(int_m.invoke(item)) <= 0:
                            return True
    except Exception:
        pass
    return False


exteraless_predictive = is_exteraless_predictive_disabled


def is_extera_predictive_disabled() -> bool:
    try:
        ExteraConfig = find_class("com.exteragram.messenger.ExteraConfig")
        if ExteraConfig is not None:
            methods = find_methods_by_name(ExteraConfig, "getPredictiveBackIntensity")
            if methods:
                m = methods[0]
                m.setAccessible(True)
                val = float(m.invoke(None))
                if val <= 0.001:
                    return True

            field = find_field(ExteraConfig, "predictiveBackAnimation")
            if field is not None:
                val = bool(field.get(None))
                if not val:
                    return True
    except Exception:
        pass
    return False


extera_predictive = is_extera_predictive_disabled


def is_tablet() -> bool:
    try:
        AndroidUtilities = find_class("org.telegram.messenger.AndroidUtilities")
        if AndroidUtilities is not None:
            return bool(AndroidUtilities.isTablet())
    except Exception:
        pass
    return False


def is_predictive_back_supported() -> bool:
    if not is_predictive_back_platform_supported():
        return False
    if is_tablet():
        return False
    if is_button_navigation():
        return False
    if is_exteraless_predictive_disabled():
        return False
    if is_extera_predictive_disabled():
        return False
    return True


def get_android_release() -> str:
    try:
        Build = find_class("android.os.Build$VERSION")
        if Build:
            val = getattr(Build, "RELEASE", None)
            if val:
                return str(val)
    except Exception:
        pass
    sdk = get_android_sdk()
    return f"API {sdk}" if sdk else "unknown"


def get_incompatibility_reason() -> str | None:
    if get_android_sdk() < 34:
        return "android_version"
    if not is_predictive_back_platform_supported():
        return "telegram_version"
    if is_tablet():
        return "tablet"
    if is_button_navigation():
        return "buttons"
    if is_exteraless_predictive_disabled() or is_extera_predictive_disabled():
        return "client_disabled"
    return None


class ContainerCore:
    def __init__(self):
        self.saved_children = None

    def _container_back(self, layout):
        try:
            return get_private_field(layout, "containerViewBack")
        except Exception:
            return None

    def clearBackContainer(self, layout):
        try:
            back = self._container_back(layout)
            if back is None:
                return False
            count = int(back.getChildCount())
            self.saved_children = [back.getChildAt(i) for i in range(count)]
            back.removeAllViews()
            return True
        except Exception as e:
            print(f"[Quick Back] clearBackContainer error: {e}")
            return False

    def restoreViews(self, layout):
        try:
            back = self._container_back(layout)
            if back is None or self.saved_children is None:
                return False
            back.removeAllViews()
            for child in self.saved_children:
                back.addView(child)
            self.saved_children = None
            return True
        except Exception as e:
            print(f"[Quick Back] restoreViews error: {e}")
            return False

    def dropSaved(self):
        self.saved_children = None


_CORE = ContainerCore()


def quick_back_core(plugin=None):
    return _CORE
