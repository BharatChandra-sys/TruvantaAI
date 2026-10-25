# Ownership notice: Bodapati Bharat chandra
"""
Test SHAP Explainability Implementation

Tests the SHAP-based highlighting and explanation features.
"""

import pytest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_shap_explainer_import():
    """Test that SHAP explainer can be imported"""
    try:
        from app.analysis.shap_explainer import SHAPExplainer, explain_prediction
        assert SHAPExplainer is not None
        assert explain_prediction is not None
    except ImportError as e:
        pytest.skip(f"SHAP not installed: {e}")


def test_highlight_with_shap():
    """Test SHAP-based highlighting"""
    try:
        from app.analysis.highlight import get_highlights_with_shap
        import joblib
        
        # Load model
        model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "model.joblib")
        vec_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "vectorizer.joblib")
        
        if not (os.path.exists(model_path) and os.path.exists(vec_path)):
            pytest.skip("Model files not found")
        
        model = joblib.load(model_path)
        vectorizer = joblib.load(vec_path)
        
        # Test claim
        text = "BREAKING: Scientists discover shocking truth about vaccines that they don't want you to know!"
        
        highlights, explanation_type = get_highlights_with_shap(
            text, model, vectorizer, model_type="tfidf", timeout_ms=1000
        )
        
        assert highlights is not None
        assert len(highlights) > 0
        assert explanation_type in ["shap", "heuristic"]
        
        # Check highlight structure
        for h in highlights:
            assert "phrase" in h
            assert "score" in h or "importance" in h
            assert "reason" in h or "direction" in h
        
        print(f"✓ Generated {len(highlights)} highlights using {explanation_type}")
        
    except ImportError as e:
        pytest.skip(f"Required libraries not installed: {e}")


def test_shap_highlight_structure():
    """Test SHAP highlight data structure"""
    from app.analysis.highlight import generate_shap_highlights
    
    # Mock SHAP values
    mock_shap_values = {
        "token_importances": [
            {"token": "shocking", "importance": 0.45, "position": 0, "direction": "fake", "confidence": 0.85},
            {"token": "truth", "importance": -0.25, "position": 1, "direction": "real", "confidence": 0.65},
            {"token": "vaccines", "importance": 0.15, "position": 2, "direction": "fake", "confidence": 0.55},
        ]
    }
    
    text = "shocking truth about vaccines"
    highlights = generate_shap_highlights(text, mock_shap_values, threshold=0.1)
    
    assert len(highlights) > 0
    
    for h in highlights:
        assert "phrase" in h
        assert "importance" in h
        assert "direction" in h
        assert "position" in h
        assert "confidence" in h
        assert "explanation" in h
        assert h["direction"] in ["fake", "real"]
    
    print(f"✓ SHAP highlight structure validated")


def test_fallback_to_heuristic():
    """Test fallback to heuristic highlighting when SHAP fails"""
    from app.analysis.highlight import get_highlights
    
    text = "BREAKING: Shocking news that will blow your mind!"
    highlights = get_highlights(text)
    
    assert highlights is not None
    assert len(highlights) > 0
    
    for h in highlights:
        assert "phrase" in h
        assert "score" in h
        assert "reason" in h
    
    print(f"✓ Heuristic fallback works: {len(highlights)} highlights")


def test_attention_extractor_import():
    """Test that attention extractor can be imported"""
    try:
        from app.analysis.attention_extractor import AttentionExtractor
        assert AttentionExtractor is not None
    except ImportError as e:
        pytest.skip(f"Transformers not installed: {e}")


if __name__ == "__main__":
    print("Running SHAP Explainability Tests...\n")
    
    # Run tests
    test_shap_explainer_import()
    test_highlight_with_shap()
    test_shap_highlight_structure()
    test_fallback_to_heuristic()
    test_attention_extractor_import()
    
    print("\n✅ All SHAP tests passed!")
