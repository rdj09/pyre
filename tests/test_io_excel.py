import tempfile
import unittest
from datetime import date
from pathlib import Path

try:
    import openpyxl
    from openpyxl import Workbook

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


@unittest.skipUnless(HAS_OPENPYXL, "openpyxl not installed; pip install -e '.[excel]'")
class TestReadClaims(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "claims.xlsx"

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write_claims_sheet(self, rows, headers=None, sheet_name="Claims", trailing_blank_row=False):
        headers = headers or [
            "claim_id", "currency", "contract_limit",
            "loss_date", "development_month", "cumulative_paid", "cumulative_incurred",
        ]
        wb = Workbook()
        ws = wb.active
        ws.title = sheet_name
        ws.append(headers)
        for row in rows:
            ws.append(row)
        if trailing_blank_row:
            ws.append([None] * len(headers))
        wb.save(self.path)

    def test_builds_claims_with_correct_dev_history(self):
        from pyre.io_excel.claims_io import read_claims

        self._write_claims_sheet(
            [
                ["CLM001", "USD", 2000000, date(2022, 3, 1), 12, 50000, 120000],
                ["CLM001", "USD", 2000000, date(2022, 3, 1), 24, 90000, 250000],
                ["CLM002", "USD", 2000000, date(2022, 7, 10), 12, 20000, 60000],
            ]
        )

        claims = read_claims(self.path)
        self.assertEqual(sorted(claims.modelling_years), [2022])

        by_id = {c.claims_meta_data.claim_id: c for c in claims.claims}
        self.assertEqual(
            by_id["CLM001"].capped_claim_development_history.cumulative_dev_paid,
            [50000.0, 90000.0],
        )
        self.assertEqual(
            by_id["CLM001"].capped_claim_development_history.development_months,
            [12, 24],
        )

    def test_accepts_iso_string_dates_as_well_as_native_excel_dates(self):
        from pyre.io_excel.claims_io import read_claims

        self._write_claims_sheet(
            [["CLM001", "USD", 2000000, "2022-03-01", 12, 50000, 120000]]
        )

        claims = read_claims(self.path)
        self.assertEqual(claims.claims[0].claims_meta_data.loss_date, date(2022, 3, 1))

    def test_rejects_missing_required_column(self):
        from pyre.io_excel.claims_io import read_claims

        self._write_claims_sheet(
            rows=[["CLM001", "USD", 12, 50000, 120000]],
            headers=["claim_id", "currency", "development_month", "cumulative_paid", "cumulative_incurred"],
        )

        with self.assertRaises(ValueError):
            read_claims(self.path)

    def test_rejects_missing_or_zero_contract_limit(self):
        from pyre.io_excel.claims_io import read_claims

        self._write_claims_sheet(
            [["CLM001", "USD", 0, date(2022, 3, 1), 12, 50000, 120000]]
        )

        with self.assertRaises(ValueError):
            read_claims(self.path)

    def test_ignores_trailing_blank_row(self):
        from pyre.io_excel.claims_io import read_claims

        self._write_claims_sheet(
            [["CLM001", "USD", 2000000, date(2022, 3, 1), 12, 50000, 120000]],
            trailing_blank_row=True,
        )

        claims = read_claims(self.path)
        self.assertEqual(len(claims), 1)

    def test_missing_optional_column_entirely_defaults_cleanly(self):
        from pyre.io_excel.claims_io import read_claims

        # No "claim_year_basis", "contract_deductible", "line_of_business" etc. columns at all
        self._write_claims_sheet(
            [["CLM001", "USD", 2000000, date(2022, 3, 1), 12, 50000, 120000]]
        )

        claims = read_claims(self.path)  # must not raise KeyError
        self.assertEqual(claims.claims[0].claims_meta_data.contract_deductible, 0.0)
        self.assertEqual(claims.claims[0].claims_meta_data.status, "Open")


@unittest.skipUnless(HAS_OPENPYXL, "openpyxl not installed; pip install -e '.[excel]'")
class TestReadExposures(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "exposures.xlsx"

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write_exposures_sheet(self, rows, headers=None, trailing_blank_row=False):
        headers = headers or [
            "exposure_id", "exposure_name", "exposure_period_start",
            "exposure_period_end", "currency", "exposure_value",
        ]
        wb = Workbook()
        ws = wb.active
        ws.title = "Exposures"
        ws.append(headers)
        for row in rows:
            ws.append(row)
        if trailing_blank_row:
            ws.append([None] * len(headers))
        wb.save(self.path)

    def test_builds_exposures(self):
        from pyre.io_excel.exposures_io import read_exposures

        self._write_exposures_sheet(
            [
                ["EXP2022", "2022 Premium", date(2022, 1, 1), date(2022, 12, 31), "USD", 1000000],
                ["EXP2023", "2023 Premium", date(2023, 1, 1), date(2023, 12, 31), "USD", 1200000],
            ]
        )

        exposures = read_exposures(self.path)
        self.assertEqual(sorted(exposures.modelling_years), [2022, 2023])

    def test_rejects_missing_required_column(self):
        from pyre.io_excel.exposures_io import read_exposures

        self._write_exposures_sheet(
            rows=[["EXP2022", date(2022, 1, 1), date(2022, 12, 31), "USD", 1000000]],
            headers=["exposure_id", "exposure_period_start", "exposure_period_end", "currency", "exposure_value"],
        )

        with self.assertRaises(ValueError):
            read_exposures(self.path)

    def test_ignores_trailing_blank_row(self):
        from pyre.io_excel.exposures_io import read_exposures

        self._write_exposures_sheet(
            [["EXP2022", "2022 Premium", date(2022, 1, 1), date(2022, 12, 31), "USD", 1000000]],
            trailing_blank_row=True,
        )

        exposures = read_exposures(self.path)
        self.assertEqual(len(exposures), 1)

    def test_missing_optional_column_entirely_defaults_cleanly(self):
        from pyre.io_excel.exposures_io import read_exposures

        self._write_exposures_sheet(
            [["EXP2022", "2022 Premium", date(2022, 1, 1), date(2022, 12, 31), "USD", 1000000]]
        )

        exposures = read_exposures(self.path)  # must not raise KeyError
        self.assertEqual(exposures.exposures[0].exposure_values.attachment_point, 0.0)


if __name__ == "__main__":
    unittest.main()
