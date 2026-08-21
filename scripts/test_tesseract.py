"""
Test script to verify Tesseract installation
"""
import sys
from pathlib import Path

print("="*80)
print("Tesseract OCR Installation Test")
print("="*80)

# Test 1: Check pytesseract import
print("\n1. Testing pytesseract import...")
try:
    import pytesseract
    print("   ✓ pytesseract imported successfully")
except ImportError as e:
    print(f"   ✗ Failed to import pytesseract: {e}")
    print("   Run: pip install pytesseract")
    sys.exit(1)

# Test 2: Check Tesseract installation
print("\n2. Checking Tesseract OCR installation...")
try:
    version = pytesseract.get_tesseract_version()
    print(f"   ✓ Tesseract OCR found (version {version})")
except Exception as e:
    print(f"   ✗ Tesseract not found: {e}")
    print("\n   Please install Tesseract OCR:")
    print("   Windows: https://github.com/UB-Mannheim/tesseract/wiki")
    print("   After installation, either:")
    print("   - Add to PATH, or")
    print("   - Specify path in code:")
    print("     pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'")
    sys.exit(1)

# Test 3: Check other dependencies
print("\n3. Checking other dependencies...")
dependencies = {
    'PIL': 'Pillow',
    'fitz': 'PyMuPDF',
    'pdf2image': 'pdf2image'
}

missing = []
for module, package in dependencies.items():
    try:
        __import__(module)
        print(f"   ✓ {package}")
    except ImportError:
        print(f"   ✗ {package} - Not installed")
        missing.append(package)

if missing:
    print(f"\n   Install missing packages: pip install {' '.join(missing)}")
    sys.exit(1)

# Test 4: Test OCR Service
print("\n4. Testing OCR Service...")
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.services.ocr_service import OCRService
    
    ocr_service = OCRService(lang='eng')
    print("   ✓ OCR Service initialized successfully")
except Exception as e:
    print(f"   ✗ Failed to initialize OCR Service: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Test on sample PDF (if available)
print("\n5. Looking for sample PDF to test...")
test_dirs = [
    'dataset/raw_drawings/Electrical Engineering',
    'dataset/raw_drawings/GPD',
    'dataset/raw_drawings/Pipe Support Engineering'
]

test_pdf = None
for test_dir in test_dirs:
    pdf_dir = Path(test_dir)
    if pdf_dir.exists():
        pdfs = list(pdf_dir.glob('*.pdf'))
        if pdfs:
            test_pdf = pdfs[0]
            break

if not test_pdf:
    print("   ⚠ No sample PDF found")
    print("   Skipping OCR test")
    print("\n" + "="*80)
    print("✅ Tesseract is installed and ready to use!")
    print("="*80)
    print("\nNext steps:")
    print("  1. Place PDF files in dataset/raw_drawings/")
    print("  2. Run: python scripts/run_tesseract.py")
    print("  3. Check results in dataset/extracted_text/")
    sys.exit(0)

print(f"   ✓ Found sample PDF: {test_pdf.name}")

# Test 6: Run OCR on sample
print("\n6. Testing OCR on sample PDF...")
print("   This may take a moment...")
try:
    from PIL import Image
    import io
    import fitz
    
    # Open PDF and convert first page
    doc = fitz.open(test_pdf)
    page = doc[0]
    
    # Convert to image (low DPI for quick test)
    zoom = 150 / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    
    # Convert to PIL Image
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))
    
    # Run OCR
    text = pytesseract.image_to_string(img, lang='eng')
    
    doc.close()
    
    if text.strip():
        print(f"   ✓ OCR successful!")
        print(f"   - Extracted {len(text)} characters")
        print(f"\n   First 200 characters:")
        print(f"   {'-'*76}")
        print(f"   {text[:200]}...")
    else:
        print("   ⚠ OCR returned no text")
        print("   This could mean:")
        print("   - The PDF page is blank")
        print("   - The PDF contains only vector graphics")
        print("   - Try with a different PDF")
    
except Exception as e:
    print(f"   ✗ OCR test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Success!
print("\n" + "="*80)
print("✅ SUCCESS: Tesseract OCR is working correctly!")
print("="*80)
print("\nYou can now:")
print("  1. Run: python scripts/run_tesseract.py")
print("  2. Process your drawings in batch")
print("  3. Check docs/TESSERACT_SETUP.md for more options")
