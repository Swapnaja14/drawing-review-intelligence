"""
Image Preprocessing Service for Engineering Drawings
Enhances image quality before OCR to improve text extraction accuracy

Features:
- PDF to image conversion
- Deskewing (straighten rotated images)
- Noise removal (denoising)
- Contrast enhancement
- Binarization (black & white conversion)
- Border removal
- Adaptive thresholding
- Morphological operations
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import cv2
from PIL import Image
import pymupdf as fitz
import io

# Increase PIL image size limit for large engineering drawings
# Default is ~89 million pixels, we need more for high-DPI scans
Image.MAX_IMAGE_PIXELS = 150_000_000  # Allow up to 150 million pixels

logger = logging.getLogger(__name__)


class ImagePreprocessingService:
    """Service for preprocessing images before OCR"""
    
    def __init__(self):
        """Initialize preprocessing service"""
        logger.info("Image Preprocessing Service initialized")
    
    # ========================
    # PDF to Image Conversion
    # ========================
    
    def pdf_to_images(
        self,
        pdf_path: str,
        dpi: int = 300,
        output_format: str = 'numpy'
    ) -> List[Union[np.ndarray, Image.Image]]:
        """
        Convert PDF pages to images
        
        Args:
            pdf_path: Path to PDF file
            dpi: DPI for rendering (higher = better quality, 300 recommended)
            output_format: 'numpy' for cv2 arrays, 'pil' for PIL Images
        
        Returns:
            List of images (one per page)
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        logger.info(f"Converting PDF to images: {pdf_path.name} at {dpi} DPI")
        
        images = []
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Convert page to image
            zoom = dpi / 72  # PDF default is 72 DPI
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            pil_img = Image.open(io.BytesIO(img_data))
            
            # Convert to requested format
            if output_format == 'numpy':
                # Convert PIL to OpenCV format (BGR)
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                images.append(img)
            else:
                images.append(pil_img)
            
            logger.debug(f"Converted page {page_num + 1}/{len(doc)}")
        
        doc.close()
        logger.info(f"Converted {len(images)} pages to images")
        return images
    
    # ========================
    # Core Preprocessing Steps
    # ========================
    
    def grayscale_conversion(self, img: np.ndarray) -> np.ndarray:
        """
        Convert image to grayscale
        
        Args:
            img: Input image (BGR or RGB)
        
        Returns:
            Grayscale image
        """
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            logger.debug("Converted to grayscale")
            return gray
        return img
    
    def denoise(
        self,
        img: np.ndarray,
        method: str = 'fastNlMeans',
        strength: int = 10
    ) -> np.ndarray:
        """
        Remove noise from image
        
        Args:
            img: Input image
            method: Denoising method ('fastNlMeans', 'bilateral', 'gaussian', 'median')
            strength: Denoising strength (higher = more denoising)
        
        Returns:
            Denoised image
        """
        logger.debug(f"Applying {method} denoising with strength {strength}")
        
        if method == 'fastNlMeans':
            # Non-local means denoising (best quality, slower)
            if len(img.shape) == 3:
                denoised = cv2.fastNlMeansDenoisingColored(img, None, strength, strength, 7, 21)
            else:
                denoised = cv2.fastNlMeansDenoising(img, None, strength, 7, 21)
        
        elif method == 'bilateral':
            # Bilateral filter (preserves edges)
            denoised = cv2.bilateralFilter(img, 9, strength * 2, strength * 2)
        
        elif method == 'gaussian':
            # Gaussian blur (fast, simple)
            denoised = cv2.GaussianBlur(img, (5, 5), strength / 10.0)
        
        elif method == 'median':
            # Median filter (good for salt-and-pepper noise)
            denoised = cv2.medianBlur(img, 5)
        
        else:
            raise ValueError(f"Unknown denoising method: {method}")
        
        return denoised
    
    def deskew(self, img: np.ndarray, min_angle: float = -10, max_angle: float = 10) -> Tuple[np.ndarray, float]:
        """
        Detect and correct image skew (rotation)
        
        Args:
            img: Input image
            min_angle: Minimum angle to check (degrees)
            max_angle: Maximum angle to check (degrees)
        
        Returns:
            Tuple of (deskewed image, detected angle)
        """
        logger.debug("Detecting image skew...")
        
        # Convert to grayscale if needed
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        # Detect edges
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Detect lines using Hough transform
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        
        if lines is None:
            logger.warning("No lines detected for deskewing")
            return img, 0.0
        
        # Calculate angles
        angles = []
        for rho, theta in lines[:, 0]:
            angle = np.degrees(theta) - 90
            if min_angle <= angle <= max_angle:
                angles.append(angle)
        
        if not angles:
            logger.warning("No valid angles found for deskewing")
            return img, 0.0
        
        # Use median angle (more robust than mean)
        detected_angle = np.median(angles)
        
        if abs(detected_angle) < 0.5:
            logger.debug(f"Image is already straight (angle: {detected_angle:.2f}°)")
            return img, detected_angle
        
        # Rotate image
        logger.info(f"Deskewing image by {detected_angle:.2f} degrees")
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, detected_angle, 1.0)
        
        # Calculate new image size to avoid cropping
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))
        
        # Adjust rotation matrix
        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]
        
        # Apply rotation with white background
        deskewed = cv2.warpAffine(img, M, (new_w, new_h), 
                                   flags=cv2.INTER_CUBIC,
                                   borderMode=cv2.BORDER_CONSTANT,
                                   borderValue=(255, 255, 255))
        
        return deskewed, detected_angle
    
    def enhance_contrast(
        self,
        img: np.ndarray,
        method: str = 'clahe',
        clip_limit: float = 2.0
    ) -> np.ndarray:
        """
        Enhance image contrast
        
        Args:
            img: Input image
            method: Enhancement method ('clahe', 'histogram_equalization', 'adaptive')
            clip_limit: Contrast limiting threshold (for CLAHE)
        
        Returns:
            Contrast-enhanced image
        """
        logger.debug(f"Enhancing contrast using {method}")
        
        # Convert to grayscale if needed
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        if method == 'clahe':
            # CLAHE (Contrast Limited Adaptive Histogram Equalization)
            # Best for engineering drawings with varying lighting
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
        
        elif method == 'histogram_equalization':
            # Standard histogram equalization
            enhanced = cv2.equalizeHist(gray)
        
        elif method == 'adaptive':
            # Adaptive histogram equalization
            enhanced = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
        
        else:
            raise ValueError(f"Unknown contrast method: {method}")
        
        return enhanced
    
    def binarize(
        self,
        img: np.ndarray,
        method: str = 'otsu',
        threshold: int = 127
    ) -> np.ndarray:
        """
        Convert image to binary (black and white)
        
        Args:
            img: Input image
            method: Binarization method ('otsu', 'adaptive', 'simple')
            threshold: Threshold value (for simple method)
        
        Returns:
            Binary image
        """
        logger.debug(f"Binarizing image using {method} method")
        
        # Convert to grayscale if needed
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        if method == 'otsu':
            # Otsu's method (automatic threshold calculation)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        elif method == 'adaptive':
            # Adaptive thresholding (best for varying lighting)
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
        
        elif method == 'simple':
            # Simple threshold
            _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
        
        else:
            raise ValueError(f"Unknown binarization method: {method}")
        
        return binary
    
    def remove_borders(
        self,
        img: np.ndarray,
        border_size: int = 10
    ) -> np.ndarray:
        """
        Remove borders from image (useful for scanned drawings)
        
        Args:
            img: Input image
            border_size: Border size to remove in pixels
        
        Returns:
            Image with borders removed
        """
        logger.debug(f"Removing {border_size}px borders")
        
        h, w = img.shape[:2]
        cropped = img[border_size:h-border_size, border_size:w-border_size]
        return cropped
    
    def morphological_operations(
        self,
        img: np.ndarray,
        operation: str = 'close',
        kernel_size: int = 3
    ) -> np.ndarray:
        """
        Apply morphological operations to clean up image
        
        Args:
            img: Input image (binary)
            operation: Operation type ('close', 'open', 'dilate', 'erode')
            kernel_size: Size of morphological kernel
        
        Returns:
            Processed image
        """
        logger.debug(f"Applying {operation} morphology with kernel size {kernel_size}")
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
        
        if operation == 'close':
            # Closing (dilation followed by erosion) - fills small holes
            result = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)
        
        elif operation == 'open':
            # Opening (erosion followed by dilation) - removes noise
            result = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)
        
        elif operation == 'dilate':
            # Dilation - makes text thicker
            result = cv2.dilate(img, kernel, iterations=1)
        
        elif operation == 'erode':
            # Erosion - makes text thinner
            result = cv2.erode(img, kernel, iterations=1)
        
        else:
            raise ValueError(f"Unknown morphological operation: {operation}")
        
        return result
    
    def resize_for_ocr(
        self,
        img: np.ndarray,
        target_height: int = 2000,
        maintain_aspect: bool = True
    ) -> np.ndarray:
        """
        Resize image to optimal size for OCR
        
        Args:
            img: Input image
            target_height: Target height in pixels (recommended: 1500-3000)
            maintain_aspect: Whether to maintain aspect ratio
        
        Returns:
            Resized image
        """
        h, w = img.shape[:2]
        
        if h == target_height:
            return img
        
        if maintain_aspect:
            ratio = target_height / h
            new_w = int(w * ratio)
            new_h = target_height
        else:
            new_w = w
            new_h = target_height
        
        logger.debug(f"Resizing image from {w}x{h} to {new_w}x{new_h}")
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        return resized
    
    # ========================
    # Complete Pipeline
    # ========================
    
    def preprocess_for_ocr(
        self,
        img: np.ndarray,
        pipeline: str = 'standard',
        custom_steps: Optional[List[Dict]] = None
    ) -> Tuple[np.ndarray, Dict]:
        """
        Apply complete preprocessing pipeline
        
        Args:
            img: Input image
            pipeline: Predefined pipeline ('standard', 'aggressive', 'light', 'handwriting')
            custom_steps: Custom pipeline steps (overrides pipeline parameter)
        
        Returns:
            Tuple of (preprocessed image, metadata dict)
        """
        logger.info(f"Starting preprocessing pipeline: {pipeline}")
        
        metadata = {
            'original_shape': img.shape,
            'steps_applied': [],
            'deskew_angle': 0.0
        }
        
        # Define predefined pipelines
        pipelines = {
            'standard': [
                {'step': 'grayscale'},
                {'step': 'denoise', 'method': 'fastNlMeans', 'strength': 10},
                {'step': 'deskew'},
                {'step': 'enhance_contrast', 'method': 'clahe', 'clip_limit': 2.0},
                {'step': 'binarize', 'method': 'otsu'},
                {'step': 'morphology', 'operation': 'close', 'kernel_size': 2},
            ],
            'aggressive': [
                {'step': 'grayscale'},
                {'step': 'denoise', 'method': 'fastNlMeans', 'strength': 15},
                {'step': 'deskew'},
                {'step': 'enhance_contrast', 'method': 'clahe', 'clip_limit': 3.0},
                {'step': 'binarize', 'method': 'adaptive'},
                {'step': 'morphology', 'operation': 'open', 'kernel_size': 2},
                {'step': 'morphology', 'operation': 'close', 'kernel_size': 3},
            ],
            'light': [
                {'step': 'grayscale'},
                {'step': 'denoise', 'method': 'bilateral', 'strength': 5},
                {'step': 'enhance_contrast', 'method': 'clahe', 'clip_limit': 1.5},
            ],
            'handwriting': [
                {'step': 'grayscale'},
                {'step': 'denoise', 'method': 'bilateral', 'strength': 8},
                {'step': 'deskew'},
                {'step': 'enhance_contrast', 'method': 'clahe', 'clip_limit': 2.5},
                {'step': 'binarize', 'method': 'adaptive'},
            ]
        }
        
        # Select steps
        if custom_steps:
            steps = custom_steps
        elif pipeline in pipelines:
            steps = pipelines[pipeline]
        else:
            raise ValueError(f"Unknown pipeline: {pipeline}")
        
        # Apply each step
        processed = img.copy()
        
        for step_config in steps:
            step_name = step_config.pop('step')
            metadata['steps_applied'].append(step_name)
            
            if step_name == 'grayscale':
                processed = self.grayscale_conversion(processed)
            
            elif step_name == 'denoise':
                processed = self.denoise(processed, **step_config)
            
            elif step_name == 'deskew':
                processed, angle = self.deskew(processed)
                metadata['deskew_angle'] = angle
            
            elif step_name == 'enhance_contrast':
                processed = self.enhance_contrast(processed, **step_config)
            
            elif step_name == 'binarize':
                processed = self.binarize(processed, **step_config)
            
            elif step_name == 'morphology':
                processed = self.morphological_operations(processed, **step_config)
            
            elif step_name == 'remove_borders':
                processed = self.remove_borders(processed, **step_config)
            
            elif step_name == 'resize':
                processed = self.resize_for_ocr(processed, **step_config)
            
            else:
                logger.warning(f"Unknown step: {step_name}")
        
        metadata['final_shape'] = processed.shape
        logger.info(f"Preprocessing complete: {len(steps)} steps applied")
        
        return processed, metadata
    
    def preprocess_pdf(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None,
        dpi: int = 300,
        pipeline: str = 'standard',
        save_images: bool = True
    ) -> List[Tuple[np.ndarray, Dict]]:
        """
        Convert PDF to images and preprocess all pages
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Directory to save preprocessed images
            dpi: DPI for PDF conversion
            pipeline: Preprocessing pipeline to use
            save_images: Whether to save preprocessed images
        
        Returns:
            List of (preprocessed image, metadata) tuples
        """
        # Convert PDF to images
        images = self.pdf_to_images(pdf_path, dpi=dpi, output_format='numpy')
        
        # Preprocess each page
        results = []
        for page_num, img in enumerate(images, 1):
            logger.info(f"Preprocessing page {page_num}/{len(images)}")
            
            preprocessed, metadata = self.preprocess_for_ocr(img, pipeline=pipeline)
            metadata['page_number'] = page_num
            results.append((preprocessed, metadata))
            
            # Save if requested
            if save_images and output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                
                pdf_stem = Path(pdf_path).stem
                img_path = output_path / f"{pdf_stem}_page{page_num}_preprocessed.png"
                cv2.imwrite(str(img_path), preprocessed)
                logger.debug(f"Saved preprocessed image: {img_path}")
        
        return results
    
    # ========================
    # Utility Functions
    # ========================
    
    def save_image(self, img: np.ndarray, output_path: str):
        """Save image to file"""
        cv2.imwrite(output_path, img)
        logger.info(f"Image saved: {output_path}")
    
    def show_comparison(
        self,
        original: np.ndarray,
        preprocessed: np.ndarray,
        title: str = "Comparison"
    ):
        """
        Display original and preprocessed images side-by-side
        (for debugging/visualization)
        """
        try:
            import matplotlib.pyplot as plt
            
            fig, axes = plt.subplots(1, 2, figsize=(15, 7))
            
            axes[0].imshow(cv2.cvtColor(original, cv2.COLOR_BGR2RGB) if len(original.shape) == 3 else original, cmap='gray')
            axes[0].set_title('Original')
            axes[0].axis('off')
            
            axes[1].imshow(preprocessed, cmap='gray')
            axes[1].set_title('Preprocessed')
            axes[1].axis('off')
            
            plt.suptitle(title)
            plt.tight_layout()
            plt.show()
        except ImportError:
            logger.warning("matplotlib not available for visualization")


