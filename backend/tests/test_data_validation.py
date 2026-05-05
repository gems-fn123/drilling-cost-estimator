"""
Test data validation logic for the Drilling Campaign Cost Estimator app.
Tests the data contract validation for uploaded files.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.app.components.data_validation import (
    validate_excel_file,
    validate_csv_file,
    FileValidationResult,
    SheetValidationResult,
    DASHBOARD_WORKBOOK_CONTRACT,
    PRIMARY_WORKBOOK_CONTRACT,
    MINIMUM_VIABLE_CONTRACTS,
)


class TestDataValidationContracts:
    """Test data contract definitions"""
    
    def test_dashboard_contract_has_required_sheets(self):
        """Dashboard workbook contract should have Structured.Cost and General.Camp.Data"""
        sheet_names = [s[0] for s in DASHBOARD_WORKBOOK_CONTRACT]
        assert "Structured.Cost" in sheet_names
        assert "General.Camp.Data" in sheet_names
        print("PASS: Dashboard contract has required sheets")
    
    def test_minimum_viable_contracts_defined(self):
        """Minimum viable contracts should be defined for dashboard and primary"""
        assert "dashboard" in MINIMUM_VIABLE_CONTRACTS
        assert "primary" in MINIMUM_VIABLE_CONTRACTS
        assert "required_sheets" in MINIMUM_VIABLE_CONTRACTS["dashboard"]
        assert "required_sheets" in MINIMUM_VIABLE_CONTRACTS["primary"]
        print("PASS: Minimum viable contracts are properly defined")
    
    def test_dashboard_minimum_sheets(self):
        """Dashboard minimum should require Structured.Cost and General.Camp.Data"""
        min_sheets = MINIMUM_VIABLE_CONTRACTS["dashboard"]["required_sheets"]
        assert "Structured.Cost" in min_sheets
        assert "General.Camp.Data" in min_sheets
        print("PASS: Dashboard minimum sheets are correct")


class TestExcelValidation:
    """Test Excel file validation logic"""
    
    def test_validate_dashboard_workbook_with_valid_sheets(self):
        """Test validation of a valid dashboard workbook"""
        # Simulate sheets data with required headers
        sheets_data = {
            "Structured.Cost": [
                ["Asset", "Campaign", "Level 2", "Level 3", "Level 4", "Level 5", "Well", "Actual Cost USD"],
                ["DARAJAT", "DRJ-2024", "Drilling", "Well Cost", "Materials", "Casing", "DRJ-01", "100000"],
            ],
            "General.Camp.Data": [
                ["Asset", "Campaign", "WBS CODE", "Well Name Actual", "Well Name SAP", "Well Name Alt 1", "Well Name Alt 2"],
                ["DARAJAT", "DRJ-2024", "WBS001", "DRJ-01", "DRJ-01-SAP", "DRJ-01-A1", "DRJ-01-A2"],
            ],
        }
        
        result = validate_excel_file(Path("/tmp/test.xlsx"), sheets_data)
        
        assert result.readable is True
        assert result.detected_type == "dashboard"
        assert result.pipeline_ready is True
        print(f"PASS: Dashboard workbook validation - detected_type={result.detected_type}, pipeline_ready={result.pipeline_ready}")
    
    def test_validate_workbook_with_missing_sheets(self):
        """Test validation of workbook with missing required sheets"""
        # Only one sheet, missing General.Camp.Data
        sheets_data = {
            "Structured.Cost": [
                ["Asset", "Campaign", "Level 2", "Level 3", "Level 4", "Level 5", "Well", "Actual Cost USD"],
                ["DARAJAT", "DRJ-2024", "Drilling", "Well Cost", "Materials", "Casing", "DRJ-01", "100000"],
            ],
        }
        
        result = validate_excel_file(Path("/tmp/test.xlsx"), sheets_data)
        
        # Should not be pipeline ready without both required sheets
        assert result.pipeline_ready is False or result.detected_type != "dashboard"
        print(f"PASS: Missing sheets validation - detected_type={result.detected_type}, pipeline_ready={result.pipeline_ready}")
    
    def test_validate_workbook_with_missing_headers(self):
        """Test validation of workbook with missing required headers"""
        # Sheet exists but missing required headers
        sheets_data = {
            "Structured.Cost": [
                ["Asset", "Campaign", "Level 2"],  # Missing Level 3, Level 4, Level 5, Well, Actual Cost USD
                ["DARAJAT", "DRJ-2024", "Drilling"],
            ],
            "General.Camp.Data": [
                ["Asset", "Campaign"],  # Missing WBS CODE, Well Name columns
                ["DARAJAT", "DRJ-2024"],
            ],
        }
        
        result = validate_excel_file(Path("/tmp/test.xlsx"), sheets_data)
        
        # Should have sheet results with missing headers
        assert len(result.sheet_results) > 0
        # Check that missing headers are detected
        has_missing = any(len(sr.missing_headers) > 0 for sr in result.sheet_results)
        assert has_missing is True
        print(f"PASS: Missing headers validation - found missing headers in {sum(1 for sr in result.sheet_results if sr.missing_headers)} sheets")
    
    def test_validate_unknown_workbook(self):
        """Test validation of workbook that doesn't match any contract"""
        # Random sheets that don't match any contract
        sheets_data = {
            "RandomSheet1": [
                ["Column1", "Column2", "Column3"],
                ["Value1", "Value2", "Value3"],
            ],
            "RandomSheet2": [
                ["A", "B", "C"],
                ["1", "2", "3"],
            ],
        }
        
        result = validate_excel_file(Path("/tmp/test.xlsx"), sheets_data)
        
        assert result.detected_type == "unknown"
        assert result.pipeline_ready is False
        assert len(result.warnings) > 0
        print(f"PASS: Unknown workbook validation - detected_type={result.detected_type}, warnings={len(result.warnings)}")


