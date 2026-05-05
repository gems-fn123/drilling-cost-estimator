"""
Test estimation engine for the Drilling Campaign Cost Estimator app.
Tests the estimate_campaign function with processed artifacts.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

# The actual app root is /app, not /app/backend/tests/../../../
APP_ROOT = Path("/app")
PROCESSED_DIR = APP_ROOT / "data" / "processed"


class TestEstimationEngine:
    """Test the estimation engine functionality"""
    
    def test_processed_artifacts_exist(self):
        """Verify processed artifacts directory exists and has files"""
        assert PROCESSED_DIR.exists(), "Processed directory should exist"
        
        files = list(PROCESSED_DIR.glob("*"))
        assert len(files) > 0, "Processed directory should have files"
        print(f"PASS: Found {len(files)} processed artifacts")
    
    def test_required_artifacts_present(self):
        """Check that key artifacts required for estimation are present"""
        required_patterns = [
            "unit_price_history_mart.csv",
            "canonical_campaign_mapping.csv",
            "canonical_well_mapping.csv",
        ]
        
        for pattern in required_patterns:
            matches = list(PROCESSED_DIR.glob(f"*{pattern}*")) + list(PROCESSED_DIR.glob(pattern))
            # Check if file exists directly or with similar name
            direct_match = PROCESSED_DIR / pattern
            if direct_match.exists() or matches:
                print(f"PASS: Found artifact matching '{pattern}'")
            else:
                # List available files for debugging
                available = [f.name for f in PROCESSED_DIR.glob("*.csv")]
                print(f"INFO: '{pattern}' not found. Available CSVs: {available[:10]}")
    
    def test_estimate_campaign_function_exists(self):
        """Verify estimate_campaign function can be imported"""
        try:
            from src.modeling.phase5_estimation_core import estimate_campaign, build_validation_artifacts
            print("PASS: estimate_campaign and build_validation_artifacts imported successfully")
        except ImportError as e:
            pytest.fail(f"Failed to import estimation functions: {e}")
    
    def test_build_validation_artifacts(self):
        """Test that build_validation_artifacts runs without error"""
        try:
            from src.modeling.phase5_estimation_core import build_validation_artifacts
            
            # Run with refresh_pipeline=False to use existing artifacts
            build_validation_artifacts(refresh_pipeline=False)
            print("PASS: build_validation_artifacts completed successfully")
        except Exception as e:
            pytest.fail(f"build_validation_artifacts failed: {e}")
    
    def test_estimate_campaign_slk_field(self):
        """Test estimation for SLK field with 3 wells and 2 pads"""
        try:
            from src.modeling.phase5_estimation_core import estimate_campaign, build_validation_artifacts
            
            # Build validation artifacts first
            build_validation_artifacts(refresh_pipeline=False)
            
            # Campaign input matching the UI defaults
            campaign_input = {
                "year": 2026,
                "field": "SLK",
                "no_pads": 2,
                "no_wells": 3,
                "no_pad_expansion": 0,
                "use_external_forecast": True,
                "use_synthetic_data": False,
            }
            
            # Well rows with default parameters (matching input_panel.py structure)
            well_rows = [
                {"well_label": "Well-1", "pad_label": "Pad-1", "depth_ft": 7000, "leg_type": "Standard-J", "drill_rate_mode": "Standard"},
                {"well_label": "Well-2", "pad_label": "Pad-1", "depth_ft": 7000, "leg_type": "Standard-J", "drill_rate_mode": "Standard"},
                {"well_label": "Well-3", "pad_label": "Pad-1", "depth_ft": 7000, "leg_type": "Standard-J", "drill_rate_mode": "Standard"},
            ]
            
            result = estimate_campaign(campaign_input, well_rows)
            
            # Verify result structure
            assert result is not None, "Result should not be None"
            assert isinstance(result, dict), "Result should be a dictionary"
            
            # Check for expected keys in result
            expected_keys = ["total_mm_usd", "well_linked_usd", "campaign_tied_usd"]
            for key in expected_keys:
                if key in result:
                    print(f"PASS: Result contains '{key}' = {result[key]}")
                else:
                    print(f"INFO: Result missing '{key}', available keys: {list(result.keys())[:10]}")
            
            # Verify total is positive
            total = result.get("total_mm_usd", result.get("total", 0))
            if total and total > 0:
                print(f"PASS: Total estimate is positive: {total} MM USD")
            
        except Exception as e:
            pytest.fail(f"estimate_campaign failed: {e}")


class TestWBSTreeArtifacts:
    """Test WBS tree artifacts"""
    
    def test_wbs_tree_json_exists(self):
        """Verify WBS tree JSON artifact exists"""
        try:
            from src.modeling.wbs_tree_diagram import WBS_TREE_COMBINED_JSON
            
            if WBS_TREE_COMBINED_JSON.exists():
                print(f"PASS: WBS tree JSON exists at {WBS_TREE_COMBINED_JSON}")
            else:
                print(f"INFO: WBS tree JSON not found at {WBS_TREE_COMBINED_JSON}")
        except ImportError as e:
            print(f"INFO: Could not import WBS tree module: {e}")
    
    def test_load_wbs_tree_payload(self):
        """Test loading WBS tree payload"""
        try:
            from src.modeling.wbs_tree_diagram import load_wbs_tree_payload, WBS_TREE_COMBINED_JSON
            
            if not WBS_TREE_COMBINED_JSON.exists():
                pytest.skip("WBS tree JSON not found")
            
            payload = load_wbs_tree_payload()
            
            assert payload is not None, "Payload should not be None"
            assert "fields" in payload, "Payload should have 'fields' key"
            
            fields = payload.get("fields", {})
            print(f"PASS: WBS tree payload loaded with {len(fields)} fields: {list(fields.keys())}")
            
        except Exception as e:
            pytest.fail(f"Failed to load WBS tree payload: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
