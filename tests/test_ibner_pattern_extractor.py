import unittest
from pyre.claims.triangles import Triangle, IBNERPatternExtractor

class TestIBNERPatternExtractor(unittest.TestCase):
    def setUp(self):
        # Create a sample triangle for testing
        self.triangle_data = {
            2020: {12: 100, 24: 150, 36: 175},
            2021: {12: 120, 24: 180},
            2022: {12: 110}
        }
        self.triangle = Triangle(triangle=self.triangle_data)
        self.extractor = IBNERPatternExtractor(triangle=self.triangle)
    
    def test_compute_N_and_D(self):
        # Test the internal computation method
        self.extractor._compute_N_and_D()
        
        # Check that N and D triangles were created
        self.assertIsNotNone(self.extractor._N_triangle)
        self.assertIsNotNone(self.extractor._D_triangle)
        
        # Check some values in the N triangle
        self.assertEqual(self.extractor._N_triangle[2020][12], 100)
        self.assertEqual(self.extractor._N_triangle[2020][24], 150)
        
        # Check some values in the D triangle
        self.assertEqual(self.extractor._D_triangle[2020][12], 100)
        self.assertEqual(self.extractor._D_triangle[2020][24], 150/100)
    
    def test_get_N_triangle(self):
        N_triangle = self.extractor.get_N_triangle()
        self.assertIsInstance(N_triangle, Triangle)
        self.assertEqual(N_triangle[2020][12], 100)
        self.assertEqual(N_triangle[2020][24], 150)
        self.assertEqual(N_triangle[2020][36], 175)
    
    def test_get_D_triangle(self):
        D_triangle = self.extractor.get_D_triangle()
        self.assertIsInstance(D_triangle, Triangle)
        self.assertEqual(D_triangle[2020][12], 1.0)
        self.assertEqual(D_triangle[2020][24], 1.5)
        self.assertEqual(D_triangle[2020][36], 175/150)
    
    def test_get_IBNER_pattern(self):
        pattern = self.extractor.get_IBNER_pattern()
        
        # Check that we get a dictionary
        self.assertIsInstance(pattern, dict)
        
        # Check that all years are included
        for year in [2020, 2021, 2022]:
            self.assertIn(year, pattern)
        
        # Check that the pattern values make sense
        # For 2020, we have data up to 36 months, so the pattern should be 1.0
        self.assertEqual(pattern[2020], 1.0)
        
        # For 2021, we have data up to 24 months, so the pattern should be the ratio
        # of the 36-month to 24-month development for 2020
        expected_2021 = 175/150
        self.assertAlmostEqual(pattern[2021], expected_2021)
        
        # For 2022, we have data up to 12 months, so the pattern should be the ratio
        # of the 36-month to 12-month development for 2020
        expected_2022 = 175/100
        self.assertAlmostEqual(pattern[2022], expected_2022)

if __name__ == "__main__":
    unittest.main()