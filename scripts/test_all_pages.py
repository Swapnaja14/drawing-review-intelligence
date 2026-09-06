"""
Test annotations on ALL pages to verify they're different.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.services.annotation_service_enhanced import AnnotationDetectionServiceEnhanced


def main():
    print("\n" + "="*80)
    print(" " * 20 + "TESTING ALL PAGES")
    print("="*80)
    
    # Find sample PDF
    project_root = Path(__file__).resolve().parents[1]
    sample_pdf = project_root / 'dataset' / 'raw_drawings' / 'Electrical Engineering' / '5-1307-137_F_RJY.pdf'
    
    if not sample_pdf.exists():
        print(f"\n❌ Sample PDF not found: {sample_pdf}")
        return
    
    print(f"\nPDF: {sample_pdf.name}")
    
    # Initialize service
    annotation_service = AnnotationDetectionServiceEnhanced()
    
    # Test all pages
    for page_num in range(3):  # 3 pages in this PDF
        print(f"\n{'='*80}")
        print(f"PAGE {page_num + 1}:")
        print('='*80)
        
        result = annotation_service.detect_annotations_on_page(sample_pdf, page_num, method='color')
        
        print(f"✓ Detected {len(result.regions)} regions")
        
        if not result.regions:
            print("❌ NO REGIONS!")
            continue
        
        # Show first 5 regions
        for i, region in enumerate(result.regions[:5], 1):
            x_pct = (region.x0 / 3024.0) * 100
            y_pct = (region.y0 / 2160.0) * 100
            print(f"  Region {i}: [{region.x0:7.1f}, {region.y0:7.1f}] → {x_pct:.1f}% from left, {y_pct:.1f}% from top")
        
        if len(result.regions) > 5:
            print(f"  ... and {len(result.regions) - 5} more")
    
    print("\n" + "="*80)
    print("RESULT:")
    print("="*80)
    print("If coordinates are DIFFERENT between pages, annotations are dynamic ✅")
    print("If coordinates are THE SAME, there's a bug ❌")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
