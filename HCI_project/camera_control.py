"""Apply the menu's camera switch without changing gesture recognition."""


def read_camera_frame(capture, enabled):
    if not enabled:
        if capture.isOpened():
            capture.release()
        return True, None
    if not capture.isOpened() and not capture.open(0):
        return False, None
    return capture.read()
