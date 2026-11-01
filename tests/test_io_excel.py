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

from pyre import (
    Claim,
    ClaimDevelopmentHistory,
    Claims,
    ClaimsMetaData,
    ExperienceModelData,
    Exposure,
    ExposureMetaData,
    Exposures,
    ExposureValues,
    RIContract,
    RIContractMetadata,
    RILayer,
)
from pyre.treaty import ClaimTriggerBasis, ContractType, IndexationClauseType


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

    def test_writes_to_an_in_memory_buffer(self):
        import io

        from pyre.io_excel._workbook import write_table

        buffer = io.BytesIO()
        write_table(headers=["a", "b"], rows=[[1, 2]], path=buffer, sheet_name="Sheet1")

        buffer.seek(0)
        wb = openpyxl.load_workbook(buffer)
        values = [list(row) for row in wb["Sheet1"].iter_rows(values_only=True)]
        self.assertEqual(values, [["a", "b"], [1, 2]])

    def test_two_calls_on_the_same_buffer_both_sheets_present(self):
        import io

        from pyre.io_excel._workbook import write_table

        buffer = io.BytesIO()
        write_table(headers=["a"], rows=[[1]], path=buffer, sheet_name="First")
        write_table(headers=["b"], rows=[[2]], path=buffer, sheet_name="Second")

        buffer.seek(0)
        wb = openpyxl.load_workbook(buffer)
        self.assertEqual(set(wb.sheetnames), {"First", "Second"})


