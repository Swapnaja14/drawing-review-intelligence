"""
Complete Pipeline Demo - For Mentor Presentation
Shows: OCR → Text Cleaning → Classification on any drawing

Usage: python scripts/demo_complete_pipeline.py
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.services.ocr_service import OCRService
from src.services.text_cleaning_service import TextCleaningService
from src.services.classification_service import ClassificationService
import logging

# Setup logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise


def print_header(title):
    """Print formatted header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_section(title):
    """Print section divider"""
    print(f"\n{'-'*80}")
    print(f"  {title}")
    print(f"{'-'*80}\n")


def list_available_drawings():
    """List all available PDF drawings"""
    base_dir = Path("dataset/raw_drawings")
    
    if not base_dir.exists():
        print(f"❌ Directory not found: {base_dir}")
        return []
    
    drawings = []
    categories = []
    
    # Scan all subdirectories
    for category_dir in sorted(base_dir.iterdir()):
        if category_dir.is_dir():
            pdf_files = list(category_dir.glob("*.pdf"))
            if pdf_files:
                categories.append(category_dir.name)
                for pdf in sorted(pdf_files):
                    drawings.append({
                        'path': pdf,
                        'name': pdf.name,
                        'category': category_dir.name
                    })
    
    return drawings, categories


def select_drawing(drawings):
    """Interactive drawing selection"""
    print("Available Engineering Drawings:\n")
    
    current_category = None
    for i, drawing in enumerate(drawings, 1):
        # Print category header
        if drawing['category'] != current_category:
            current_category = drawing['category']
            print(f"\n📁 {current_category}")
            print("   " + "-" * 50)
        
        # Print drawing with number
        print(f"   [{i:2d}] {drawing['name']}")
    
    print(f"\n   [0] Exit\n")
    
    while True:
        try:
            choice = input("Select drawing number: ").strip()
            
            if not choice:
                continue
            
            choice = int(choice)
            
            if choice == 0:
                print("\n👋 Exiting...\n")
                return None
            
            if 1 <= choice <= len(drawings):
                return drawings[choice - 1]
            else:
                print(f"❌ Invalid choice. Please select 1-{len(drawings)}")
        
        except ValueError:
            print("❌ Please enter a number")
        except KeyboardInterrupt:
            print("\n\n👋 Exiting...\n")
            return None


def extract_text_from_drawing(pdf_path):
    """Extract text using OCR"""
    import time
    
    print(f"📄 Processing: {pdf_path.name}")
    print(f"   Category: {pdf_path.parent.name}")
    print(f"   Path: {pdf_path}\n")
    
    print("⏳ Extracting text with OCR (Tesseract at 200 DPI - optimized for speed)...")
    print("   This may take 3-5 seconds... ⏰")
    
    start_time = time.time()
    
    try:
        ocr = OCRService()
        # Use 200 DPI for faster demo (instead of 300)
        result = ocr.process_pdf(str(pdf_path), output_dir=None, dpi=200)
        
        elapsed = time.time() - start_time
        
        # Extract all text
        all_text = result['total_text'].strip()
        
        # Get confidence scores
        avg_confidence = 0
        if result['pages']:
            confidences = [p.get('avg_confidence', 0) for p in result['pages']]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        print(f"✅ OCR Complete in {elapsed:.1f} seconds!")
        print(f"   Pages: {result['metadata']['total_pages']}")
        print(f"   Characters extracted: {len(all_text)}")
        print(f"   Average confidence: {avg_confidence:.1%}")
        
        return all_text, avg_confidence
    
    except Exception as e:
        print(f"❌ OCR Error: {e}")
        return None, 0


def extract_sample_comments(text, num_lines=10):
    """Extract sample lines that look like comments"""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Filter out very short lines (likely noise)
    meaningful_lines = [line for line in lines if len(line) > 10]
    
    # Take first N lines as sample
    sample = meaningful_lines[:num_lines] if meaningful_lines else lines[:num_lines]
    
    return sample


def demo_text_cleaning(text_samples):
    """Demonstrate text cleaning on samples"""
    print_section("STEP 2: Text Cleaning")
    
    cleaner = TextCleaningService()
    
    print("Cleaning extracted text (expanding abbreviations, normalizing)...\n")
    
    cleaned_samples = []
    
    for i, raw_text in enumerate(text_samples, 1):
        if not raw_text:
            continue
        
        print(f"Sample {i}:")
        print(f"  Original: \"{raw_text[:80]}{'...' if len(raw_text) > 80 else ''}\"")
        
        # Clean text
        result = cleaner.clean_text(raw_text)
        
        print(f"  Cleaned:  \"{result.cleaned_text[:80]}{'...' if len(result.cleaned_text) > 80 else ''}\"")
        
        if result.corrections:
            print(f"  Corrections: {len(result.corrections)} applied")
            # Show first 2 corrections
            for correction in result.corrections[:2]:
                print(f"    - '{correction.original}' → '{correction.corrected}'")
        else:
            print(f"  Corrections: None needed")
        
        print()
        
        cleaned_samples.append(result.cleaned_text)
    
    return cleaned_samples


