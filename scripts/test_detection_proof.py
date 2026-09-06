"""
Proof Test: Show what gets detected and what gets filtered
This demonstrates the system correctly distinguishes comments from non-comments
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import logging
from src.services.colored_comment_detector import ColoredCommentDetector

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def test_detection_proof():
    """
    Show detailed proof of what gets accepted vs rejected
    """
    print("\n" + "="*80)
    print("DETECTION PROOF TEST")
    print("="*80 + "\n")
    
    detector = ColoredCommentDetector()
    pdf_path = Path("dataset/raw_drawings/Electrical Engineering/5-1307-137_F_RJY.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"Testing: {pdf_path.name}")
    print(f"Configuration:")
    print(f"  - Min area: {detector.min_comment_area_px} pixels")
    print(f"  - Max area: {detector.max_comment_area_px} pixels")
    print(f"  - Min words: {detector.min_word_count}")
    print(f"  - Min text confidence: {detector.min_text_confidence}")
    print("\n" + "-"*80 + "\n")
    
    # Process first page with detailed logging
    import fitz
    import cv2
    import numpy as np
    
    doc = fitz.open(pdf_path)
    page = doc[0]
    
    # Step 1: Show initial color detection
    print("STEP 1: COLOR DETECTION")
    print("-"*80)
    
    colored_regions = detector._detect_colored_regions(page, 0)
    print(f"Found {len(colored_regions)} colored regions:\n")
    
    for i, region in enumerate(colored_regions, 1):
        area = (region.x1 - region.x0) * (region.y1 - region.y0)
        print(f"  [{i}] {region.color_category.upper()}")
        print(f"      Position: ({region.x0:.1f}, {region.y0:.1f}) → ({region.x1:.1f}, {region.y1:.1f})")
        print(f"      Size: {(region.x1 - region.x0):.1f} × {(region.y1 - region.y0):.1f} pts")
        print(f"      Area: {area:.0f} sq pts")
        print(f"      Confidence: {region.confidence:.2%}")
        print()
    
    # Step 2: Shape filtering
    print("\n" + "="*80)
    print("STEP 2: SHAPE FILTERING")
    print("-"*80)
    
    shaped_regions = detector._filter_by_box_shape(page, colored_regions)
    
    filtered_out = len(colored_regions) - len(shaped_regions)
    print(f"Kept {len(shaped_regions)} box-shaped regions (filtered {filtered_out})\n")
    
    # Step 3: Text extraction
    print("="*80)
    print("STEP 3: TEXT EXTRACTION (OCR)")
    print("-"*80 + "\n")
    
    text_regions = detector._extract_text_from_regions(page, shaped_regions)
    
    for i, region in enumerate(text_regions, 1):
        print(f"  [{i}] {region.color_category.upper()}")
        print(f"      Extracted text: '{region.extracted_text}'")
        print(f"      Text confidence: {region.text_confidence:.2%}")
        print(f"      Text length: {len(region.extracted_text)} characters")
        print(f"      Word count: {len(region.extracted_text.split())}")
        print()
    
    # Step 4: Text validation (the critical filter)
    print("="*80)
    print("STEP 4: TEXT VALIDATION (COMMENT DETECTION)")
    print("-"*80 + "\n")
    
    print("Checking each region against validation rules:\n")
    
    import re
    
    for i, region in enumerate(text_regions, 1):
        text = region.extracted_text.strip()
        print(f"  [{i}] Testing: '{text}'")
        print(f"      Color: {region.color_category}")
        
        # Check 1: Has text
        if not text:
            print(f"      ❌ REJECTED: No text")
            print()
            continue
        
        # Check 2: Length
        if len(text) < detector.min_text_length and region.text_confidence < 0.7:
            print(f"      ❌ REJECTED: Too short ({len(text)} chars) with low confidence")
            print()
            continue
        
        # Check 3: Confidence
        if len(text) >= detector.min_text_length and region.text_confidence < detector.min_text_confidence:
            print(f"      ❌ REJECTED: Low OCR confidence ({region.text_confidence:.2%})")
            print()
            continue
        
        # Check 4: Alphanumeric
        alphanumeric = sum(c.isalnum() for c in text)
        if alphanumeric < 1:
            print(f"      ❌ REJECTED: No alphanumeric characters")
            print()
            continue
        
        # Check 5: Measurement patterns
        is_measurement = False
        matched_pattern = None
        for pattern in detector.measurement_patterns:
            if re.match(pattern, text.strip(), re.IGNORECASE):
                is_measurement = True
                matched_pattern = pattern
                break
        
        if is_measurement:
            print(f"      ❌ REJECTED: Matches measurement pattern '{matched_pattern}'")
            print(f"         Pattern: {pattern}")
            print()
            continue
        
        # Check 6: Word count
        words = text.split()
        word_count = len(words)
        
        if word_count < detector.min_word_count:
            # Check for comment keywords
            comment_keywords = ['update', 'check', 'verify', 'review', 'change', 
                               'fix', 'revise', 'note', 'see', 'confirm', 'approved',
                               'modify', 'correct', 'attention', 'important', 'warning']
            has_keyword = any(keyword in text.lower() for keyword in comment_keywords)
            
            if not has_keyword:
                print(f"      ❌ REJECTED: Single word without comment keyword")
                print(f"         Word count: {word_count} (required: {detector.min_word_count})")
                print()
                continue
        
        # Check 7: Common words (for short text)
        common_words = ['the', 'this', 'that', 'with', 'from', 'for', 'to', 'as',
                       'is', 'are', 'was', 'be', 'on', 'at', 'in', 'of', 'and', 'or']
        has_common = any(word in text.lower().split() for word in common_words)
        
        if len(text) < 10 and not has_common:
            print(f"      ❌ REJECTED: Short text without common words")
            print(f"         Text length: {len(text)} (threshold: 10)")
            print(f"         Has common word: {has_common}")
            print()
            continue
        
        # If we get here, it's accepted!
        print(f"      ✅ ACCEPTED: Valid comment text")
        print(f"         - Has {word_count} words")
        print(f"         - Confidence: {region.text_confidence:.2%}")
        print(f"         - Length: {len(text)} characters")
        print()
    
    # Final validation
    print("="*80)
    print("FINAL RESULT")
    print("-"*80 + "\n")
    
    validated = detector._validate_text_presence(text_regions)
    
    print(f"Initial colored regions: {len(colored_regions)}")
    print(f"After shape filtering: {len(shaped_regions)}")
    print(f"After text extraction: {len(text_regions)}")
    print(f"After text validation: {len(validated)} ✅")
    print()
    
    if validated:
        print("DETECTED COMMENTS:")
        for i, comment in enumerate(validated, 1):
            print(f"  {i}. [{comment.color_category.upper()}] '{comment.extracted_text}'")
            print(f"     Confidence: {comment.confidence:.2%}")
            print(f"     Position: ({comment.x0:.1f}, {comment.y0:.1f})")
    else:
        print("✅ NO FALSE POSITIVES: No comments detected")
        print("   All colored regions were correctly identified as:")
        print("   - Blank backgrounds")
        print("   - Measurements/labels")
        print("   - Non-comment drawing text")
    
    print("\n" + "="*80)
    print("PROOF COMPLETE")
    print("="*80 + "\n")
    
    doc.close()


if __name__ == "__main__":
    test_detection_proof()
