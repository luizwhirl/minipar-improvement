"""Compile the real channel helper and check complete, ordered TCP messages."""
from pathlib import Path
import os
import shutil
import socket
import subprocess
import tempfile
import unittest

from src.cpp_template import _CPP_HEADER


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("g++"), "Requires g++ on PATH")
class ChannelMessageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / "output").mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "output", prefix="channel-messages-")
        cls.addClassCleanup(temporary.cleanup)
        work = Path(temporary.name)
        source = work / "messages.cpp"
        cls.executable = work / ("messages.exe" if os.name == "nt" else "messages")
        source.write_text(_CPP_HEADER + r'''
int main(int argc, char** argv) {
    if (argc != 3) return 2;
    #ifdef _WIN32
        WSADATA wsa;
        if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) return 3;
    #endif
    MiniParChannel channel("127.0.0.1", std::stoi(argv[1]));
    const bool large = std::string(argv[2]) == "large";
    const std::vector<std::string> expected = large
        ? std::vector<std::string>{std::string(9000, 'Z'), "", "Ol\xC3\xA1 \xF0\x9F\xA7\xB5"}
        : std::vector<std::string>{"alpha", "beta", "gamma"};
    bool correct = true;
    std::thread receiver([&]() {
        try {
            for (size_t index = 0; index < expected.size(); ++index) {
                const auto message = channel.receiveData();
                const bool same = message == expected[index];
                correct = correct && same;
                std::cout << index << ":" << message.size() << ":" << same << std::endl;
            }
        } catch (const std::exception& error) {
            correct = false;
            std::cerr << "receive: " << error.what() << std::endl;
        }
    });
    std::thread sender([&]() {
        try {
            for (const auto& message : expected) channel.sendData(message);
        } catch (const std::exception& error) {
            std::cerr << "send: " << error.what() << std::endl;
        }
    });
    sender.join();
    receiver.join();
    return correct ? 0 : 1;
}
''', encoding="utf-8")
        command = ["g++", "-std=c++20", "-O2", str(source), "-o", str(cls.executable), "-pthread"]
        if os.name == "nt":
            command.append("-lws2_32")
        compiled = subprocess.run(command, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=30)
        if compiled.returncode:
            raise AssertionError(compiled.stderr)

    def exchange(self, profile):
        # A separate ephemeral port prevents collisions with the example
        # programs and lets each child exercise a fresh channel lifecycle.
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        result = subprocess.run([str(self.executable), str(port), profile],
                                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=8)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "", result.stderr)
        return result.stdout.splitlines()

    def test_large_empty_and_unicode_messages_remain_complete_across_repeated_connections(self):
        for attempt in range(10):
            with self.subTest(attempt=attempt):
                self.assertEqual(self.exchange("large"), ["0:9000:1", "1:0:1", "2:9:1"])

    def test_three_short_messages_keep_their_order(self):
        self.assertEqual(self.exchange("short"), ["0:5:1", "1:4:1", "2:5:1"])


if __name__ == "__main__":
    unittest.main()
