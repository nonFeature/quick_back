from hook_utils import get_private_field


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
