"""
Test script for Hybrid OCR Service
"""
import sys
import logging
from pathlib import Path
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.hybrid_ocr_service import HybridOCRService


def test_tesseract_only():
    """Test Tesseract engine"""
    print("\n" + "="*80)
    print("Test 1: Tesseract Only (Printed Text)")
    print("="*80)
    
    ocr = HybridOCRService(lang='eng')
    
    # Find test file
    test_file = Path('dataset/raw_drawings/Electrical Engineering/5-1307-137_F_RJY.pdf')
    if not test_file.exists():
        print("Test file not found")
        return
    
    start = time.time()
    result = ocr.process_pdf(
        str(test_file),
        output_dir='dataset/extracted_text/test_hybrid',
        dpi=300,
        ocr_engine='tesseract'
    )
    elapsed = time.time() - start
    
    print(f"\n✓ Processed in {elapsed:.2f} seconds")
    print(f"  - Pages: {len(result['pages'])}")
    print(f"  - Characters extracted: {len(result['total_text'])}")
    if result['pages']:
        print(f"  - Avg confidence: {result['pages'][0]['avg_confidence']:.2%}")
    print(f"\nFirst 200 characters:")
    print(result['total_text'][:200])


def test_trocr_only():
    """Test TrOCR engine"""
    print("\n" + "="*80)
    print("Test 2: TrOCR Only (Handwritten Text)")
    print("="*80)
    print("Note: This will be slower as TrOCR downloads models on first run")
    print("Expected: ~300MB model download, then 3-5 seconds per page")
    
    ocr = HybridOCRService(
        lang='eng',
        trocr_model='microsoft/trocr-small-handwritten',  # Use small model for testing
        use_gpu=False
    )
    
    test_file = Path('dataset/raw_drawings/Electrical Engineering/5-1307-137_F_RJY.pdf')
    if not test_file.exists():
        print("Test file not found")
        return
    
    start = time.time()
    result = ocr.process_pdf(
        str(test_file),
        output_dir='dataset/extracted_text/test_hybrid',
        dpi=200,  # Lower DPI for faster testing
        ocr_engine='trocr'
    )
    elapsed = time.time() - start
    
    print(f"\n✓ Processed in {elapsed:.2f} seconds")
    print(f"  - Pages: {len(result['pages'])}")
    print(f"  - Text extracted: {len(result['total_text'])} characters")
    print(f"\nExtracted text:")
    print(result['total_text'][:300])


def test_auto_mode():
    """Test automatic engine selection"""
    print("\n" + "="*80)
    print("Test 3: Auto Mode (Intelligent Selection)")
    print("="*80)
    print("Will use Tesseract first, fallback to TrOCR if confidence is low")
    
    ocr = HybridOCRService(
        lang='eng',
        trocr_model='microsoft/trocr-small-handwritten',
        use_gpu=False
    )
    
    test_file = Path('dataset/raw_drawings/Electrical Engineering/5-1307-137_F_RJY.pdf')
    if not test_file.exists():
        print("Test file not found")
        return
    
    start = time.time()
    result = ocr.process_pdf(
        str(test_file),
        output_dir='dataset/extracted_text/test_hybrid',
        dpi=300,
        ocr_engine='auto'
    )
    elapsed = time.time() - start
    
    print(f"\n✓ Processed in {elapsed:.2f} seconds")
    print(f"  - Pages: {len(result['pages'])}")
    
    for page in result['pages']:
        engines = ', '.join(page['engines_used'])
        print(f"  - Page {page['page_number']}: Used {engines}")
        if 'avg_confidence' in page:
            print(f"    Confidence: {page['avg_confidence']:.2%}")


def test_both_engines():
    """Test both engines for comparison"""
    print("\n" + "="*80)
    print("Test 4: Both Engines (Side-by-Side Comparison)")
    print("="*80)
    
    ocr = HybridOCRService(
        lang='eng',
        trocr_model='microsoft/trocr-small-handwritten',
        use_gpu=False
    )
    
    test_file = Path('dataset/raw_drawings/Electrical Engineering/5-1307-137_F_RJY.pdf')
    if not test_file.exists():
        print("Test file not found")
        return
    
    start = time.time()
    result = ocr.process_pdf(
        str(test_file),
        output_dir='dataset/extracted_text/test_hybrid',
        dpi=200,
        ocr_engine='both'
    )
    elapsed = time.time() - start
    
    print(f"\n✓ Processed in {elapsed:.2f} seconds")
    print(f"\nResults saved with both engine outputs for comparison")
    print(f"Check: dataset/extracted_text/test_hybrid/")


def test_region_extraction():
    """Test extracting specific regions (e.g., title block with handwritten notes)"""
    print("\n" + "="*80)
    print("Test 5: Region Extraction (Title Block)")
    print("="*80)
    
    ocr = HybridOCRService(lang='eng')
    
    test_file = Path('dataset/raw_drawings/Electrical Engineering/5-1307-137_F_RJY.pdf')
    if not test_file.exists():
        print("Test file not found")
        return
    
    # Extract title block with Tesseract
    print("\nExtracting with Tesseract...")
    result_tess = ocr.process_region(
        str(test_file),
        page_num=0,
        region=None,  # Auto-detect bottom-right 30%
        ocr_engine='tesseract'
    )
    
    print(f"✓ Tesseract result ({result_tess['confidence']:.2%} confidence):")
    print(result_tess['text'][:200])
    
    # Same region with TrOCR (good for handwritten markups)
    print("\nExtracting with TrOCR (for handwritten annotations)...")
    result_trocr = ocr.process_region(
        str(test_file),
        page_num=0,
        region=None,
        ocr_engine='trocr'
    )
    
    print(f"✓ TrOCR result:")
    print(result_trocr['text'][:200])


def main():
    """Run all tests"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("="*80)
    print("Hybrid OCR Service Test Suite")
    print("="*80)
    print("\nThis will test:")
    print("  1. Tesseract (fast, for printed text)")
    print("  2. TrOCR (slower, for handwritten text)")
    print("  3. Auto mode (intelligent selection)")
    print("  4. Both engines (comparison)")
    print("  5. Region extraction (title blocks, annotations)")
    
    print("\n⚠️  Note: First run will download TrOCR models (~300MB)")
    print("    Subsequent runs will be much faster")
    
    choice = input("\nRun which test? (1-5, or 'all'): ").strip().lower()
    
    try:
        if choice == '1':
            test_tesseract_only()
        elif choice == '2':
            test_trocr_only()
        elif choice == '3':
            test_auto_mode()
        elif choice == '4':
            test_both_engines()
        elif choice == '5':
            test_region_extraction()
        elif choice == 'all':
            test_tesseract_only()
            test_trocr_only()
            test_auto_mode()
            test_both_engines()
            test_region_extraction()
        else:
            print("Invalid choice")
            return
        
        print("\n" + "="*80)
        print("✅ Tests Complete!")
        print("="*80)
        print("\nCheck results in: dataset/extracted_text/test_hybrid/")
        print("\nNext steps:")
        print("  - Use 'tesseract' for fast processing of printed text")
        print("  - Use 'trocr' for handwritten annotations and markups")
        print("  - Use 'auto' for intelligent engine selection")
        print("  - Use 'both' to compare results side-by-side")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
