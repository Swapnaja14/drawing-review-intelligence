"""
Test template region filtering across all pages.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.services.annotation_service_enhanced import AnnotationDetectionServiceEnhanced


def main():
    print("\n" + "="*80)
    print(" " * 15 + "TESTING TEMPLATE FILTERING")
    print("="*80)
    
    # Find sample PDF
    project_root = Path(__file__).resolve().parents[1]
    sample_pdf = project_root / 'dataset' / 'raw_drawings' / 'Electrical Engineering' / '5-1307-137_F_RJY.pdf'
    
    if not sample_pdf.exists():
        print(f"\n❌ Sample PDF not found: {sample_pdf}")
        return
    
    print(f"\nPDF: {sample_pdf.name}\n")
    
    # Initialize service
    annotation_service = AnnotationDetectionServiceEnhanced()
    
    # Test WITHOUT filtering
    print("="*80)
    print("WITHOUT TEMPLATE FILTERING:")
    print("="*80)
    result_unfiltered = annotation_service.detect_all_pages(sample_pdf, method='hybrid', 
                                                             filter_template_regions=False)
    
    for page_result in result_unfiltered.page_results:
        print(f"\nPage {page_result.page_number + 1}: {len(page_result.regions)} regions")
        if page_result.regions:
            for i, region in enumerate(page_result.regions[:3], 1):
                x_pct = (region.x0 / 3024.0) * 100
                y_pct = (region.y0 / 2160.0) * 100
                print(f"  Region {i}: [{region.x0:7.1f}, {region.y0:7.1f}] → {x_pct:.1f}% from left, {y_pct:.1f}% from top ({region.label})")
    
    # Test WITH filtering
    print("\n" + "="*80)
    print("WITH TEMPLATE FILTERING:")
    print("="*80)
    result_filtered = annotation_service.detect_all_pages(sample_pdf, method='hybrid', 
                                                           filter_template_regions=True)
    
    for page_result in result_filtered.page_results:
        print(f"\nPage {page_result.page_number + 1}: {len(page_result.regions)} regions")
        if page_result.regions:
            for i, region in enumerate(page_result.regions[:3], 1):
                x_pct = (region.x0 / 3024.0) * 100
                y_pct = (region.y0 / 2160.0) * 100
                print(f"  Region {i}: [{region.x0:7.1f}, {region.y0:7.1f}] → {x_pct:.1f}% from left, {y_pct:.1f}% from top ({region.label})")
        else:
            print("  (No regions - all were template elements)")
    
    print("\n" + "="*80)
    print("COMPARISON:")
    print("="*80)
    print(f"Before filtering: {result_unfiltered.total_regions} total regions")
    print(f"After filtering:  {result_filtered.total_regions} total regions")
    print(f"Removed:          {result_unfiltered.total_regions - result_filtered.total_regions} template regions")
    
    print("\n" + "="*80)
    print("EXPECTED RESULT:")
    print("="*80)
    print("- Page 3 should have MOST regions (it has 2 native annotations + text)")
    print("- Pages 1-2 should have FEWER regions (no native annotations)")
    print("- Regions should be at DIFFERENT positions on each page (not all in title block)")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
