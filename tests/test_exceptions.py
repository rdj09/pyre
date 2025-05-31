import unittest
from pyre.exceptions.exceptions import (
    GeneralException,
    ExposureException,
    ClaimsException,
    ContractException
)

class TestGeneralException(unittest.TestCase):
    def test_init_with_identifier(self):
        exception = GeneralException("Test error message", "TEST001")
        self.assertEqual(exception.message, "Test error message")
        self.assertEqual(exception.identifier, "TEST001")
        self.assertEqual(str(exception), "Exception: Test error message (ID: TEST001)")
    
    def test_init_without_identifier(self):
        exception = GeneralException("Test error message", None)
        self.assertEqual(exception.message, "Test error message")
        self.assertIsNone(exception.identifier)
        self.assertEqual(str(exception), "Exception: Test error message")
    
    def test_format_message(self):
        exception = GeneralException("Test error message", "TEST001")
        self.assertEqual(exception._format_message(), "Exception: Test error message (ID: TEST001)")
        
        exception = GeneralException("Test error message", None)
        self.assertEqual(exception._format_message(), "Exception: Test error message")

class TestExposureException(unittest.TestCase):
    def test_init(self):
        exception = ExposureException("Invalid exposure data", "EXP001")
        self.assertEqual(exception.message, "Invalid exposure data")
        self.assertEqual(exception.identifier, "EXP001")
        self.assertEqual(str(exception), "Exception: Invalid exposure data (ID: EXP001)")
        
        # Test inheritance from GeneralException
        self.assertIsInstance(exception, GeneralException)

class TestClaimsException(unittest.TestCase):
    def test_init(self):
        exception = ClaimsException("Invalid claim data", "CLM001")
        self.assertEqual(exception.message, "Invalid claim data")
        self.assertEqual(exception.identifier, "CLM001")
        self.assertEqual(str(exception), "Exception: Invalid claim data (ID: CLM001)")
        
        # Test inheritance from GeneralException
        self.assertIsInstance(exception, GeneralException)

class TestContractException(unittest.TestCase):
    def test_init(self):
        exception = ContractException("Invalid contract data", "CNT001")
        self.assertEqual(exception.message, "Invalid contract data")
        self.assertEqual(exception.identifier, "CNT001")
        self.assertEqual(str(exception), "Exception: Invalid contract data (ID: CNT001)")
        
        # Test inheritance from GeneralException
        self.assertIsInstance(exception, GeneralException)

if __name__ == "__main__":
    unittest.main()