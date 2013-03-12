import unittest
from localtunnel.server.frontend import peek_http_host


class Socket(object):
    def __init__(self, message):
        self.message = message

    def recv(self, length, flags):
        return self.message[0:length]


class TestFrontendPeek(unittest.TestCase):
    def _test(self, header, expected):
        actual = peek_http_host(Socket(header))
        self.assertEqual(actual, expected)

    def test_simple(self):
        self._test("Host: ABC\r\n", "ABC")
        self._test("Other: XX\r\nHost: ABC\r\n", "ABC")
        self._test("Other: XX\r\nHost: ABC\r\nMore: XX\r\n", "ABC")

    def test_without_newline(self):
        self._test("Host: ABC", None)

    def test_port(self):
        self._test("Host: ABC:8000\r\n", "ABC:8000")

    def test_peeking(self):
        # Make sure the first peek of 128 chars contains just `Host: A`
        header = "%s\r\nHost: ABC\r\n" % (" " * 119)
        self._test(header, "ABC")

        # Make sure the second peek of 256 chars contains just `Host: A`
        header = "%s\r\nHost: ABC\r\n" % (" " * 247)
        self._test(header, "ABC")

        # Make sure the third peek of 512 chars contains just `Host: A`
        header = "%s\r\nHost: ABC\r\n" % (" " * 503)
        self._test(header, "ABC")
