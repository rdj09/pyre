import tempfile
import unittest
from pathlib import Path

try:
    import openpyxl

    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


@unittest.skipUnless(HAS_OPENPYXL, "openpyxl not installed; pip install -e '.[excel]'")
class TestWriteTable(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "out.xlsx"

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_writes_header_and_rows(self):
        from pyre.io_excel._workbook import write_table

        write_table(
            headers=["a", "b"],
            rows=[[1, 2], [3, 4]],
            path=self.path,
            sheet_name="Sheet1",
        )

        wb = openpyxl.load_workbook(self.path)
        ws = wb["Sheet1"]
        values = [list(row) for row in ws.iter_rows(values_only=True)]
        self.assertEqual(values, [["a", "b"], [1, 2], [3, 4]])

    def test_accepts_str_path_and_pathlib_path(self):
        from pyre.io_excel._workbook import write_table

        write_table(["a"], [[1]], str(self.path), sheet_name="S")
        write_table(["a"], [[1]], Path(self.path), sheet_name="S")  # must not raise

    def test_rewriting_same_sheet_overwrites_not_duplicates(self):
        from pyre.io_excel._workbook import write_table

        write_table(["a"], [[1], [2]], self.path, sheet_name="S")
        write_table(["a"], [[9]], self.path, sheet_name="S")  # re-run with different data

        wb = openpyxl.load_workbook(self.path)
        self.assertEqual(wb.sheetnames, ["S"])
        values = [list(row) for row in wb["S"].iter_rows(values_only=True)]
        self.assertEqual(values, [["a"], [9]])

    def test_second_sheet_is_appended_not_replacing_the_first(self):
        from pyre.io_excel._workbook import write_table

        write_table(["a"], [[1]], self.path, sheet_name="First")
        write_table(["b"], [[2]], self.path, sheet_name="Second")

        wb = openpyxl.load_workbook(self.path)
        self.assertEqual(set(wb.sheetnames), {"First", "Second"})


if __name__ == "__main__":
    unittest.main()
