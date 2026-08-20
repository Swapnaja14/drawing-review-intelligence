# Hybrid OCR Setup Guide

## Overview
This project uses a **Hybrid OCR approach** combining two engines:
- **Tesseract** - Fast, accurate for printed text (specifications, labels, typed comments)
- **TrOCR** - Deep learning model for handwritten text (markups, redlines, annotations)

## Why Hybrid?

Engineering drawings typically contain **both**:
- ✅ **Printed text**: Title blocks, part numbers, specifications → Use **Tesseract**
- ✅ **Handwritten text**: Redlines, comments, markups → Use **TrOCR**

## Installation

### Prerequisites

1. **Tesseract OCR** (for printed text)
   - Download: https://github.com/UB-Mannheim/tesseract/wiki
   - Install to default location: `C:\Program Files\Tesseract-OCR`

2. **Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

This installs:
- `pytesseract` - Tesseract wrapper
- `transformers` - TrOCR models
- `torch` - PyTorch (already installed)
- `pdf2image`, `Pillow`, `PyMuPDF` - Image processing

### Verify Installation

```bash
python scripts/test_hybrid_ocr.py
```

## Quick Start

### 1. Basic Usage

```python
from src.services.hybrid_ocr_service import HybridOCRService

# Initialize
ocr = HybridOCRService(
    lang='eng',
    trocr_model='microsoft/trocr-base-handwritten',
    use_gpu=False
)

# Process PDF with auto engine selection
result = ocr.process_pdf(
    'drawing.pdf',
    output_dir='output',
    ocr_engine='auto'  # Intelligent selection
)
```

### 2. Engine Selection Modes

#### Auto Mode (Recommended)
Automatically chooses the best engine:
```python
result = ocr.process_pdf(pdf_path, ocr_engine='auto')
```
- Uses Tesseract first (fast)
- Falls back to TrOCR if confidence < 50%
- Best for mixed content

#### Tesseract Only (Fast)
For drawings with mostly printed text:
```python
result = ocr.process_pdf(pdf_path, ocr_engine='tesseract')
```
- ~1 second per page
- Best for clean, typed text

#### TrOCR Only (Accurate for Handwriting)
For heavily marked-up drawings:
```python
result = ocr.process_pdf(pdf_path, ocr_engine='trocr')
```
- ~3-5 seconds per page (CPU)
- Best for handwritten annotations

#### Both Engines (Comparison)
Run both and compare results:
```python
result = ocr.process_pdf(pdf_path, ocr_engine='both')
```
- Saves both outputs
- Good for evaluating accuracy

### 3. Process Specific Regions

Extract handwritten notes from title block:
```python
result = ocr.process_region(
    pdf_path='drawing.pdf',
    page_num=0,
    region=(2100, 2800, 600, 400),  # (x, y, width, height)
    ocr_engine='trocr'  # Use TrOCR for handwriting
)

print(result['text'])
```

## TrOCR Models

### Available Models

| Model | Size | Speed | Use Case |
|-------|------|-------|----------|
| `microsoft/trocr-small-printed` | 300MB | Fast | Printed text (backup) |
| `microsoft/trocr-base-printed` | 500MB | Medium | High-quality printed |
| `microsoft/trocr-small-handwritten` | 300MB | Fast | Handwritten (recommended) |
| `microsoft/trocr-base-handwritten` | 500MB | Slow | High-quality handwritten |
| `microsoft/trocr-large-handwritten` | 1.3GB | Very slow | Best accuracy |

### Model Selection

**For typical engineering drawings:**
```python
# Recommended: Balance speed and accuracy
ocr = HybridOCRService(
    trocr_model='microsoft/trocr-small-handwritten'
)

# For higher accuracy on difficult handwriting
ocr = HybridOCRService(
    trocr_model='microsoft/trocr-base-handwritten'
)
```

## Performance Comparison

### Speed (per page)

| Engine | CPU Time | GPU Time | Use Case |
|--------|----------|----------|----------|
| Tesseract | ~1s | N/A | Printed text |
| TrOCR (small) | ~3s | ~0.8s | Handwritten |
| TrOCR (base) | ~5s | ~1.2s | High accuracy |
| TrOCR (large) | ~10s | ~2s | Best quality |

### Accuracy

| Content Type | Tesseract | TrOCR |
|--------------|-----------|-------|
| Printed text | 95%+ | 90%+ |
| Handwritten (clean) | 50-70% | 85-95% |
| Handwritten (messy) | 20-40% | 70-85% |
| Mixed content | 70-80% | 80-90% |

## Usage Examples

### Example 1: Process Drawing with Auto Detection

```python
from src.services.hybrid_ocr_service import HybridOCRService

ocr = HybridOCRService()

result = ocr.process_pdf(
    'dataset/raw_drawings/Electrical Engineering/drawing.pdf',
    output_dir='dataset/extracted_text',
    dpi=300,
    ocr_engine='auto'
)

# Check which engine was used
for page in result['pages']:
    print(f"Page {page['page_number']}: {page['engines_used']}")
```

### Example 2: Extract Handwritten Comments Only