class TestCSVValidation:
    """Test CSV file validation logic"""
    
    def test_validate_csv_with_content(self, tmp_path):
        """Test validation of a valid CSV file"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Column1,Column2,Column3\nValue1,Value2,Value3\nValue4,Value5,Value6")
        
        result = validate_csv_file(csv_file)
        
        assert result.readable is True
        assert result.pipeline_ready is True
        assert result.detected_type == "csv_supplement"
        assert len(result.sheet_results) == 1
        assert result.sheet_results[0].row_count == 2  # 2 data rows
        print(f"PASS: CSV validation - readable={result.readable}, row_count={result.sheet_results[0].row_count}")
    
    def test_validate_empty_csv(self, tmp_path):
        """Test validation of an empty CSV file"""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")
        
        result = validate_csv_file(csv_file)
        
        assert result.readable is False
        assert "empty" in result.error_message.lower()
        print(f"PASS: Empty CSV validation - error_message={result.error_message}")


class TestFileValidationResult:
    """Test FileValidationResult dataclass"""
    
    def test_valid_sheet_count(self):
        """Test valid_sheet_count property"""
        result = FileValidationResult(
            file_name="test.xlsx",
            file_path=Path("/tmp/test.xlsx"),
            readable=True,
            sheet_results=[
                SheetValidationResult(
                    sheet_name="Sheet1",
                    found=True,
                    required_headers=["A", "B"],
                    found_headers=["A", "B"],
                    missing_headers=[],
                ),
                SheetValidationResult(
                    sheet_name="Sheet2",
                    found=True,
                    required_headers=["C", "D"],
                    found_headers=["C"],
                    missing_headers=["D"],
                ),
            ],
        )
        
        assert result.valid_sheet_count == 1  # Only Sheet1 is valid
        assert result.total_sheets_checked == 2
        print(f"PASS: valid_sheet_count={result.valid_sheet_count}, total_sheets_checked={result.total_sheets_checked}")


class TestSheetValidationResult:
    """Test SheetValidationResult dataclass"""
    
    def test_headers_valid_property(self):
        """Test headers_valid property"""
        # Valid sheet
        valid_sheet = SheetValidationResult(
            sheet_name="ValidSheet",
            found=True,
            required_headers=["A", "B"],
            found_headers=["A", "B"],
            missing_headers=[],
        )
        assert valid_sheet.headers_valid is True
        
        # Invalid sheet - missing headers
        invalid_sheet = SheetValidationResult(
            sheet_name="InvalidSheet",
            found=True,
            required_headers=["A", "B"],
            found_headers=["A"],
            missing_headers=["B"],
        )
        assert invalid_sheet.headers_valid is False
        
        # Invalid sheet - not found
        not_found_sheet = SheetValidationResult(
            sheet_name="NotFoundSheet",
            found=False,
            required_headers=["A", "B"],
            missing_headers=["A", "B"],
        )
        assert not_found_sheet.headers_valid is False
        
        print("PASS: headers_valid property works correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