@unittest.skipUnless(HAS_OPENPYXL, "openpyxl not installed; pip install -e '.[excel]'")
class TestReadClaims(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "claims.xlsx"

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write_claims_sheet(
        self, rows, headers=None, sheet_name="Claims", trailing_blank_row=False
    ):
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
            headers=[
                "claim_id", "currency", "development_month",
                "cumulative_paid", "cumulative_incurred",
            ],
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

    def test_empty_sheet_raises_value_error_not_stop_iteration(self):
        from pyre.io_excel.claims_io import read_claims

        wb = Workbook()
        ws = wb.active
        ws.title = "Claims"
        wb.save(self.path)

        with self.assertRaises(ValueError):
            read_claims(self.path)

    def test_blank_development_month_raises_value_error_naming_the_claim(self):
        from pyre.io_excel.claims_io import read_claims

        self._write_claims_sheet(
            [["CLM001", "USD", 2000000, date(2022, 3, 1), None, 50000, 120000]]
        )

        with self.assertRaises(ValueError) as ctx:
            read_claims(self.path)
        self.assertIn("CLM001", str(ctx.exception))

    def test_blank_currency_raises_value_error_instead_of_string_none(self):
        from pyre.io_excel.claims_io import read_claims

        self._write_claims_sheet(
            [["CLM001", None, 2000000, date(2022, 3, 1), 12, 50000, 120000]]
        )

        with self.assertRaises(ValueError):
            read_claims(self.path)


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
            headers=[
                "exposure_id", "exposure_period_start", "exposure_period_end",
                "currency", "exposure_value",
            ],
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

    def test_blank_exposure_value_raises_value_error(self):
        from pyre.io_excel.exposures_io import read_exposures

        self._write_exposures_sheet(
            [["EXP2022", "2022 Premium", date(2022, 1, 1), date(2022, 12, 31), "USD", None]]
        )

        with self.assertRaises(ValueError):
            read_exposures(self.path)

    def test_blank_exposure_name_raises_value_error_instead_of_string_none(self):
        from pyre.io_excel.exposures_io import read_exposures

        self._write_exposures_sheet(
            [["EXP2022", None, date(2022, 1, 1), date(2022, 12, 31), "USD", 1000000]]
        )

        with self.assertRaises(ValueError):
            read_exposures(self.path)


@unittest.skipUnless(HAS_OPENPYXL, "openpyxl not installed; pip install -e '.[excel]'")
class TestWriteTriangle(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "triangle.xlsx"

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_writes_grid_with_blank_cells_for_missing_combinations(self):
        from pyre.claims.triangles import Triangle
        from pyre.io_excel.triangle_io import write_triangle

        triangle = Triangle(
            triangle={
                2020: {1: 100.0, 2: 150.0, 3: 175.0},
                2021: {1: 110.0, 2: 165.0},
                2022: {1: 120.0},
            },
            origin_years=[2020, 2021, 2022],
            dev_periods=[1, 2, 3],
        )

        write_triangle(triangle, self.path)

        wb = openpyxl.load_workbook(self.path)
        ws = wb["Triangle"]
        rows = [list(row) for row in ws.iter_rows(values_only=True)]

        self.assertEqual(rows[0], ["origin_year", "1", "2", "3"])
        self.assertEqual(rows[1], [2020, 100.0, 150.0, 175.0])
        self.assertEqual(rows[2], [2021, 110.0, 165.0, None])
        self.assertEqual(rows[3], [2022, 120.0, None, None])


@unittest.skipUnless(HAS_OPENPYXL, "openpyxl not installed; pip install -e '.[excel]'")
class TestWriteExperienceRatingResults(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "experience.xlsx"

        claim = Claim(
            ClaimsMetaData(
                claim_id="CLM001",
                currency="USD",
                contract_limit=2_000_000.0,
                loss_date=date(2022, 3, 1),
            ),
            ClaimDevelopmentHistory(
                development_months=[12, 24],
                cumulative_dev_paid=[50000.0, 90000.0],
                cumulative_dev_incurred=[120000.0, 250000.0],
            ),
        )
        claims = Claims([claim])

        exposure = Exposure(
            ExposureMetaData(
                exposure_id="EXP2022",
                exposure_name="2022 Premium",
                exposure_period_start=date(2022, 1, 1),
                exposure_period_end=date(2022, 12, 31),
                currency="USD",
            ),
            ExposureValues(exposure_value=1_000_000.0, attachment_point=0.0, limit=1_000_000.0),
        )
        exposures = Exposures([exposure])

        metadata = RIContractMetadata(
            contract_id="C-0001",
            contract_description="Test",
            cedent_name="Acme Re",
            trigger_basis=ClaimTriggerBasis.LOD,
            indexation_clause=IndexationClauseType.FULL_INDEXATION,
            indexation_margin=0.0,
            inception_date=date(2022, 1, 1),
            expiration_date=date(2022, 12, 31),
            fx_rates={"USD": 1.0},
        )
        layer = RILayer(
            layer_id=1,
            layer_name="XOL Layer",
            layer_type=ContractType.EXCESS_OF_LOSS,
            occurrence_attachment=100_000.0,
            occurrence_limit=200_000.0,
            aggregate_attachment=0.0,
            aggregate_limit=0.0,
            subject_lines_of_business=[],
            subject_lob_exposure_amounts=[],
            full_subject_premium=0.0,
            written_line=1.0,
            signed_line=1.0,
            number_of_reinstatements=0,
            reinstatement_cost={},
        )
        contract = RIContract(contract_meta_data=metadata, layers=[layer])

        self.model_data = ExperienceModelData(
            claims=claims, exposures=exposures, ri_contract=contract
        )

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_writes_both_sheets(self):
        from pyre.io_excel.results_io import write_experience_rating_results

        write_experience_rating_results(self.model_data, self.path)

        wb = openpyxl.load_workbook(self.path)
        self.assertEqual(set(wb.sheetnames), {"ByLayerYear", "ExposuresByYear"})

        by_layer_year = [list(row) for row in wb["ByLayerYear"].iter_rows(values_only=True)]
        self.assertEqual(
            by_layer_year[0],
            [
                "layer_id", "layer_name", "modelling_year", "ceded_paid",
                "ceded_incurred", "claim_count", "earned_premium", "loss_ratio",
            ],
        )
        self.assertEqual(by_layer_year[1][:7], [1, "XOL Layer", 2022, 0.0, 150000.0, 1, 1000000.0])
        self.assertAlmostEqual(by_layer_year[1][7], 0.15)

        exposures_by_year = [list(row) for row in wb["ExposuresByYear"].iter_rows(values_only=True)]
        self.assertEqual(exposures_by_year[0], ["modelling_year", "written", "earned"])
        self.assertEqual(exposures_by_year[1][0], 2022)

    def test_no_claims_still_writes_a_valid_header_only_sheet(self):
        from pyre.claims.claims import Claims
        from pyre.io_excel.results_io import write_experience_rating_results

        self.model_data.claims = Claims([])

        write_experience_rating_results(self.model_data, self.path)  # must not raise

        wb = openpyxl.load_workbook(self.path)
        by_layer_year = [list(row) for row in wb["ByLayerYear"].iter_rows(values_only=True)]
        self.assertEqual(
            by_layer_year,
            [[
                "layer_id", "layer_name", "modelling_year", "ceded_paid",
                "ceded_incurred", "claim_count", "earned_premium", "loss_ratio",
            ]],
        )

    def test_rerunning_overwrites_rather_than_duplicating_rows(self):
        from pyre.io_excel.results_io import write_experience_rating_results

        write_experience_rating_results(self.model_data, self.path)
        write_experience_rating_results(self.model_data, self.path)  # re-run

        wb = openpyxl.load_workbook(self.path)
        self.assertEqual(wb.sheetnames.count("ByLayerYear"), 1)
        by_layer_year_rows = list(wb["ByLayerYear"].iter_rows(values_only=True))
        self.assertEqual(len(by_layer_year_rows), 2)  # header + 1 data row, not 1 + 2


@unittest.skipUnless(HAS_OPENPYXL, "openpyxl not installed; pip install -e '.[excel]'")
class TestWriteExposureRatingResults(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "exposure.xlsx"

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_writes_one_row_per_exposure_layer_pair(self):
        from pyre.io_excel.results_io import write_exposure_rating_results
        from pyre.models.Exposure.exposure_curve_functions import ExposureCurveType
        from pyre.models.Exposure.exposure_rating_cost import ExposureModel

        exposure = Exposure(
            ExposureMetaData(
                exposure_id="EXP001",
                exposure_name="EXP001",
                exposure_period_start=date(2023, 1, 1),
                exposure_period_end=date(2023, 12, 31),
                currency="USD",
            ),
            ExposureValues(exposure_value=1_000_000.0, attachment_point=0.0, limit=1_000_000.0),
        )
        layer = RILayer(
            layer_id=1,
            layer_name="Layer 1",
            layer_type=ContractType.EXCESS_OF_LOSS,
            occurrence_attachment=100_000.0,
            occurrence_limit=400_000.0,
            aggregate_attachment=0.0,
            aggregate_limit=0.0,
            subject_lines_of_business=[],
            subject_lob_exposure_amounts=[],
            full_subject_premium=0.0,
            written_line=1.0,
            signed_line=1.0,
            number_of_reinstatements=0,
            reinstatement_cost={},
        )
        metadata = RIContractMetadata(
            contract_id="C-0001",
            contract_description="Test",
            cedent_name="Acme Re",
            trigger_basis=ClaimTriggerBasis.LOD,
            indexation_clause=IndexationClauseType.FULL_INDEXATION,
            indexation_margin=0.0,
            inception_date=date(2023, 1, 1),
            expiration_date=date(2023, 12, 31),
            fx_rates={"USD": 1.0},
        )
        contract = RIContract(contract_meta_data=metadata, layers=[layer])
        model = ExposureModel(
            exposures=Exposures([exposure]),
            ri_contract=contract,
            selected_curve=ExposureCurveType.MBBEFD,
            curve_parameters={"curve": 3.0},
        )

        write_exposure_rating_results(model, self.path)

        wb = openpyxl.load_workbook(self.path)
        rows = [list(row) for row in wb["ExposureShares"].iter_rows(values_only=True)]
        self.assertEqual(rows[0], ["exposure_id", "layer_id", "share"])
        self.assertEqual(rows[1][0], "EXP001")
        self.assertEqual(rows[1][1], 1)


@unittest.skipUnless(HAS_OPENPYXL, "openpyxl not installed; pip install -e '.[excel]'")
class TestPublicApiSurface(unittest.TestCase):
    def test_all_five_functions_importable_from_io_excel_package(self):
        from pyre.io_excel import (
            read_claims,
            read_exposures,
            write_experience_rating_results,
            write_exposure_rating_results,
            write_triangle,
        )

        self.assertTrue(callable(read_claims))
        self.assertTrue(callable(read_exposures))
        self.assertTrue(callable(write_triangle))
        self.assertTrue(callable(write_experience_rating_results))
        self.assertTrue(callable(write_exposure_rating_results))

    def test_bare_import_pyre_does_not_require_openpyxl(self):
        # Confirms pyre/__init__.py never imports io_excel transitively.
        # (openpyxl IS installed in this test env, so this only checks that
        # `pyre.io_excel` is absent from sys.modules after a bare `import pyre`
        # -- it does not prove openpyxl is uninstallable-safe, just that the
        # import graph doesn't pull it in.)
        import sys

        for name in list(sys.modules):
            if name == "pyre" or name.startswith("pyre."):
                del sys.modules[name]

        import pyre  # noqa: F401

        self.assertNotIn("pyre.io_excel", sys.modules)


if __name__ == "__main__":
    unittest.main()
