"""
Interactive script to run Hybrid OCR on engineering drawings
"""
import sys
import logging
from pathlib import Path
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.hybrid_ocr_service import HybridOCRService


def print_header():
    """Print script header"""
    print("="*80)
    print("Hybrid OCR Processor for Engineering Drawings")
    print("="*80)
    print("\nCombines:")
    print("  • Tesseract - Fast processing for printed text")
    print("  • TrOCR - AI-powered recognition for handwritten text")
    print()


def get_test_file():
    """Find a test PDF file"""
    test_dirs = [
        'dataset/raw_drawings/Electrical Engineering',
        'dataset/raw_drawings/GPD',
        'dataset/raw_drawings/Pipe Support Engineering'
    ]
    
    for test_dir in test_dirs:
        test_path = Path(test_dir)
        if test_path.exists():
            pdfs = list(test_path.glob('*.pdf'))
            if pdfs:
                return pdfs[0]
    return None


def process_single_file():
    """Process a single file with engine selection"""
    print("\n" + "="*80)
    print("Single File Processing")
    print("="*80)
    
    test_file = get_test_file()
    if not test_file:
        print("No PDF files found in dataset/raw_drawings/")
        return
    
    print(f"\nFile: {test_file.name}")
    print("\nSelect OCR Engine:")
    print("  1. Auto (recommended) - Intelligent selection")
    print("  2. Tesseract only - Fast, for printed text")
    print("  3. TrOCR only - Slow, for handwritten text")
    print("  4. Both - Compare results side-by-side")
    
    engine_choice = input("\nChoice (1-4): ").strip()
    engine_map = {
        '1': 'auto',
        '2': 'tesseract',
        '3': 'trocr',
        '4': 'both'
    }
    
    engine = engine_map.get(engine_choice, 'auto')
    
    print(f"\nInitializing OCR (engine: {engine})...")
    
    if engine in ['trocr', 'both', 'auto']:
        print("⚠️  Note: TrOCR will download ~300MB model on first run")
        print("   This is a one-time download. Please wait...")
    
    try:
        ocr = HybridOCRService(
            lang='eng',
            trocr_model='microsoft/trocr-small-handwritten',
            use_gpu=False
        )
        
        print(f"\n✓ OCR initialized")
        print(f"Processing {test_file.name}...")
        
        start = time.time()
        result = ocr.process_pdf(
            str(test_file),
            output_dir='dataset/extracted_text/test_hybrid',
            dpi=300,
            ocr_engine=engine
        )
        elapsed = time.time() - start
        
        # Display results
        print(f"\n{'='*80}")
        print(f"Results")
        print(f"{'='*80}")
        print(f"✓ Processed in {elapsed:.2f} seconds")
        print(f"  - Pages: {result['metadata']['total_pages']}")
        print(f"  - Characters extracted: {len(result['total_text'])}")
        
        # Show which engines were used per page
        print(f"\nEngines used per page:")
        for page in result['pages']:
            engines = ', '.join(page['engines_used'])
            conf = page.get('avg_confidence', 0)
            print(f"  - Page {page['page_number']}: {engines} (confidence: {conf:.2%})")
        
        print(f"\n📄 Output saved to:")
        print(f"   dataset/extracted_text/test_hybrid/{test_file.stem}_hybrid_ocr.txt")
        
        print(f"\nText preview (first 300 chars):")
        print("-"*80)
        print(result['total_text'][:300])
        print("-"*80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def process_category():
    """Process all files in a category"""
    print("\n" + "="*80)
    print("Batch Processing by Category")
    print("="*80)
    
    categories = [
        'Electrical Engineering',
        'GPD',
        'Pipe Support Engineering',
        'Piping Engineering',
        'Process Engineering',
        'Structural Engineering'
    ]
    
    print("\nAvailable categories:")
    for i, cat in enumerate(categories, 1):
        cat_path = Path(f'dataset/raw_drawings/{cat}')
        if cat_path.exists():
            pdf_count = len(list(cat_path.glob('*.pdf')))
            print(f"  {i}. {cat} ({pdf_count} PDFs)")
        else:
            print(f"  {i}. {cat} (not found)")
    
    choice = input("\nSelect category (1-6): ").strip()
    try:
        cat_idx = int(choice) - 1
        if 0 <= cat_idx < len(categories):
            category = categories[cat_idx]
        else:
            print("Invalid choice")
            return
    except ValueError:
        print("Invalid choice")
        return
    
    input_dir = f'dataset/raw_drawings/{category}'
    if not Path(input_dir).exists():
        print(f"Directory not found: {input_dir}")
        return
    
    # Engine selection
    print("\nSelect OCR Engine:")
    print("  1. Auto (recommended)")
    print("  2. Tesseract only (fast)")
    print("  3. TrOCR only (for handwritten markups)")
    
    engine_choice = input("\nChoice (1-3): ").strip()
    engine_map = {'1': 'auto', '2': 'tesseract', '3': 'trocr'}
    engine = engine_map.get(engine_choice, 'auto')
    
    print(f"\nInitializing OCR...")
    
    try:
        ocr = HybridOCRService(
            lang='eng',
            trocr_model='microsoft/trocr-small-handwritten',
            use_gpu=False
        )
        
        print(f"✓ OCR initialized")
        print(f"\nProcessing {category}...")
        print(f"Engine: {engine}")
        print(f"This may take several minutes...\n")
        
        start = time.time()
        results = ocr.batch_process_drawings(
            input_dir=input_dir,
            output_dir=f'dataset/extracted_text/{category}',
            dpi=300,
            ocr_engine=engine
        )
        elapsed = time.time() - start
        
        # Summary
        successful = [r for r in results if 'error' not in r]
        failed = [r for r in results if 'error' in r]
        
        print(f"\n{'='*80}")
        print(f"Batch Processing Complete")
        print(f"{'='*80}")
        print(f"Time elapsed: {elapsed/60:.1f} minutes")
        print(f"Total files: {len(results)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")
        
        if successful:
            avg_time = elapsed / len(successful)
            print(f"Average time per file: {avg_time:.1f} seconds")
        
        if failed:
            print(f"\n❌ Failed files:")
            for r in failed[:5]:  # Show first 5 failures
                print(f"  - {r['file_name']}: {r.get('error', 'Unknown')[:50]}")
            if len(failed) > 5:
                print(f"  ... and {len(failed)-5} more")
        
        print(f"\n✓ Results saved to: dataset/extracted_text/{category}/")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def extract_handwritten_regions():
    """Extract handwritten comments from specific regions"""
    print("\n" + "="*80)
    print("Extract Handwritten Comments/Markups")
    print("="*80)
    
    test_file = get_test_file()
    if not test_file:
        print("No PDF files found")
        return
    
    print(f"\nFile: {test_file.name}")
    print("\nThis will extract text from the bottom-right region")
    print("(typical location for title blocks and handwritten notes)")
    
    input("\nPress Enter to continue...")
    
    try:
        print("\nInitializing TrOCR for handwritten text...")
        ocr = HybridOCRService(
            lang='eng',
            trocr_model='microsoft/trocr-base-handwritten',  # Better for handwriting
            use_gpu=False
        )
        
        print("✓ TrOCR loaded")
        print("Extracting title block region...")
        
        # Extract with both engines for comparison
        result_tess = ocr.process_region(
            str(test_file),
            page_num=0,
            region=None,  # Auto: bottom-right 30%
            ocr_engine='tesseract'
        )
        
        result_trocr = ocr.process_region(
            str(test_file),
            page_num=0,
            region=None,
            ocr_engine='trocr'
        )
        
        print(f"\n{'='*80}")
        print("Extraction Results")
        print(f"{'='*80}")
        
        print(f"\n=== Tesseract (Printed Text) ===")
        print(f"Confidence: {result_tess['confidence']:.2%}")
        print(f"Text:\n{result_tess['text'][:300]}")
        
        print(f"\n=== TrOCR (Handwritten Text) ===")
        print(f"Text:\n{result_trocr['text'][:300]}")
        
        print(f"\n💡 Tip: TrOCR is better at reading handwritten annotations,")
        print(f"   while Tesseract is faster for printed text")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def compare_engines():
    """Run both engines and compare results"""
    print("\n" + "="*80)
    print("Engine Comparison Test")
    print("="*80)
    
    test_file = get_test_file()
    if not test_file:
        print("No PDF files found")
        return
    
    print(f"\nFile: {test_file.name}")
    print("\nThis will run both Tesseract and TrOCR on the same file")
    print("and save results for comparison.")
    
    input("\nPress Enter to continue...")
    
    try:
        print("\nInitializing hybrid OCR...")
        ocr = HybridOCRService(
            lang='eng',
            trocr_model='microsoft/trocr-small-handwritten',
            use_gpu=False
        )
        
        print("✓ OCR initialized")
        print("\nProcessing with both engines...")
        
        start = time.time()
        result = ocr.process_pdf(
            str(test_file),
            output_dir='dataset/extracted_text/comparison',
            dpi=250,  # Lower DPI for faster testing
            ocr_engine='both'
        )
        elapsed = time.time() - start
        
        print(f"\n{'='*80}")
        print("Comparison Complete")
        print(f"{'='*80}")
        print(f"Time: {elapsed:.1f} seconds")
        print(f"\nResults saved to:")
        print(f"  dataset/extracted_text/comparison/{test_file.stem}_hybrid_ocr.txt")
        print(f"\nThe file contains outputs from both engines for comparison")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main menu"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    print_header()
    
    while True:
        print("\nOptions:")
        print("  1. Process single file (with engine selection)")
        print("  2. Batch process category")
        print("  3. Extract handwritten comments/markups")
        print("  4. Compare engines side-by-side")
        print("  5. Exit")
        
        choice = input("\nChoice (1-5): ").strip()
        
        if choice == '1':
            process_single_file()
        elif choice == '2':
            process_category()
        elif choice == '3':
            extract_handwritten_regions()
        elif choice == '4':
            compare_engines()
        elif choice == '5':
            print("\nExiting...")
            break
        else:
            print("Invalid choice")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
