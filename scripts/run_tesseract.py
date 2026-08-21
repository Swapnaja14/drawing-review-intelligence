"""
Script to run Tesseract OCR on engineering drawings
"""
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.ocr_service import OCRService


def process_single_file():
    """Test OCR on a single file"""
    print("Testing OCR on single file...")
    
    ocr_service = OCRService(lang='eng')
    
    # Find test file
    test_dirs = [
        'dataset/raw_drawings/Electrical Engineering',
        'dataset/raw_drawings/GPD',
        'dataset/raw_drawings/Pipe Support Engineering'
    ]
    
    test_file = None
    for test_dir in test_dirs:
        test_path = Path(test_dir)
        if test_path.exists():
            pdfs = list(test_path.glob('*.pdf'))
            if pdfs:
                test_file = pdfs[0]
                break
    
    if not test_file:
        print(f"No test PDF found in:")
        for d in test_dirs:
            print(f"  - {d}")
        print("Please add PDF files to process")
        return
    
    print(f"\nProcessing: {test_file.name}")
    print("This may take a minute...")
    
    result = ocr_service.process_pdf(
        str(test_file),
        output_dir='dataset/extracted_text/test',
        dpi=300
    )
    
    print(f"\n{'='*80}")
    print(f"File: {result['file_name']}")
    print(f"Pages: {result['metadata']['total_pages']}")
    print(f"Total characters: {len(result['total_text'])}")
    
    if result['pages']:
        avg_conf = sum(p['avg_confidence'] for p in result['pages']) / len(result['pages'])
        print(f"Average confidence: {avg_conf:.2%}")
    
    print(f"\nExtracted Text Preview:")
    print(f"{'='*80}")
    print(result['total_text'][:500])  # First 500 characters
    print(f"\n... (total {len(result['total_text'])} characters)")
    print(f"\n✓ Results saved to: dataset/extracted_text/test/{Path(test_file).stem}_ocr.txt")


def process_all_electrical():
    """Process all Electrical Engineering drawings"""
    print("Processing all Electrical Engineering drawings...")
    
    ocr_service = OCRService(lang='eng')
    
    input_dir = 'dataset/raw_drawings/Electrical Engineering'
    if not Path(input_dir).exists():
        print(f"Directory not found: {input_dir}")
        return
    
    results = ocr_service.batch_process_drawings(
        input_dir=input_dir,
        output_dir='dataset/extracted_text/Electrical Engineering',
        dpi=300
    )
    
    # Summary
    print(f"\n{'='*80}")
    print(f"Batch Processing Complete")
    print(f"{'='*80}")
    print(f"Total files processed: {len(results)}")
    
    successful = [r for r in results if 'error' not in r]
    failed = [r for r in results if 'error' in r]
    
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if successful:
        avg_conf = sum(
            sum(p['avg_confidence'] for p in r['pages']) / len(r['pages'])
            for r in successful if r['pages']
        ) / len([r for r in successful if r['pages']])
        print(f"Average confidence: {avg_conf:.2%}")
    
    if failed:
        print("\nFailed files:")
        for r in failed:
            print(f"  - {r['file_name']}: {r.get('error', 'Unknown error')}")


def process_all_categories():
    """Process all drawing categories"""
    print("Processing all drawing categories...")
    
    ocr_service = OCRService(lang='eng')
    
    categories = [
        'Electrical Engineering',
        'GPD',
        'Pipe Support Engineering',
        'Piping Engineering',
        'Process Engineering',
        'Structural Engineering'
    ]
    
    base_dir = Path('dataset/raw_drawings')
    
    overall_stats = {
        'total_files': 0,
        'successful': 0,
        'failed': 0
    }
    
    for category in categories:
        category_path = base_dir / category
        if not category_path.exists():
            print(f"Skipping {category} (directory not found)")
            continue
        
        print(f"\nProcessing {category}...")
        
        results = ocr_service.batch_process_drawings(
            input_dir=str(category_path),
            output_dir=f'dataset/extracted_text/{category}',
            dpi=300
        )
        
        successful = [r for r in results if 'error' not in r]
        failed = [r for r in results if 'error' in r]
        
        overall_stats['total_files'] += len(results)
        overall_stats['successful'] += len(successful)
        overall_stats['failed'] += len(failed)
        
        print(f"  ✓ {len(successful)}/{len(results)} files processed")
    
    print(f"\n{'='*80}")
    print("Overall Summary")
    print(f"{'='*80}")
    print(f"Total files: {overall_stats['total_files']}")
    print(f"Successful: {overall_stats['successful']}")
    print(f"Failed: {overall_stats['failed']}")
    
    if overall_stats['successful'] > 0:
        success_rate = (overall_stats['successful'] / overall_stats['total_files']) * 100
        print(f"Success rate: {success_rate:.1f}%")


def main():
    """Main entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("="*80)
    print("Engineering Drawing OCR Processor (Tesseract)")
    print("="*80)
    print("\nOptions:")
    print("1. Test single file")
    print("2. Process all Electrical Engineering drawings")
    print("3. Process all categories")
    print("4. Exit")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == '1':
        process_single_file()
    elif choice == '2':
        process_all_electrical()
    elif choice == '3':
        process_all_categories()
    elif choice == '4':
        print("Exiting...")
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