def demo_classification(text_samples):
    """Demonstrate classification on samples"""
    print_section("STEP 3: AI Classification")
    
    classifier = ClassificationService()
    
    print("Classifying comments into 6 categories...\n")
    
    results = []
    
    for i, text in enumerate(text_samples, 1):
        if not text:
            continue
        
        # Classify
        result = classifier.classify_comment(text, comment_id=str(i))
        results.append(result)
        
        # Display result
        confidence = result.primary_category.confidence
        category = result.primary_category.category_name
        
        # Confidence indicator
        if confidence >= 0.8:
            indicator = "🟢 High"
        elif confidence >= 0.6:
            indicator = "🟡 Medium"
        else:
            indicator = "🔴 Low"
        
        print(f"Comment {i}:")
        print(f"  Text: \"{text[:70]}{'...' if len(text) > 70 else ''}\"")
        print(f"  Category: {category}")
        print(f"  Confidence: {indicator} ({confidence:.1%})")
        
        if result.primary_category.matched_keywords:
            keywords = ', '.join(result.primary_category.matched_keywords[:5])
            if len(result.primary_category.matched_keywords) > 5:
                keywords += f" (+{len(result.primary_category.matched_keywords)-5} more)"
            print(f"  Keywords: {keywords}")
        
        if result.requires_human_review:
            print(f"  ⚠️  Flagged for human review (low confidence)")
        
        print()
    
    return results


def show_summary(results):
    """Show classification summary"""
    print_section("SUMMARY")
    
    # Count by category
    category_counts = {}
    high_conf = 0
    low_conf = 0
    flagged = 0
    
    for result in results:
        cat = result.primary_category.category_name
        category_counts[cat] = category_counts.get(cat, 0) + 1
        
        if result.primary_category.confidence >= 0.8:
            high_conf += 1
        else:
            low_conf += 1
        
        if result.requires_human_review:
            flagged += 1
    
    print(f"Total Comments Analyzed: {len(results)}")
    print(f"\nCategory Distribution:")
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat:30s}: {count:2d} ({count/len(results)*100:.1f}%)")
    
    print(f"\nConfidence Scores:")
    print(f"  High confidence (≥80%): {high_conf} ({high_conf/len(results)*100:.1f}%)")
    print(f"  Low confidence (<80%):  {low_conf} ({low_conf/len(results)*100:.1f}%)")
    
    if flagged > 0:
        print(f"\n⚠️  {flagged} comment(s) flagged for human review")
    
    print()


def main():
    """Main demo function"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "COMPLETE PIPELINE DEMONSTRATION" + " " * 27 + "║")
    print("║" + " " * 15 + "OCR → Text Cleaning → Classification" + " " * 27 + "║")
    print("╚" + "═" * 78 + "╝")
    
    # List available drawings
    print_header("Available Drawings")
    
    drawings, categories = list_available_drawings()
    
    if not drawings:
        print("❌ No drawings found in dataset/raw_drawings/")
        return
    
    print(f"Found {len(drawings)} drawings across {len(categories)} categories")
    
    # Select drawing
    selected = select_drawing(drawings)
    
    if selected is None:
        return
    
    print(f"\n✅ Selected: {selected['name']}")
    
    # Step 1: OCR
    print_header("STEP 1: OCR Text Extraction")
    
    text, confidence = extract_text_from_drawing(selected['path'])
    
    if not text:
        print("❌ Failed to extract text. Cannot continue.")
        return
    
    # Extract sample comments
    print(f"\n📝 Extracting sample lines from OCR output...")
    samples = extract_sample_comments(text, num_lines=8)
    print(f"✅ Extracted {len(samples)} sample lines\n")
    
    if not samples:
        print("❌ No meaningful text found. Cannot continue.")
        return
    
    # Step 2: Text Cleaning
    cleaned_samples = demo_text_cleaning(samples)
    
    # Step 3: Classification
    results = demo_classification(cleaned_samples)
    
    # Summary
    if results:
        show_summary(results)
    
    # Conclusion
    print("="*80)
    print("\n✅ DEMO COMPLETE!\n")
    print("This demonstration showed:")
    print("  1. ✅ OCR text extraction (Tesseract)")
    print("  2. ✅ Text cleaning (44 abbreviations)")
    print("  3. ✅ AI classification (6 categories, 170+ keywords)")
    print("  4. ✅ Confidence scoring")
    print("  5. ✅ Automatic flagging for human review")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted. Exiting...\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
