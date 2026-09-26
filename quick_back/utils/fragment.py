from hook_utils import find_class


def _frag_log(msg):
    try:
        from android_utils import log

        log(f"[Quick Back] {msg}")
    except Exception as e:
        print(f"[Quick Back] {msg} (log failed: {e})")


def java_runnable(func):
    try:
        from java import dynamic_proxy

        Runnable = find_class("java.lang.Runnable")
        proxy_cls = dynamic_proxy(Runnable)

        class _Runnable(proxy_cls):
            def run(self):
                func()

        return _Runnable()
    except Exception as e:
        _frag_log(f"Runnable proxy failed: {e}")
        return None


def post_ui(func, delay_ms=0):
    """AndroidUtilities.runOnUIThread with a Python callable."""
    try:
        AndroidUtilities = find_class("org.telegram.messenger.AndroidUtilities")
        runnable = java_runnable(func)
        if runnable is None:
            return False
        if delay_ms:
            AndroidUtilities.runOnUIThread(runnable, int(delay_ms))
        else:
            AndroidUtilities.runOnUIThread(runnable)
        return True
    except Exception as e:
        _frag_log(f"post to UI failed: {e}")
        return False
