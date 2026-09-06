"""
Test script for image preprocessing service
Demonstrates all preprocessing capabilities with visual examples
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np
from src.services.image_preprocessing_service import ImagePreprocessingService


def print_header(title):
    """Print formatted header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def test_pdf_conversion():
    """Test PDF to image conversion"""
    print_header("TEST 1: PDF to Image Conversion")
    
    preprocessor = ImagePreprocessingService()
    
    # Test PDF
    pdf_path = "dataset/raw_drawings/Electrical Engineering/5-1307-137_F_RJY.pdf"
    
    if not Path(pdf_path).exists():
        print(f"❌ PDF not found: {pdf_path}")
        print("Please provide a valid PDF path")
        return
    
    print(f"Converting PDF: {pdf_path}")
    print(f"DPI: 300")
    
    images = preprocessor.pdf_to_images(pdf_path, dpi=300)
    
    print(f"\n✅ Converted {len(images)} pages")
    for i, img in enumerate(images, 1):
        print(f"  Page {i}: Shape {img.shape}, Dtype {img.dtype}")


def test_individual_steps():
    """Test each preprocessing step individually"""
    print_header("TEST 2: Individual Preprocessing Steps")
    
    preprocessor = ImagePreprocessingService()
    
    # Load test image
    pdf_path = "dataset/raw_drawings/Electrical Engineering/5-1307-137_F_RJY.pdf"
    
    if not Path(pdf_path).exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    images = preprocessor.pdf_to_images(pdf_path, dpi=300)
    original = images[0]
    
    print(f"Original image shape: {original.shape}\n")
    
    # Test each step
    steps = [
        ('Grayscale', lambda: preprocessor.grayscale_conversion(original)),
        ('Denoise (fastNlMeans)', lambda: preprocessor.denoise(original, method='fastNlMeans', strength=10)),
        ('Denoise (bilateral)', lambda: preprocessor.denoise(original, method='bilateral', strength=10)),
        ('Denoise (gaussian)', lambda: preprocessor.denoise(original, method='gaussian', strength=10)),
        ('Denoise (median)', lambda: preprocessor.denoise(original, method='median')),
        ('Deskew', lambda: preprocessor.deskew(original)[0]),
        ('Contrast (CLAHE)', lambda: preprocessor.enhance_contrast(original, method='clahe')),
        ('Contrast (Histogram Eq)', lambda: preprocessor.enhance_contrast(original, method='histogram_equalization')),
        ('Binarize (Otsu)', lambda: preprocessor.binarize(original, method='otsu')),
        ('Binarize (Adaptive)', lambda: preprocessor.binarize(original, method='adaptive')),
        ('Morphology (Close)', lambda: preprocessor.morphological_operations(
            preprocessor.binarize(original, method='otsu'), operation='close', kernel_size=3
        )),
    ]
    
    for step_name, step_func in steps:
        try:
            result = step_func()
            print(f"✅ {step_name:30s} → Shape: {result.shape}")
        except Exception as e:
            print(f"❌ {step_name:30s} → Error: {e}")


def test_pipelines():
    """Test predefined preprocessing pipelines"""
    print_header("TEST 3: Preprocessing Pipelines")
    
    preprocessor = ImagePreprocessingService()
    
    # Load test image
    pdf_path = "dataset/raw_drawings/Electrical Engineering/5-1307-137_F_RJY.pdf"
    
    if not Path(pdf_path).exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    images = preprocessor.pdf_to_images(pdf_path, dpi=300)
    original = images[0]
    
    pipelines = ['standard', 'aggressive', 'light', 'handwriting']
    
    for pipeline_name in pipelines:
        print(f"\nTesting pipeline: {pipeline_name.upper()}")
        print("-" * 60)
        
        try:
            preprocessed, metadata = preprocessor.preprocess_for_ocr(original, pipeline=pipeline_name)
            
            print(f"  ✅ Success")
            print(f"  Original shape: {metadata['original_shape']}")
            print(f"  Final shape: {metadata['final_shape']}")
            print(f"  Deskew angle: {metadata['deskew_angle']:.2f}°")
            print(f"  Steps applied: {', '.join(metadata['steps_applied'])}")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")


