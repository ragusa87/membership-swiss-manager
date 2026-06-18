from django.test import SimpleTestCase

from core.utils import chf_to_centimes


class ChfToCentimesTest(SimpleTestCase):
    def test_whole_franc(self):
        self.assertEqual(chf_to_centimes("42"), 4200)

    def test_two_decimals(self):
        self.assertEqual(chf_to_centimes("42.50"), 4250)

    def test_avoids_binary_float_truncation(self):
        # int(float("64.10") * 100) yields 6409 due to binary FP; helper must return 6410.
        self.assertEqual(chf_to_centimes("64.10"), 6410)

    def test_zero(self):
        self.assertEqual(chf_to_centimes("0.00"), 0)

    def test_accepts_numeric(self):
        self.assertEqual(chf_to_centimes(42.5), 4250)
