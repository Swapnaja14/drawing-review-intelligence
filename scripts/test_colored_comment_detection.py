"""
Test script for colored comment detection
Demonstrates detection of red, yellow, blue, green, and other colored comment boxes
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import cv2
import logging
from src.services.colored_comment_detector import ColoredCommentDetector

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)


def print_header(title):
    """Print formatted header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def test_single_page_detection():
    """Test colored comment detection on a single page"""
    print_header("TEST 1: Single Page Colored Comment Detection")
    
    # Initialize detector
    detector = ColoredCommentDetector(detection_dpi=200, ocr_dpi=300)
    
    # Test PDF path
    pdf_path = Path("dataset/raw_drawings/Electrical Engineering/5-1307-137_F_RJY.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        print("Please provide a valid PDF path with colored comments")
        return
    
    print(f"Processing: {pdf_path.name}")
    print(f"Page: 0 (first page)")
    print()
    
    # Detect comments with text extraction
    comments = detector.detect_comments_on_page(
        pdf_path=pdf_path,
        page_number=0,
        extract_text=True,
        filter_by_shape=True,
        require_text_validation=True  # IMPORTANT: Only keep regions with actual text
    )
    
    print(f"\n✅ Detected {len(comments)} colored comment boxes\n")
    
    # Group by color
    by_color = {}
    for comment in comments:
        color = comment.color_category
        if color not in by_color:
            by_color[color] = []
        by_color[color].append(comment)
    
    # Print summary by color
    print("Comments by color:")
    for color, color_comments in sorted(by_color.items()):
        print(f"  {color.upper()}: {len(color_comments)} comments")
    
    print("\nDetailed results:")
    print("-" * 80)
    
    for i, comment in enumerate(comments, 1):
        print(f"\n[{i}] {comment.color_category.upper()} Comment")
        print(f"    Position: ({comment.x0:.1f}, {comment.y0:.1f}) → ({comment.x1:.1f}, {comment.y1:.1f})")
        print(f"    Size: {(comment.x1 - comment.x0):.1f} × {(comment.y1 - comment.y0):.1f} pts")
        print(f"    Box-shaped: {'Yes' if comment.is_box_shaped else 'No'}")
        print(f"    Detection confidence: {comment.confidence:.2%}")
        
        if comment.extracted_text:
            print(f"    Text: '{comment.extracted_text}'")
            print(f"    Text confidence: {comment.text_confidence:.2%}")
        else:
            print(f"    Text: (none detected)")
    
    # Save visualization
    output_dir = Path("dataset/preprocessed_images/comment_detection")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    vis_path = output_dir / f"{pdf_path.stem}_page0_annotated.png"
    print(f"\nCreating visualization...")
    detector.visualize_detections(pdf_path, 0, comments, vis_path)
    print(f"✅ Visualization saved to: {vis_path}")
    
    # Export to JSON
    json_path = output_dir / f"{pdf_path.stem}_page0_comments.json"
    detector.export_to_json(comments, json_path)
    print(f"✅ Comments exported to: {json_path}")


def test_multi_page_detection():
    """Test colored comment detection across all pages"""
    print_header("TEST 2: Multi-Page Colored Comment Detection")
    
    detector = ColoredCommentDetector(detection_dpi=200, ocr_dpi=300)
    
    pdf_path = Path("dataset/raw_drawings/Electrical Engineering/5-1307-137_F_RJY.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"Processing: {pdf_path.name}")
    print("Detecting comments on all pages...")
    print()
    
    # Progress callback
    def progress(page_num, total_pages):
        print(f"  Processed page {page_num}/{total_pages}")
    
    # Detect all pages
    result = detector.detect_all_pages(
        pdf_path=pdf_path,
        extract_text=True,
        filter_by_shape=True,
        require_text_validation=True,  # Filter blank backgrounds
        progress_callback=progress
    )
    
    print(f"\n✅ Processing complete")
    print(f"   Total pages: {result.total_pages}")
    print(f"   Total comments: {result.total_regions}")
    
    # Summary by page
    print("\nComments per page:")
    for page_result in result.page_results:
        if page_result.regions:
            colors = {}
            for region in page_result.regions:
                color = region.color_category
                colors[color] = colors.get(color, 0) + 1
            
            color_summary = ", ".join([f"{count} {color}" for color, count in sorted(colors.items())])
            print(f"  Page {page_result.page_number}: {len(page_result.regions)} comments ({color_summary})")
        else:
            print(f"  Page {page_result.page_number}: No comments")
    
    # Save visualizations for pages with comments
    output_dir = Path("dataset/preprocessed_images/comment_detection")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\nCreating visualizations...")
    for page_result in result.page_results:
        if page_result.regions:
            vis_path = output_dir / f"{pdf_path.stem}_page{page_result.page_number}_annotated.png"
            detector.visualize_detections(
                pdf_path, page_result.page_number, page_result.regions, vis_path
            )
            print(f"  ✅ Page {page_result.page_number}: {vis_path.name}")


def test_different_colors():
    """Test detection of different color categories"""
    print_header("TEST 3: Different Color Category Detection")
    
    detector = ColoredCommentDetector(detection_dpi=200, ocr_dpi=300)
    
    print("Supported color categories:")
    print("  • RED: Typically used for critical comments/corrections")
    print("  • YELLOW: Highlighted areas and notes")
    print("  • BLUE: Information boxes")
    print("  • GREEN: Approval marks and confirmations")
    print("  • CYAN: Additional annotations")
    print("  • MAGENTA: Special markings")
    print("  • ORANGE: Warning or attention markers")
    print()
    
    pdf_path = Path("dataset/raw_drawings/Electrical Engineering/5-1307-137_F_RJY.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"Testing on: {pdf_path.name}")
    
    # Detect all colors
    result = detector.detect_all_pages(pdf_path, extract_text=False, filter_by_shape=False)
    
    # Count by color across all pages
    color_counts = {}
    for page_result in result.page_results:
        for region in page_result.regions:
            color = region.color_category
            color_counts[color] = color_counts.get(color, 0) + 1
    
    print("\nDetection results:")
    if color_counts:
        for color in sorted(color_counts.keys()):
            count = color_counts[color]
            print(f"  {color.upper():10s}: {count:3d} regions detected")
    else:
        print("  No colored regions detected")


def test_with_batch_processing():
    """Test batch processing of multiple PDFs"""
    print_header("TEST 4: Batch Processing Multiple PDFs")
    
    detector = ColoredCommentDetector(detection_dpi=200, ocr_dpi=300)
    
    input_dir = Path("dataset/raw_drawings/Electrical Engineering")
    output_dir = Path("dataset/preprocessed_images/comment_detection/batch")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not input_dir.exists():
        print(f"❌ Input directory not found: {input_dir}")
        return
    
    # Get first 3 PDFs for testing
    pdf_files = list(input_dir.glob("*.pdf"))[:3]
    
    if not pdf_files:
        print(f"❌ No PDF files found in: {input_dir}")
        return
    
    print(f"Processing {len(pdf_files)} PDF files:")
    for pdf in pdf_files:
        print(f"  • {pdf.name}")
    print()
    
    batch_results = []
    
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")
        
        try:
            result = detector.detect_all_pages(
                pdf_path=pdf_path,
                extract_text=True,
                filter_by_shape=True
            )
            
            batch_results.append({
                'file': pdf_path.name,
                'status': 'success',
                'pages': result.total_pages,
                'comments': result.total_regions
            })
            
            print(f"    ✅ Success: {result.total_regions} comments across {result.total_pages} pages")
            
            # Save first page visualization if comments exist
            if result.total_regions > 0 and result.page_results:
                first_page_with_comments = next(
                    (pr for pr in result.page_results if pr.regions), None
                )
                if first_page_with_comments:
                    vis_path = output_dir / f"{pdf_path.stem}_preview.png"
                    detector.visualize_detections(
                        pdf_path,
                        first_page_with_comments.page_number,
                        first_page_with_comments.regions,
                        vis_path
                    )
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            batch_results.append({
                'file': pdf_path.name,
                'status': 'failed',
                'error': str(e)
            })
    
    # Summary
    print(f"\n{'='*80}")
    print("BATCH PROCESSING SUMMARY")
    print(f"{'='*80}\n")
    
    successful = [r for r in batch_results if r['status'] == 'success']
    failed = [r for r in batch_results if r['status'] == 'failed']
    
    print(f"Total files: {len(pdf_files)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if successful:
        total_comments = sum(r['comments'] for r in successful)
        print(f"\nTotal comments detected: {total_comments}")
        print("\nPer-file results:")
        for r in successful:
            print(f"  • {r['file']}: {r['comments']} comments ({r['pages']} pages)")
    
    if failed:
        print("\nFailed files:")
        for r in failed:
            print(f"  ❌ {r['file']}: {r['error']}")


def test_parameter_tuning():
    """Test different detection parameters"""
    print_header("TEST 5: Detection Parameter Tuning")
    
    pdf_path = Path("dataset/raw_drawings/Electrical Engineering/5-1307-137_F_RJY.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"Testing different parameters on: {pdf_path.name}")
    print()
    
    # Test different DPI settings
    dpi_configs = [
        (150, 200, "Low (fast)"),
        (200, 300, "Medium (balanced)"),
        (300, 400, "High (accurate)")
    ]
    
    print("DPI Settings Comparison:")
    print("-" * 80)
    
    for detection_dpi, ocr_dpi, label in dpi_configs:
        import time
        
        detector = ColoredCommentDetector(
            detection_dpi=detection_dpi,
            ocr_dpi=ocr_dpi
        )
        
        start = time.time()
        comments = detector.detect_comments_on_page(pdf_path, 0, extract_text=False)
        elapsed = time.time() - start
        
        print(f"{label:20s} (detection={detection_dpi}, ocr={ocr_dpi})")
        print(f"  Comments detected: {len(comments)}")
        print(f"  Processing time: {elapsed:.2f}s")
        print()
    
    # Test with/without text extraction
    print("\nText Extraction Comparison:")
    print("-" * 80)
    
    detector = ColoredCommentDetector(detection_dpi=200, ocr_dpi=300)
    
    import time
    
    start = time.time()
    comments_no_text = detector.detect_comments_on_page(pdf_path, 0, extract_text=False)
    time_no_text = time.time() - start
    
    start = time.time()
    comments_with_text = detector.detect_comments_on_page(pdf_path, 0, extract_text=True)
    time_with_text = time.time() - start
    
    print(f"Without text extraction:")
    print(f"  Comments: {len(comments_no_text)}")
    print(f"  Time: {time_no_text:.2f}s")
    print()
    
    print(f"With text extraction:")
    print(f"  Comments: {len(comments_with_text)}")
    print(f"  Time: {time_with_text:.2f}s")
    print(f"  Overhead: {((time_with_text - time_no_text) / time_no_text * 100):.1f}%")
    print()
    
    # Show extracted text samples
    text_samples = [c for c in comments_with_text if c.extracted_text][:5]
    if text_samples:
        print("Sample extracted text:")
        for i, comment in enumerate(text_samples, 1):
            print(f"  {i}. [{comment.color_category}] '{comment.extracted_text[:50]}...'")


def run_all_tests():
    """Run all test cases"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 25 + "COLORED COMMENT DETECTION TESTS" + " " * 22 + "║")
    print("╚" + "═" * 78 + "╝")
    
    tests = [
        ("Single Page Detection", test_single_page_detection),
        ("Multi-Page Detection", test_multi_page_detection),
        ("Color Category Detection", test_different_colors),
        ("Batch Processing", test_with_batch_processing),
        ("Parameter Tuning", test_parameter_tuning),
    ]
    
    for test_name, test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"\n❌ Test failed: {test_name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 33 + "TESTS COMPLETE" + " " * 31 + "║")
    print("╚" + "═" * 78 + "╝")
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_num = sys.argv[1]
        
        tests = {
            '1': test_single_page_detection,
            '2': test_multi_page_detection,
            '3': test_different_colors,
            '4': test_with_batch_processing,
            '5': test_parameter_tuning,
        }
        
        if test_num in tests:
            tests[test_num]()
        else:
            print(f"Unknown test: {test_num}")
            print(f"Available tests: {', '.join(tests.keys())}")
    else:
        # Run all tests
        run_all_tests()
