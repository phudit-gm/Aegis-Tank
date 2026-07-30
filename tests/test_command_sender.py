import socket
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.actuators.command_sender import CommandSender


class TestCommandSender(unittest.TestCase):
    def setUp(self):
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.settimeout(1.0)
        host, port = self.listener.getsockname()
        self.sender = CommandSender(host, port)

    def tearDown(self):
        self.sender.close()
        self.listener.close()

    def _recv(self):
        data, _ = self.listener.recvfrom(1024)
        return data.decode("utf-8")

    def test_track(self):
        self.sender.track("FORWARD", 300)  # exceeds range, must be clamped to 255
        self.assertEqual(self._recv(), "TRACK:FORWARD:255")

    def test_track_pivot(self):
        self.sender.track("PIVOT_LEFT", 150)
        self.assertEqual(self._recv(), "TRACK:PIVOT_LEFT:150")

    def test_turret(self):
        self.sender.turret("LEFT", 300)  # exceeds range, must be clamped to 255
        self.assertEqual(self._recv(), "TURRET:LEFT:255")

    def test_turret_invalid_direction(self):
        with self.assertRaises(ValueError):
            self.sender.turret("UP", 100)

    def test_tilt(self):
        self.sender.tilt("DOWN", -10)  # below range, must be clamped to 0
        self.assertEqual(self._recv(), "TILT:DOWN:0")

    def test_tilt_up_not_allowed(self):
        # No UP in the protocol — tilting up is via return spring (SPEC.md §1)
        with self.assertRaises(ValueError):
            self.sender.tilt("UP", 100)

    def test_fire(self):
        self.sender.fire("ON", 1000)
        self.assertEqual(self._recv(), "FIRE:ON:1000")

    def test_invalid_track_direction(self):
        with self.assertRaises(ValueError):
            self.sender.track("SIDEWAYS", 100)

    def test_missing_host_raises(self):
        with self.assertRaises(ValueError):
            CommandSender(None, 5555)


if __name__ == "__main__":
    unittest.main()
