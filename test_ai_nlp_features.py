"""
test_ai_nlp_features.py
Interactive & automated verification tool for AI Text Cleaning, Engineering Dictionary,
Spell Correction, Multi-Action Segmentation, and Reviewer Attribution.
"""

import sys
from pathlib import Path

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.text_cleaning_service import TextCleaningService
from src.services.classification_service import ClassificationService


def test_custom_samples():
    cleaner = TextCleaningService(expand_acronyms=False)
    classifier = ClassificationService()

    sample_cases = [
        {
            "name": "1. OCR Typos & Misspellings Recovery",
            "input": "NUVA FEEDEER TAGS ARE CORRECT IF SYSTEMS REVISES P&ID M-009 -JDM",
        },
        {
            "name": "2. Preserving Dimensions, Schedules & Part Tags",
            "input": "CL EL 345'-11 3/4\" TYPICAL FOR 8\" SCH 40 PIPE (174005-S12-04-P08) -JDM",
        },
        {
            "name": "3. Multi-Action Comment Segmentation (Punch-list)",
            "input": "1. FOR GENERAL NOTES SEE C-54718-31-002 2. BILL OF MATERIALS REVISE QUANTITY 3. LASER SCANNING VERIFY DATES -BEK",
        },
        {
            "name": "4. Critical Priority & Action Verb Detection",
            "input": "INCORRECT FLANGE RATING! DO NOT PROCEED WITH INSTALLATION -JCM",
        },
        {
            "name": "5. OCR Scan Noise Stripping",
            "input": "\\\\ : !!!! RECIEVER B IS OPTIONAL FOR LASER SCANNING _~ TYPICAL -JJD",
        },
        {
            "name": "6. Engineering Acronym Expansion (with expand_acronyms=True)",
            "input": "CHECK P&ID AND VERIFY HSS WELDING IN BOM",
        },
    ]

    print("=" * 80)
    print(" [AI TEXT INTELLIGENCE & ENGINEERING NLP TEST RUNNER]")
    print("=" * 80)

    for case in sample_cases:
        print(f"\n[TEST CASE]: {case['name']}")
        print(f"   Raw Input:      {case['input']}")
        
        # Test default or expanded
        if "expand_acronyms" in case['name']:
            exp_cleaner = TextCleaningService(expand_acronyms=True)
            res = exp_cleaner.clean_text(case['input'])
        else:
            res = cleaner.clean_text(case['input'])
            
        class_res = classifier.classify_comment(res.cleaned_text)

        print(f"   Cleaned Text:   {res.cleaned_text}")
        print(f"   Reviewer:       {res.reviewer_initials or 'None'}")
        print(f"   Priority:       {res.priority_level}")
        print(f"   Action Verb:    {res.action_verb or 'None'}")
        print(f"   Category:       {class_res.primary_category.category_name} (Confidence: {class_res.primary_category.confidence:.2f})")
        print(f"   Sub-Actions:    {res.sub_actions}")
        print(f"   Domain Terms:   {res.engineering_terms_found}")
        if res.corrections:
            corrs = [f"{c.original} -> {c.corrected} ({c.correction_type})" for c in res.corrections]
            print(f"   Corrections:    {', '.join(corrs)}")
        print("-" * 80)


def interactive_mode():
    cleaner = TextCleaningService(expand_acronyms=False)
    classifier = ClassificationService()

    print("\n[INFO] Type your own comment text below to test in real-time (or press Ctrl+C / Enter empty line to exit):")
    while True:
        try:
            user_input = input("\nEnter comment: ").strip()
            if not user_input:
                break
            res = cleaner.clean_text(user_input)
            class_res = classifier.classify_comment(res.cleaned_text)

            print(f"   Cleaned:     {res.cleaned_text}")
            print(f"   Reviewer:    {res.reviewer_initials}")
            print(f"   Priority:    {res.priority_level}")
            print(f"   Action Verb: {res.action_verb}")
            print(f"   Category:    {class_res.primary_category.category_name} ({class_res.primary_category.confidence:.2f})")
            print(f"   Sub-Actions: {res.sub_actions}")
            if res.corrections:
                print(f"   Corrections: {[f'{c.original} -> {c.corrected}' for c in res.corrections]}")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break


if __name__ == "__main__":
    test_custom_samples()
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_mode()
