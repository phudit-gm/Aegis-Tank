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
        self.sender.track("FORWARD", 300)  # เกิน range ต้องถูก clamp เป็น 255
        self.assertEqual(self._recv(), "TRACK:FORWARD:255")

    def test_turret_clamp(self):
        self.sender.turret(200)  # เกิน 180
        self.assertEqual(self._recv(), "TURRET:PAN:180")

    def test_tilt_clamp(self):
        self.sender.tilt(-999)
        self.assertEqual(self._recv(), "TILT:PITCH:-90")

    def test_laser(self):
        self.sender.laser("ON", 1000)
        self.assertEqual(self._recv(), "LASER:ON:1000")

    def test_invalid_direction(self):
        with self.assertRaises(ValueError):
            self.sender.track("SIDEWAYS", 100)

    def test_missing_host_raises(self):
        with self.assertRaises(ValueError):
            CommandSender(None, 5555)


if __name__ == "__main__":
    unittest.main()
