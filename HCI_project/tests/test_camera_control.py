import unittest
from unittest.mock import Mock

from camera_control import read_camera_frame


class CameraControlTests(unittest.TestCase):
    def test_turning_camera_off_releases_it_without_reading(self):
        capture = Mock()
        capture.isOpened.return_value = True
        self.assertEqual(read_camera_frame(capture, False), (True, None))
        capture.release.assert_called_once()
        capture.read.assert_not_called()

    def test_turning_camera_back_on_reopens_capture(self):
        capture = Mock()
        capture.isOpened.return_value = False
        capture.open.return_value = True
        capture.read.return_value = (True, "test frame")
        self.assertEqual(read_camera_frame(capture, True), (True, "test frame"))
        capture.open.assert_called_once_with(0)

    def test_failed_camera_reopen_is_reported(self):
        capture = Mock()
        capture.isOpened.return_value = False
        capture.open.return_value = False
        self.assertEqual(read_camera_frame(capture, True), (False, None))
        capture.read.assert_not_called()


if __name__ == "__main__":
    unittest.main()
