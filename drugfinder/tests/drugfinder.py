import os
from pathlib import Path
from unittest import TestCase, main
from drugfinder.core import DrugFinder


class TestDrugFinder(TestCase):

    def setUp(self) -> None:
        drugbank_data = os.environ['DRUGBANK_DATA'] if 'DRUGBANK_DATA' in os.environ else os.path.join(Path.home(), 'drugbank_data')
        self.matcher = DrugFinder(drugbank_fp=drugbank_data)

    def test_info(self):
        self.assertNotEqual(self.matcher.get_info(), {})  # add assertion here


if __name__ == '__main__':
    main()