def main():
    """Example usage"""
    import sys
    
    # Initialize service
    preprocessor = ImagePreprocessingService()
    
    # Example 1: Preprocess a single PDF
    pdf_path = "dataset/raw_drawings/Electrical Engineering/5-1307-137_F_RJY.pdf"
    output_dir = "dataset/preprocessed_images"
    
    if Path(pdf_path).exists():
        print(f"\n{'='*80}")
        print(f"Preprocessing PDF: {pdf_path}")
        print(f"{'='*80}\n")
        
        results = preprocessor.preprocess_pdf(
            pdf_path=pdf_path,
            output_dir=output_dir,
            dpi=300,
            pipeline='standard',  # Options: 'standard', 'aggressive', 'light', 'handwriting'
            save_images=True
        )
        
        print(f"\n✅ Preprocessed {len(results)} pages")
        for img, metadata in results:
            print(f"  Page {metadata['page_number']}: {metadata['original_shape']} → {metadata['final_shape']}")
            print(f"    Deskew angle: {metadata['deskew_angle']:.2f}°")
            print(f"    Steps: {', '.join(metadata['steps_applied'])}")
        
        print(f"\n📁 Saved to: {output_dir}/")
    else:
        print(f"❌ PDF not found: {pdf_path}")
        print("Please provide a valid PDF path")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(message)s'
    )
    main()