```python
# Use TrOCR for handwritten markup region
comment_region = (1800, 2600, 800, 600)  # Bottom-right area

result = ocr.process_region(
    pdf_path='drawing.pdf',
    page_num=0,
    region=comment_region,
    ocr_engine='trocr'
)

print("Handwritten comments:", result['text'])
```

### Example 3: Batch Process with Both Engines

```python
results = ocr.batch_process_drawings(
    input_dir='dataset/raw_drawings/Electrical Engineering',
    output_dir='dataset/extracted_text',
    dpi=300,
    ocr_engine='both'  # Compare both engines
)

# Review results
for r in results:
    if 'error' not in r:
        print(f"{r['file_name']}: Success")
```

### Example 4: Process Drawings by Type

```python
# Printed drawings (specifications, schematics) - fast
printed_results = ocr.batch_process_drawings(
    input_dir='dataset/raw_drawings/specifications',
    output_dir='dataset/extracted_text/specifications',
    ocr_engine='tesseract'
)

# Marked-up drawings (redlines, comments) - accurate
markup_results = ocr.batch_process_drawings(
    input_dir='dataset/raw_drawings/markups',
    output_dir='dataset/extracted_text/markups',
    ocr_engine='trocr'
)
```

## Configuration Tips

### 1. Memory Management

**Low memory (<4GB available):**
```python
# Use small model and lower DPI
ocr = HybridOCRService(
    trocr_model='microsoft/trocr-small-handwritten'
)
result = ocr.process_pdf(pdf_path, dpi=200)
```

**Normal memory (4-8GB):**
```python
# Use base model
ocr = HybridOCRService(
    trocr_model='microsoft/trocr-base-handwritten'
)
result = ocr.process_pdf(pdf_path, dpi=300)
```

### 2. Speed Optimization

**For large batches:**
```python
# Process printed text first (fast)
ocr_tesseract = HybridOCRService()
results = ocr_tesseract.batch_process_drawings(
    input_dir='drawings',
    output_dir='output',
    ocr_engine='tesseract'
)

# Then only process low-confidence files with TrOCR
low_conf_files = [r for r in results if r['pages'][0]['avg_confidence'] < 0.5]
```

### 3. GPU Acceleration

If you have NVIDIA GPU with CUDA:
```python
ocr = HybridOCRService(
    trocr_model='microsoft/trocr-base-handwritten',
    use_gpu=True  # 3-5x faster
)
```

## Output Format

### File Structure
```
dataset/extracted_text/
├── drawing1_hybrid_ocr.txt
├── drawing2_hybrid_ocr.txt
└── ...
```

### Output File Format
```
File: drawing1.pdf
Total Pages: 1
OCR Engine: auto
================================================================================

Page 1
Engines: tesseract
Confidence: 87.45%
--------------------------------------------------------------------------------
[Extracted text from Tesseract]

```

## Troubleshooting

### Issue: TrOCR model download fails
**Solution**: Check internet connection, or manually download:
```python
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

# This will download models to cache
processor = TrOCRProcessor.from_pretrained('microsoft/trocr-small-handwritten')
model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-small-handwritten')
```

### Issue: Out of memory error with TrOCR
**Solutions**:
1. Use smaller model: `trocr-small-handwritten`
2. Lower DPI: `dpi=200` or `dpi=150`
3. Close other applications
4. Process files one at a time

### Issue: TrOCR too slow
**Solutions**:
1. Use GPU: `use_gpu=True` (requires CUDA)
2. Use smaller model: `trocr-small-handwritten`
3. Lower DPI: `dpi=200`
4. Use auto mode to only use TrOCR when needed

### Issue: Poor accuracy on handwriting
**Solutions**:
1. Increase DPI: `dpi=400`
2. Use larger model: `trocr-base-handwritten`
3. Preprocess image (increase contrast)
4. Extract smaller regions instead of full page

## Best Practices

### 1. Start with Auto Mode
```python
result = ocr.process_pdf(pdf_path, ocr_engine='auto')
```
- Fastest for most drawings
- Automatically adapts to content

### 2. Use Specific Engines for Known Content
```python
# Clean CAD drawings with typed text
ocr.process_pdf(cad_drawing, ocr_engine='tesseract')

# Field markup with handwritten notes
ocr.process_pdf(markup_drawing, ocr_engine='trocr')
```

### 3. Process Regions for Handwritten Content
```python
# Extract just the comment area
comments = ocr.process_region(
    pdf_path,
    region=comment_area,
    ocr_engine='trocr'
)
```

### 4. Use Both Mode for Evaluation
```python
# Compare results to choose best engine
result = ocr.process_pdf(pdf_path, ocr_engine='both')
# Review outputs and pick best approach
```

## Next Steps

1. **Test the setup**:
   ```bash
   python scripts/test_hybrid_ocr.py
   ```

2. **Process sample drawings**:
   ```bash
   python scripts/run_hybrid_ocr.py
   ```

3. **Customize for your workflow**:
   - Adjust engine selection based on drawing types
   - Configure DPI for quality vs speed
   - Set up batch processing scripts

## Resources

- [Tesseract Documentation](https://github.com/tesseract-ocr/tesseract)
- [TrOCR Paper](https://arxiv.org/abs/2109.10282)
- [HuggingFace Transformers](https://huggingface.co/docs/transformers)
- [TrOCR Models](https://huggingface.co/models?search=trocr)
