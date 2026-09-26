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


def is_predictive_back_supported() -> bool:
    global _CACHED_PREDICTIVE_SUPPORTED
    if _CACHED_PREDICTIVE_SUPPORTED is not None:
        return _CACHED_PREDICTIVE_SUPPORTED

    # 1. Android version check: Predictive back requires Android 14+ (API 34)
    sdk = get_android_sdk()
    if sdk < 34:
        _CACHED_PREDICTIVE_SUPPORTED = False
        return False

    # 2. Telegram version check: Predictive back was introduced in 12.2.0+
    ver_str = get_client_version()
    if ver_str != "Unknown":
        parsed = parse_version(ver_str)
        if parsed < (12, 2, 0):
            _CACHED_PREDICTIVE_SUPPORTED = False
            return False

    # 3. Method check on ActionBarLayout: must have onBackStarted
    try:
        ActionBarLayout = find_class("org.telegram.ui.ActionBar.ActionBarLayout")
        if ActionBarLayout is None:
            _CACHED_PREDICTIVE_SUPPORTED = False
            return False

        cls = ActionBarLayout
        has_on_back_started = False
        while cls is not None:
            for m in cls.getDeclaredMethods():
                if m.getName() == "onBackStarted":
                    has_on_back_started = True
                    break
            if has_on_back_started:
                break
            cls = cls.getSuperclass()

        if not has_on_back_started:
            _CACHED_PREDICTIVE_SUPPORTED = False
            return False
    except Exception:
        _CACHED_PREDICTIVE_SUPPORTED = False
        return False

    _CACHED_PREDICTIVE_SUPPORTED = True
    return True


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
