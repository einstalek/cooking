from unittest import TestCase

from RedisCursor import RedisCursor


class TestDispatcher(TestCase):
    def test_inst(self):
        disp1 = RedisCursor()
        disp2 = RedisCursor(port=1234)
        assert disp1.inst() == disp2.inst()
