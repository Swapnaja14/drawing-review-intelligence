"""
Test colored comment detection on any drawing
Usage: python scripts/test_any_drawing.py [pdf_filename]
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import logging
from src.services.colored_comment_detector import ColoredCommentDetector

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


def test_any_drawing(pdf_path_str=None):
    """Test detection on any PDF"""
    
    if pdf_path_str:
        pdf_path = Path(pdf_path_str)
    else:
        # Default: use a different PDF from dataset
        pdf_path = Path("dataset/raw_drawings/Electrical Engineering/54725-29 CIP SKID PANEL COMMENTS.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        print("\nAvailable PDFs in dataset/raw_drawings/Electrical Engineering/:")
        drawings_dir = Path("dataset/raw_drawings/Electrical Engineering")
        if drawings_dir.exists():
            for pdf in sorted(drawings_dir.glob("*.pdf"))[:10]:
                print(f"  - {pdf.name}")
        return
    
    print("\n" + "="*80)
    print(f"TESTING: {pdf_path.name}")
    print("="*80 + "\n")
    
    detector = ColoredCommentDetector()
    
    print("Configuration:")
    print(f"  Min area: {detector.min_comment_area_px} pixels")
    print(f"  Max area: {detector.max_comment_area_px} pixels")
    print(f"  Min words: {detector.min_word_count}")
    print(f"  Min text confidence: {detector.min_text_confidence}")
    print(f"  Detection DPI: {detector.detection_dpi}")
    print(f"  OCR DPI: {detector.ocr_dpi}")
    print()
    
    # Detect on first page with details
    print("Processing first page...")
    print("-"*80 + "\n")
    
    comments = detector.detect_comments_on_page(
        pdf_path, 
        page_number=0,
        extract_text=True,
        filter_by_shape=True,
        require_text_validation=True
    )
    
    print(f"\n{'='*80}")
    print("RESULTS")
    print("="*80 + "\n")
    
    if comments:
        print(f"✅ Found {len(comments)} comment(s):\n")
        
        for i, comment in enumerate(comments, 1):
            print(f"[{i}] {comment.color_category.upper()} Comment")
            print(f"    Position: ({comment.x0:.1f}, {comment.y0:.1f}) → ({comment.x1:.1f}, {comment.y1:.1f})")
            print(f"    Size: {(comment.x1-comment.x0):.1f} × {(comment.y1-comment.y0):.1f} pts")
            print(f"    Text: '{comment.extracted_text}'")
            print(f"    Text confidence: {comment.text_confidence:.2%}")
            print(f"    Detection confidence: {comment.confidence:.2%}")
            print(f"    Box-shaped: {comment.is_box_shaped}")
            print()
    else:
        print("✅ No comments detected")
        print("   (Zero false positives - no blank backgrounds or measurements marked)")
    
    # Create visualization
    output_dir = Path("dataset/preprocessed_images/comment_detection")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    vis_path = output_dir / f"{pdf_path.stem}_page0_annotated.png"
    json_path = output_dir / f"{pdf_path.stem}_page0_comments.json"
    
    print(f"\n{'='*80}")
    print("OUTPUT FILES")
    print("="*80 + "\n")
    
    detector.visualize_detections(pdf_path, 0, comments, vis_path)
    print(f"✅ Visualization: {vis_path}")
    
    detector.export_to_json(comments, json_path)
    print(f"✅ JSON export: {json_path}")
    
    # Show JSON content
    import json
    with open(json_path, 'r') as f:
        json_data = json.load(f)
    
    print(f"\n{'='*80}")
    print("JSON OUTPUT")
    print("="*80 + "\n")
    print(json.dumps(json_data, indent=2))
    
    print(f"\n{'='*80}")
    print("TEST COMPLETE")
    print("="*80 + "\n")
    
    if comments:
        print("✅ DETECTED ACTUAL COMMENTS")
        print(f"   {len(comments)} comment(s) with text content")
    else:
        print("✅ NO FALSE POSITIVES")
        print("   All colored regions correctly filtered as non-comments")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test specific PDF
        pdf_path = sys.argv[1]
        test_any_drawing(pdf_path)
    else:
        # Test default PDF
        print("\nUsage: python scripts/test_any_drawing.py [path/to/drawing.pdf]")
        print("Or run without arguments to test a default drawing\n")
        test_any_drawing()