def test_custom_pipeline():
    """Test custom preprocessing pipeline"""
    print_header("TEST 4: Custom Pipeline")
    
    preprocessor = ImagePreprocessingService()
    
    # Load test image
    pdf_path = "dataset/raw_drawings/Electrical Engineering/5-1307-137_F_RJY.pdf"
    
    if not Path(pdf_path).exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    images = preprocessor.pdf_to_images(pdf_path, dpi=300)
    original = images[0]
    
    # Define custom pipeline
    custom_steps = [
        {'step': 'grayscale'},
        {'step': 'denoise', 'method': 'bilateral', 'strength': 8},
        {'step': 'deskew'},
        {'step': 'enhance_contrast', 'method': 'clahe', 'clip_limit': 2.5},
        {'step': 'binarize', 'method': 'adaptive'},
        {'step': 'morphology', 'operation': 'open', 'kernel_size': 2},
    ]
    
    print("Custom pipeline steps:")
    for step in custom_steps:
        print(f"  - {step}")
    
    try:
        preprocessed, metadata = preprocessor.preprocess_for_ocr(original, custom_steps=custom_steps)
        
        print(f"\n✅ Custom pipeline successful")
        print(f"  Original shape: {metadata['original_shape']}")
        print(f"  Final shape: {metadata['final_shape']}")
        print(f"  Deskew angle: {metadata['deskew_angle']:.2f}°")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


