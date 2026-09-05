import unittest
from scripts.validate_data_contract import main


class DataContractTest(unittest.TestCase):
    def test_data_contract(self) -> None:
        self.assertEqual(main(), 0)


if __name__ == "__main__":
    unittest.main()
