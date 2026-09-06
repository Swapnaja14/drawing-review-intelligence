"""
Test OCR-based comment extraction on engineering drawings.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.ocr_comment_extractor import OCRCommentExtractor


def test_ocr_extraction():
    """Test OCR comment extraction on a sample PDF."""
    
    test_pdf = PROJECT_ROOT / "dataset" / "raw_drawings" / "Electrical Engineering" / "5-1307-137_F_RJY.pdf"
    
    if not test_pdf.exists():
        print(f"❌ Test PDF not found: {test_pdf}")
        return
    
    print("=" * 80)
    print("OCR COMMENT EXTRACTION TEST")
    print("=" * 80)
    print(f"PDF: {test_pdf.name}")
    print()
    
    # Initialize extractor
    extractor = OCRCommentExtractor()
    
    # Test on page 1 (index 0)
    print("Extracting comments from Page 1...")
    print()
    
    try:
        results = extractor.extract_comments_from_pdf(test_pdf, page_number=0, dpi=200)
        
        print(f"Found {len(results)} comment blocks")
        print()
        
        if results:
            print("Top 10 Comments:")
            print("-" * 80)
            
            # Sort by comment score (highest first)
            sorted_results = sorted(results, key=lambda r: r.comment_score, reverse=True)
            
            for i, result in enumerate(sorted_results[:10], 1):
                print(f"\n{i}. Text: \"{result.text}\"")
                print(f"   Score: {result.comment_score:.2f}, Confidence: {result.confidence:.2f}")
                print(f"   BBox: ({result.bbox[0]:.1f}, {result.bbox[1]:.1f}) → ({result.bbox[2]:.1f}, {result.bbox[3]:.1f})")
        else:
            print("⚠️  No comments extracted")
            print()
            print("Possible reasons:")
            print("- Tesseract not installed or not in PATH")
            print("- PDF has no text (pure image)")
            print("- Comment filtering too strict")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print()
        print("Common issues:")
        print("1. Tesseract not installed:")
        print("   Windows: choco install tesseract")
        print("   Mac: brew install tesseract")
        print("   Linux: apt-get install tesseract-ocr")
        print()
        print("2. Tesseract not in PATH:")
        print("   Add to system PATH or specify path in OCRCommentExtractor(tesseract_path=...)")


if __name__ == "__main__":
    test_ocr_extraction()