def test_full_pdf_preprocessing():
    """Test complete PDF preprocessing with file saving"""
    print_header("TEST 5: Full PDF Preprocessing")
    
    preprocessor = ImagePreprocessingService()
    
    pdf_path = "dataset/raw_drawings/Electrical Engineering/5-1307-137_F_RJY.pdf"
    output_dir = "dataset/preprocessed_images/test_output"
    
    if not Path(pdf_path).exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"Input PDF: {pdf_path}")
    print(f"Output directory: {output_dir}")
    print(f"Pipeline: standard")
    print(f"DPI: 300")
    
    try:
        results = preprocessor.preprocess_pdf(
            pdf_path=pdf_path,
            output_dir=output_dir,
            dpi=300,
            pipeline='standard',
            save_images=True
        )
        
        print(f"\n✅ Successfully preprocessed {len(results)} pages")
        
        for img, metadata in results:
            print(f"\nPage {metadata['page_number']}:")
            print(f"  Original: {metadata['original_shape']}")
            print(f"  Final: {metadata['final_shape']}")
            print(f"  Deskew: {metadata['deskew_angle']:.2f}°")
            print(f"  Steps: {', '.join(metadata['steps_applied'])}")
        
        print(f"\n📁 Preprocessed images saved to: {output_dir}/")
        
        # List saved files
        output_path = Path(output_dir)
        if output_path.exists():
            saved_files = list(output_path.glob("*.png"))
            print(f"   {len(saved_files)} files saved:")
            for f in saved_files:
                print(f"     - {f.name}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def test_deskewing_accuracy():
    """Test deskewing with angle detection"""
    print_header("TEST 6: Deskewing Accuracy")
    
    preprocessor = ImagePreprocessingService()
    
    pdf_path = "dataset/raw_drawings/Electrical Engineering/5-1307-137_F_RJY.pdf"
    
    if not Path(pdf_path).exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    images = preprocessor.pdf_to_images(pdf_path, dpi=300)
    original = images[0]
    
    print("Testing deskewing...")
    
    try:
        deskewed, angle = preprocessor.deskew(original)
        
        print(f"\n✅ Deskewing complete")
        print(f"  Detected angle: {angle:.2f}°")
        print(f"  Original shape: {original.shape}")
        print(f"  Deskewed shape: {deskewed.shape}")
        
        if abs(angle) < 0.5:
            print(f"  ℹ️  Image was already straight (angle < 0.5°)")
        else:
            print(f"  ✅ Image corrected by {abs(angle):.2f}°")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


def test_batch_preprocessing():
    """Test batch preprocessing of multiple PDFs"""
    print_header("TEST 7: Batch Preprocessing (Multiple PDFs)")
    
    preprocessor = ImagePreprocessingService()
    
    input_dir = Path("dataset/raw_drawings/Electrical Engineering")
    output_dir = "dataset/preprocessed_images/batch_output"
    
    if not input_dir.exists():
        print(f"❌ Input directory not found: {input_dir}")
        return
    
    # Get first 3 PDFs for testing
    pdf_files = list(input_dir.glob("*.pdf"))[:3]
    
    if not pdf_files:
        print(f"❌ No PDF files found in: {input_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDFs to process:")
    for pdf in pdf_files:
        print(f"  - {pdf.name}")
    
    print(f"\nOutput directory: {output_dir}")
    print(f"Pipeline: standard\n")
    
    results_summary = []
    
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")
        print("-" * 60)
        
        try:
            results = preprocessor.preprocess_pdf(
                pdf_path=str(pdf_path),
                output_dir=output_dir,
                dpi=300,
                pipeline='standard',
                save_images=True
            )
            
            print(f"  ✅ Success: {len(results)} pages preprocessed")
            
            results_summary.append({
                'file': pdf_path.name,
                'status': 'success',
                'pages': len(results)
            })
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results_summary.append({
                'file': pdf_path.name,
                'status': 'failed',
                'error': str(e)
            })
    
    # Summary
    print(f"\n{'='*80}")
    print("BATCH PREPROCESSING SUMMARY")
    print(f"{'='*80}\n")
    
    successful = [r for r in results_summary if r['status'] == 'success']
    failed = [r for r in results_summary if r['status'] == 'failed']
    
    print(f"Total files: {len(pdf_files)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if successful:
        total_pages = sum(r['pages'] for r in successful)
        print(f"Total pages processed: {total_pages}")
    
    if failed:
        print("\nFailed files:")
        for r in failed:
            print(f"  ❌ {r['file']}: {r['error']}")


def run_all_tests():
    """Run all tests"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "IMAGE PREPROCESSING SERVICE TESTS" + " " * 25 + "║")
    print("╚" + "═" * 78 + "╝")
    
    tests = [
        ("PDF to Image Conversion", test_pdf_conversion),
        ("Individual Preprocessing Steps", test_individual_steps),
        ("Preprocessing Pipelines", test_pipelines),
        ("Custom Pipeline", test_custom_pipeline),
        ("Full PDF Preprocessing", test_full_pdf_preprocessing),
        ("Deskewing Accuracy", test_deskewing_accuracy),
        ("Batch Preprocessing", test_batch_preprocessing),
    ]
    
    for test_name, test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"\n❌ Test failed: {test_name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 30 + "TESTS COMPLETE" + " " * 34 + "║")
    print("╚" + "═" * 78 + "╝")
    print()


if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(message)s'
    )
    
    # Check if specific test requested
    if len(sys.argv) > 1:
        test_num = sys.argv[1]
        
        tests = {
            '1': test_pdf_conversion,
            '2': test_individual_steps,
            '3': test_pipelines,
            '4': test_custom_pipeline,
            '5': test_full_pdf_preprocessing,
            '6': test_deskewing_accuracy,
            '7': test_batch_preprocessing,
        }
        
        if test_num in tests:
            tests[test_num]()
        else:
            print(f"Unknown test: {test_num}")
            print(f"Available tests: {', '.join(tests.keys())}")
    else:
        # Run all tests
        run_all_tests()
