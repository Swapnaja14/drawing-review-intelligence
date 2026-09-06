"""
Check what's different between pages in the PDF.
"""

import sys
from pathlib import Path
import fitz

sys.path.append(str(Path(__file__).resolve().parents[1]))


def main():
    print("\n" + "="*80)
    print(" " * 15 + "CHECKING PAGE DIFFERENCES")
    print("="*80)
    
    # Find sample PDF
    project_root = Path(__file__).resolve().parents[1]
    sample_pdf = project_root / 'dataset' / 'raw_drawings' / 'Electrical Engineering' / '5-1307-137_F_RJY.pdf'
    
    if not sample_pdf.exists():
        print(f"\n❌ Sample PDF not found: {sample_pdf}")
        return
    
    print(f"\nPDF: {sample_pdf.name}\n")
    
    doc = fitz.open(sample_pdf)
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        print(f"{'='*80}")
        print(f"PAGE {page_num + 1}:")
        print('='*80)
        
        # Check native annotations
        annots = list(page.annots())
        print(f"Native annotations: {len(annots)}")
        if annots:
            for i, annot in enumerate(annots[:3], 1):
                print(f"  {i}. Type: {annot.type}, Rect: {annot.rect}")
        
        # Check text content (sample)
        text = page.get_text()
        print(f"Text content length: {len(text)} characters")
        print(f"First 200 chars: {text[:200]}")
        
        # Check images
        images = page.get_images()
        print(f"Embedded images: {len(images)}")
        
        # Check drawings (vector graphics)
        drawings = page.get_drawings()
        print(f"Vector drawings: {len(drawings)}")
        
        print()
    
    doc.close()
    
    print("="*80)
    print("INTERPRETATION:")
    print("="*80)
    print("- If pages have SAME text/images/drawings → Template is identical")
    print("- If pages have DIFFERENT content → Should show different annotations")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
