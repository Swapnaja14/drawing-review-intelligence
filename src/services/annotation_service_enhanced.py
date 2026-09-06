"""
Enhanced Annotation Detection Service with 4 Extraction Methods:
1. Native PDF Annotation Extraction
2. Color Segmentation
3. Connected Components Analysis
4. Advanced Region Detection (MSER, Edge, Blob)
"""

import time
import cv2
import numpy as np
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Literal

from src.core.dtos.annotation_dtos import BoundingBoxDTO, AnnotationResultDTO, DocumentAnnotationDTO
from src.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

ExtractionMethod = Literal['native', 'color', 'connected', 'region', 'hybrid']


class AnnotationDetectionServiceEnhanced:
    """
    Enhanced annotation detection with multiple extraction strategies.
    
    Methods:
    - native: Fast, accurate PDF annotation extraction
    - color: HSV color segmentation for colored markup
    - connected: Connected component analysis for blob detection
    - region: Advanced region detection (MSER, edges, blobs)
    - hybrid: Combines all methods for best results
    """
    
    def __init__(self):
        self.default_dpi = 150  # Balance between quality and speed
        
    def detect_annotations_on_page(
        self, 
        pdf_path: Path, 
        page_number: int,
        method: ExtractionMethod = 'hybrid'
    ) -> AnnotationResultDTO:
        """
        Detect annotations on a single page using specified method.
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page index (0-based)
            method: Detection method to use
            
        Returns:
            AnnotationResultDTO with detected regions
        """
        start_time = time.time()
        logger.info(f"Detecting annotations on {pdf_path.name}, page {page_number} using {method} method")
        
        regions = []
        try:
            doc = fitz.open(pdf_path)
            if 0 <= page_number < len(doc):
                page = doc[page_number]
                
                if method == 'native':
                    regions.extend(self._extract_native_annotations(page, page_number))
                    regions.extend(self._extract_text_regions(page, page_number))
                    regions.extend(self._detect_redline_regions(page, page_number))
                    
                elif method == 'color':
                    regions = self._detect_by_color_segmentation(page, page_number)
                    
                elif method == 'connected':
                    regions = self._detect_by_connected_components(page, page_number)
                    
                elif method == 'region':
                    regions = self._detect_by_region_proposals(page, page_number)
                    
                elif method == 'hybrid':
                    # Fast & comprehensive markup detection:
                    # 1. Native PDF callouts, stamps, FreeText & polygon annotations
                    # 2. Vector text colored markup (red / blue / yellow / green text)
                    # 3. Vector path redlines, clouds & leaders
                    # 4. Rasterized high-sensitivity color segmentation (HSV/RGB)
                    native = self._extract_native_annotations(page, page_number)
                    native.extend(self._extract_text_regions(page, page_number))
                    native.extend(self._detect_redline_regions(page, page_number))
                    
                    color = self._detect_by_color_segmentation(page, page_number)
                    
                    # Merge and deduplicate
                    all_regions = native + color
                    regions = self._deduplicate_regions(all_regions)
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Error detecting annotations on {pdf_path}: {e}")

        processing_time_ms = (time.time() - start_time) * 1000
        
        return AnnotationResultDTO(
            drawing_id=pdf_path.name,
            page_number=page_number,
            regions=regions,
            detection_method=method,
            processing_time_ms=processing_time_ms
        )

    def detect_all_pages(
        self, 
        pdf_path: Path,
        method: ExtractionMethod = 'hybrid',
        filter_template_regions: bool = True,
        progress_callback=None
    ) -> DocumentAnnotationDTO:
        """
        Detect annotations across all pages.
        
        Args:
            pdf_path: Path to PDF file
            method: Detection method to use
            filter_template_regions: If True, removes regions that appear at identical 
                                     positions across all pages (likely template elements)
            progress_callback: Optional callback(page_num, total_pages) called after each page
            
        Returns:
            DocumentAnnotationDTO with all results
        """
        logger.info(f"Detecting annotations across all pages of {pdf_path.name} using {method}")
        page_results = []
        total_regions = 0
        total_pages = 0
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            doc.close()
            
            for page_num in range(total_pages):
                result = self.detect_annotations_on_page(pdf_path, page_num, method)
                page_results.append(result)
                total_regions += len(result.regions)
                
                # Report progress after each page
                if progress_callback:
                    progress_callback(page_num + 1, total_pages)
            
            # Filter out template regions if enabled and we have multiple pages
            if filter_template_regions and total_pages > 1:
                page_results = self._filter_template_regions(page_results)
                # Recalculate total after filtering
                total_regions = sum(len(r.regions) for r in page_results)
                logger.info(f"After filtering template regions: {total_regions} regions remain")
                
        except Exception as e:
            logger.error(f"Error processing document {pdf_path}: {e}")
            
        return DocumentAnnotationDTO(
            file_name=pdf_path.name,
            total_pages=total_pages,
            page_results=page_results,
            total_regions=total_regions
        )
    
    def _filter_template_regions(self, page_results: List[AnnotationResultDTO], 
                                  position_tolerance: float = 5.0) -> List[AnnotationResultDTO]:
        """
        Remove regions that appear at the same position on ALL pages (template elements).
        
        Engineering drawings often have title blocks with colored fields that appear at
        identical positions on every page. These are template elements, not markup.
        Real annotations/redlines vary by page.
        
        Args:
            page_results: List of per-page detection results
            position_tolerance: Maximum distance (in PDF points) to consider regions "same position"
            
        Returns:
            Filtered page results with template regions removed
        """
        if len(page_results) <= 1:
            return page_results
        
        # Build position frequency map: how many pages have a region at each position
        position_counts = {}  # (x0_rounded, y0_rounded) -> count
        position_to_regions = {}  # (x0_rounded, y0_rounded) -> list of (page_idx, region_idx)
        
        for page_idx, page_result in enumerate(page_results):
            for region_idx, region in enumerate(page_result.regions):
                # Round position to tolerance grid
                pos_key = (
                    round(region.x0 / position_tolerance),
                    round(region.y0 / position_tolerance)
                )
                
                position_counts[pos_key] = position_counts.get(pos_key, 0) + 1
                
                if pos_key not in position_to_regions:
                    position_to_regions[pos_key] = []
                position_to_regions[pos_key].append((page_idx, region_idx))
        
        # Find positions that appear on ALL pages (these are templates)
        total_pages = len(page_results)
        template_positions = {
            pos for pos, count in position_counts.items() 
            if count >= total_pages * 0.8  # 80% threshold (allows for slight variations)
        }
        
        if not template_positions:
            return page_results  # No template regions found
        
        logger.info(f"Found {len(template_positions)} template positions to filter out")
        
        # Create filtered results
        filtered_results = []
        for page_idx, page_result in enumerate(page_results):
            filtered_regions = []
            
            for region in page_result.regions:
                pos_key = (
                    round(region.x0 / position_tolerance),
                    round(region.y0 / position_tolerance)
                )
                
                # Keep region if it's NOT a template position
                if pos_key not in template_positions:
                    filtered_regions.append(region)
            
            # Create new result with filtered regions
            filtered_results.append(
                AnnotationResultDTO(
                    drawing_id=page_result.drawing_id,
                    page_number=page_result.page_number,
                    regions=filtered_regions,
                    detection_method=page_result.detection_method,
                    processing_time_ms=page_result.processing_time_ms
                )
            )
        
        return filtered_results

    # ========================================================================
    # METHOD 1: NATIVE PDF ANNOTATION EXTRACTION
    # ========================================================================
    
    def _extract_native_annotations(self, page: fitz.Page, page_num: int) -> List[BoundingBoxDTO]:
        """Extract native PDF annotations (callouts, comments, stamps, redlines)"""
        regions = []
        for annot in page.annots():
            rect = annot.rect
            info = annot.info or {}
            
            # Filter out AutoCAD SHX text font placeholder boxes
            if info.get('title') == 'AutoCAD SHX Text':
                continue
                
            annot_type = annot.type[1] if annot.type else "annotation"
            
            # Check stroke/fill color if available
            colors = annot.colors or {}
            stroke = colors.get('stroke', [])
            fill = colors.get('fill', [])
            is_red = False
            is_blue = False
            
            if stroke and len(stroke) >= 3:
                if stroke[0] > 0.6 and stroke[1] < 0.4 and stroke[2] < 0.4:
                    is_red = True
                elif stroke[2] > 0.6 and stroke[0] < 0.4 and stroke[1] < 0.4:
                    is_blue = True
            if not is_red and not is_blue and fill and len(fill) >= 3:
                if fill[0] > 0.6 and fill[1] < 0.4 and fill[2] < 0.4:
                    is_red = True
                elif fill[2] > 0.6 and fill[0] < 0.4 and fill[1] < 0.4:
                    is_blue = True
                    
            # If color wasn't in stroke/fill (e.g. FreeText callouts), check text spans inside the annot rect
            if not is_red and not is_blue:
                try:
                    annot_text_dict = page.get_text("dict", clip=rect)
                    for b in annot_text_dict.get("blocks", []):
                        if b.get("type") == 0:
                            for l in b.get("lines", []):
                                for s in l.get("spans", []):
                                    c_int = s.get("color", 0)
                                    sr = (c_int >> 16) & 0xFF
                                    sg = (c_int >> 8) & 0xFF
                                    sb = c_int & 0xFF
                                    if (sr > 130 and sr > max(sg, sb) * 1.25) or (sr > 150 and (sr - max(sg, sb)) > 25):
                                        is_red = True
                                        break
                                    elif (sb > 120 and sb > max(sr, sg) * 1.20) or (sb > 140 and (sb - max(sr, sg)) > 25):
                                        is_blue = True
                                        break
                                if is_red or is_blue:
                                    break
                        if is_red or is_blue:
                            break
                except Exception:
                    pass
                
            if is_red:
                label = "native_redline"
            elif is_blue:
                label = "comment_blue"
            else:
                label = f"native_{annot_type}"
            
            # Ignore small native highlight annotations (table cells, single characters)
            w = rect.x1 - rect.x0
            h = rect.y1 - rect.y0
            if annot_type.lower() == "highlight" and (w < 60 or h < 30 or (w * h) < 2000):
                continue
            if w < 5 and h < 5:
                continue

            regions.append(
                BoundingBoxDTO(
                    x0=float(rect.x0),
                    y0=float(rect.y0),
                    x1=float(rect.x1),
                    y1=float(rect.y1),
                    page_number=page_num,
                    confidence=1.0,
                    label=label
                )
            )
        return regions

    def _extract_text_regions(self, page: fitz.Page, page_num: int) -> List[BoundingBoxDTO]:
        """Extract significant whole comment text blocks (paragraphs/lines) representing reviewer markup"""
        blocks = page.get_text('dict').get('blocks', [])
        colored_lines = []
        
        for block in blocks:
            if block['type'] == 0:  # Text block
                for line in block.get('lines', []):
                    line_text = ""
                    line_bbox = None
                    line_is_red = False
                    line_is_blue = False
                    
                    for span in line.get('spans', []):
                        txt = span.get('text', '').strip()
                        if not txt:
                            continue
                        color = span.get('color', 0)
                        r = (color >> 16) & 0xFF
                        g = (color >> 8) & 0xFF
                        b = color & 0xFF
                        
                        is_red = (r > 130 and r > max(g, b) * 1.25) or (r > 150 and (r - max(g, b)) > 25)
                        is_blue = (b > 120 and b > max(r, g) * 1.20) or (b > 140 and (b - max(r, g)) > 25)
                        
                        if is_red:
                            line_is_red = True
                        elif is_blue:
                            line_is_blue = True
                        
                        if is_red or is_blue:
                            line_text += (" " if line_text else "") + txt
                            sb = span['bbox']
                            if line_bbox is None:
                                line_bbox = list(sb)
                            else:
                                line_bbox[0] = min(line_bbox[0], sb[0])
                                line_bbox[1] = min(line_bbox[1], sb[1])
                                line_bbox[2] = max(line_bbox[2], sb[2])
                                line_bbox[3] = max(line_bbox[3], sb[3])
                    
                    if line_bbox and line_text:
                        color_label = "comment_red" if line_is_red else "comment_blue"
                        colored_lines.append({
                            "text": line_text,
                            "bbox": line_bbox,
                            "color": color_label
                        })
        
        # Cluster vertically and horizontally adjacent lines into whole comment blocks
        clusters = []
        for line in colored_lines:
            merged = False
            l_box = line["bbox"]
            l_col = line["color"]
            l_h = l_box[3] - l_box[1]
            
            for c in clusters:
                if c["color"] != l_col:
                    continue
                c_box = c["bbox"]
                
                # Check spatial proximity
                h_overlap = max(0, min(c_box[2], l_box[2]) - max(c_box[0], l_box[0]))
                h_dist = max(0, max(c_box[0], l_box[0]) - min(c_box[2], l_box[2]))
                v_dist = max(0, max(c_box[1], l_box[1]) - min(c_box[3], l_box[3]))
                
                # If lines are vertically close (within 2 line heights) and aligned/overlapping horizontally
                if v_dist <= max(20.0, l_h * 2.2) and (h_overlap > 0 or h_dist <= 35.0):
                    c["bbox"][0] = min(c_box[0], l_box[0])
                    c["bbox"][1] = min(c_box[1], l_box[1])
                    c["bbox"][2] = max(c_box[2], l_box[2])
                    c["bbox"][3] = max(c_box[3], l_box[3])
                    c["text"] += " " + line["text"]
                    merged = True
                    break
                    
            if not merged:
                clusters.append({
                    "color": l_col,
                    "bbox": list(l_box),
                    "text": line["text"]
                })
        
        regions = []
        for c in clusters:
            clean_txt = c["text"].strip()
            if len(clean_txt) == 0:
                continue
            pad_x = 2.0
            pad_y = 2.0
            regions.append(
                BoundingBoxDTO(
                    x0=float(c["bbox"][0] - pad_x),
                    y0=float(c["bbox"][1] - pad_y),
                    x1=float(c["bbox"][2] + pad_x),
                    y1=float(c["bbox"][3] + pad_y),
                    page_number=page_num,
                    confidence=0.98,
                    label=c["color"]
                )
            )
        return regions

    def _detect_redline_regions(self, page: fitz.Page, page_num: int) -> List[BoundingBoxDTO]:
        """Detect red and blue markup (vector-based paths and arrows)"""
        regions = []
        paths = page.get_drawings()
        
        for path in paths:
            is_red = False
            is_blue = False
            
            # Check stroke color
            stroke_color = path.get('color')
            if stroke_color and len(stroke_color) >= 3:
                r, g, b = stroke_color[:3]
                if r > 0.5 and (r - max(g, b)) > 0.15:
                    is_red = True
                elif b > 0.5 and (b - max(r, g)) > 0.15:
                    is_blue = True
                    
            # Check fill color
            fill_color = path.get('fill')
            if fill_color and len(fill_color) >= 3:
                r, g, b = fill_color[:3]
                if r > 0.5 and (r - max(g, b)) > 0.15:
                    is_red = True
                elif b > 0.5 and (b - max(r, g)) > 0.15:
                    is_blue = True
                    
            if is_red or is_blue:
                rect = path['rect']
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                if w * h >= 10:  # Ignore microscopic dots
                    regions.append(
                        BoundingBoxDTO(
                            x0=float(rect[0]),
                            y0=float(rect[1]),
                            x1=float(rect[2]),
                            y1=float(rect[3]),
                            page_number=page_num,
                            confidence=0.90,
                            label="native_redline" if is_red else "comment_blue"
                        )
                    )
        return regions

    # ========================================================================
    # METHOD 2: COLOR SEGMENTATION (RED & MULTI-COLOR MARKUP)
    # ========================================================================
    
    def _detect_by_color_segmentation(self, page: fitz.Page, page_num: int) -> List[BoundingBoxDTO]:
        """
        Detect annotations using robust color segmentation.
        Prioritizes redline and blue reviewer comments and clusters text + arrows.
        """
        try:
            detection_dpi = 100
            pix = page.get_pixmap(dpi=detection_dpi)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            
            # PyMuPDF pixmap is RGB or RGBA
            if pix.n == 4:
                img_rgb = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
            else:
                img_rgb = img.copy()
            
            scale_factor = 72.0 / detection_dpi  # Convert pixel coords to PDF coords
            regions = []
            
            r = img_rgb[:, :, 0].astype(int)
            g = img_rgb[:, :, 1].astype(int)
            b = img_rgb[:, :, 2].astype(int)
            
            max_area_px = int(img_rgb.shape[0] * img_rgb.shape[1] * 0.85)
            
            # ── 1. Dedicated High-Sensitivity Red Detection ──
            red_mask = np.zeros((img_rgb.shape[0], img_rgb.shape[1]), dtype=np.uint8)
            red_condition = (r > 100) & ((r - np.maximum(g, b)) > 20)
            red_mask[red_condition] = 255
            
            # Morphological closing + dilation to cluster text letters and lines into complete cohesive comments
            kernel_close_red = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 15))
            red_closed = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel_close_red)
            kernel_dilate_red = cv2.getStructuringElement(cv2.MORPH_RECT, (12, 10))
            red_clustered = cv2.dilate(red_closed, kernel_dilate_red, iterations=1)
            
            red_contours, _ = cv2.findContours(red_clustered, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in red_contours:
                x, y, w, h = cv2.boundingRect(c)
                area_px = w * h
                if 400 <= area_px <= max_area_px and w >= 25 and h >= 12:
                    x0_pt = float(max(0, x - 2) * scale_factor)
                    y0_pt = float(max(0, y - 2) * scale_factor)
                    x1_pt = float((x + w + 2) * scale_factor)
                    y1_pt = float((y + h + 2) * scale_factor)
                    
                    regions.append(
                        BoundingBoxDTO(
                            x0=x0_pt,
                            y0=y0_pt,
                            x1=x1_pt,
                            y1=y1_pt,
                            page_number=page_num,
                            confidence=0.90,
                            label="comment_red"
                        )
                    )
            
            # ── 2. Dedicated High-Sensitivity Blue Detection ──
            blue_mask = np.zeros((img_rgb.shape[0], img_rgb.shape[1]), dtype=np.uint8)
            blue_condition = (b > 100) & ((b - np.maximum(r, g)) > 20)
            blue_mask[blue_condition] = 255
            
            # Morphological closing + dilation to cluster blue text, revision clouds, and pointer arrows together
            kernel_close_blue = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 15))
            blue_closed = cv2.morphologyEx(blue_mask, cv2.MORPH_CLOSE, kernel_close_blue)
            kernel_dilate_blue = cv2.getStructuringElement(cv2.MORPH_RECT, (12, 10))
            blue_clustered = cv2.dilate(blue_closed, kernel_dilate_blue, iterations=1)
            
            blue_contours, _ = cv2.findContours(blue_clustered, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in blue_contours:
                x, y, w, h = cv2.boundingRect(c)
                area_px = w * h
                if 400 <= area_px <= max_area_px and w >= 25 and h >= 12:
                    x0_pt = float(max(0, x - 2) * scale_factor)
                    y0_pt = float(max(0, y - 2) * scale_factor)
                    x1_pt = float((x + w + 2) * scale_factor)
                    y1_pt = float((y + h + 2) * scale_factor)
                    
                    regions.append(
                        BoundingBoxDTO(
                            x0=x0_pt,
                            y0=y0_pt,
                            x1=x1_pt,
                            y1=y1_pt,
                            page_number=page_num,
                            confidence=0.90,
                            label="comment_blue"
                        )
                    )
            
            # ── 3. Other Color Annotations (Highlighter Yellow, Green) ──
            img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
            hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
            
            # Mask out any pixels already detected as red or blue markup
            non_red_blue = (red_mask == 0) & (blue_mask == 0)
            
            other_colors = {
                'comment_yellow': [(np.array([22, 140, 140]), np.array([34, 255, 255]))],
                'comment_green':  [(np.array([45, 120, 120]), np.array([80, 255, 255]))],
            }
            
            for color_label, ranges in other_colors.items():
                mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
                for lower, upper in ranges:
                    m = cv2.inRange(hsv, lower, upper)
                    mask = cv2.bitwise_or(mask, m)
                
                mask[~non_red_blue] = 0
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 15))
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    area_px = w * h
                    # Highlights must be substantial (at least 60x30 px and 2500 px area) to avoid single character/cell fragments
                    if 2500 <= area_px <= max_area_px and w >= 60 and h >= 30:
                        x0_pt = float(x * scale_factor)
                        y0_pt = float(y * scale_factor)
                        x1_pt = float((x + w) * scale_factor)
                        y1_pt = float((y + h) * scale_factor)
                        
                        regions.append(
                            BoundingBoxDTO(
                                x0=x0_pt,
                                y0=y0_pt,
                                x1=x1_pt,
                                y1=y1_pt,
                                page_number=page_num,
                                confidence=0.85,
                                label=color_label
                            )
                        )
            
            logger.info(f"  Color segmentation found {len(regions)} regions on page {page_num}")
            return regions
            
        except Exception as e:
            logger.error(f"Error in color segmentation: {e}")
            return []

    # ========================================================================
    # METHOD 3: CONNECTED COMPONENTS ANALYSIS
    # ========================================================================
    
    def _detect_by_connected_components(self, page: fitz.Page, page_num: int) -> List[BoundingBoxDTO]:
        """
        Detect annotations using connected component analysis.
        Groups connected pixels into regions.
        """
        try:
            # Convert page to image
            pix = page.get_pixmap(dpi=self.default_dpi)
            img = np.frombuffer(pix.samples, dtype=np.uint8)
            img = img.reshape(pix.height, pix.width, pix.n)
            
            # Handle RGBA
            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            
            # Apply adaptive thresholding to handle varying lighting
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY_INV, 11, 2
            )
            
            # Morphological operations to connect nearby regions
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            # Connected component analysis
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                morph, connectivity=8, ltype=cv2.CV_32S
            )
            
            # Extract bounding boxes
            regions = []
            scale_factor = 72.0 / self.default_dpi
            
            for i in range(1, num_labels):  # Skip background (label 0)
                x, y, w, h, area = stats[i]
                
                # STRICTER filters to avoid noise
                # Annotations are typically 200-5000 pixels at 150 DPI
                # Equivalent to roughly 0.5-3 inches
                if (area >= 200 and area <= 50000 and  # Reasonable area range
                    w >= 10 and h >= 10 and  # Minimum size
                    w <= 500 and h <= 500):  # Maximum size (avoid full-page detections)
                    
                    aspect_ratio = max(w, h) / min(w, h)
                    if aspect_ratio < 10:  # Avoid very thin lines (likely drawing elements)
                        regions.append(
                            BoundingBoxDTO(
                                x0=float(x * scale_factor),
                                y0=float(y * scale_factor),
                                x1=float((x + w) * scale_factor),
                                y1=float((y + h) * scale_factor),
                                page_number=page_num,
                                confidence=0.70,
                                label="connected_component"
                            )
                        )
            
            return regions
            
        except Exception as e:
            logger.error(f"Error in connected components: {e}")
            return []

    # ========================================================================
    # METHOD 4: ADVANCED REGION DETECTION
    # ========================================================================
    
    def _detect_by_region_proposals(self, page: fitz.Page, page_num: int) -> List[BoundingBoxDTO]:
        """
        Detect annotations using advanced region detection:
        - MSER (Maximally Stable Extremal Regions)
        - Edge detection + grouping
        - Blob detection
        """
        try:
            # Convert page to image
            pix = page.get_pixmap(dpi=self.default_dpi)
            img = np.frombuffer(pix.samples, dtype=np.uint8)
            img = img.reshape(pix.height, pix.width, pix.n)
            
            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
            
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            
            regions = []
            scale_factor = 72.0 / self.default_dpi
            
            # 1. MSER Detection (best for text-like regions)
            try:
                mser = cv2.MSER_create()
                mser.setDelta(5)
                mser.setMinArea(50)
                mser.setMaxArea(10000)
                regions_mser, _ = mser.detectRegions(gray)
                
                for region in regions_mser:
                    x, y, w, h = cv2.boundingRect(region)
                    if w * h >= 50:
                        regions.append(
                            BoundingBoxDTO(
                                x0=float(x * scale_factor),
                                y0=float(y * scale_factor),
                                x1=float((x + w) * scale_factor),
                                y1=float((y + h) * scale_factor),
                                page_number=page_num,
                                confidence=0.65,
                                label="mser_region"
                            )
                        )
            except Exception as e:
                logger.warning(f"MSER detection failed: {e}")
            
            # 2. Edge-based detection
            try:
                edges = cv2.Canny(gray, 50, 150)
                
                # Dilate edges to connect nearby regions
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                edges = cv2.dilate(edges, kernel, iterations=2)
                
                contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    if w * h >= 50:
                        regions.append(
                            BoundingBoxDTO(
                                x0=float(x * scale_factor),
                                y0=float(y * scale_factor),
                                x1=float((x + w) * scale_factor),
                                y1=float((y + h) * scale_factor),
                                page_number=page_num,
                                confidence=0.60,
                                label="edge_region"
                            )
                        )
            except Exception as e:
                logger.warning(f"Edge detection failed: {e}")
            
            # 3. Blob detection
            try:
                params = cv2.SimpleBlobDetector_Params()
                params.minArea = 50
                params.maxArea = 10000
                params.filterByArea = True
                params.filterByCircularity = False
                params.filterByConvexity = False
                params.filterByInertia = False
                
                detector = cv2.SimpleBlobDetector_create(params)
                keypoints = detector.detect(gray)
                
                for kp in keypoints:
                    x, y = int(kp.pt[0]), int(kp.pt[1])
                    size = int(kp.size)
                    regions.append(
                        BoundingBoxDTO(
                            x0=float((x - size // 2) * scale_factor),
                            y0=float((y - size // 2) * scale_factor),
                            x1=float((x + size // 2) * scale_factor),
                            y1=float((y + size // 2) * scale_factor),
                            page_number=page_num,
                            confidence=0.55,
                            label="blob"
                        )
                    )
            except Exception as e:
                logger.warning(f"Blob detection failed: {e}")
            
            return regions
            
        except Exception as e:
            logger.error(f"Error in region detection: {e}")
            return []

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def _deduplicate_regions(self, regions: List[BoundingBoxDTO], iou_threshold: float = 0.45) -> List[BoundingBoxDTO]:
        """
        Remove duplicate regions using IoU and containment clustering.
        Absorbs single-letter/sub-word fragments into whole cohesive comment blocks.
        Preserves separate red and blue comments side-by-side.
        """
        if not regions:
            return []
        
        # Prefer direct colored vector text and native redline comments
        def rank_confidence(r: BoundingBoxDTO) -> float:
            score = r.confidence
            lbl = r.label.lower()
            if "red" in lbl:
                score += 0.20
            if "blue" in lbl:
                score += 0.20
            if "highlight" in lbl:
                score -= 0.15
            return score
            
        sorted_regions = sorted(regions, key=rank_confidence, reverse=True)
        keep = []
        
        for region in sorted_regions:
            reg_lbl = region.label.lower()
            reg_color = "red" if ("red" in reg_lbl) else ("blue" if ("blue" in reg_lbl) else ("green" if ("green" in reg_lbl) else ("yellow" if ("yellow" in reg_lbl) else "other")))
            
            is_duplicate = False
            for kept_region in keep:
                kept_lbl = kept_region.label.lower()
                kept_color = "red" if ("red" in kept_lbl) else ("blue" if ("blue" in kept_lbl) else ("green" if ("green" in kept_lbl) else ("yellow" if ("yellow" in kept_lbl) else "other")))
                
                # Check spatial containment and overlap
                c_reg_in_kept = self._calculate_containment(region, kept_region)
                c_kept_in_reg = self._calculate_containment(kept_region, region)
                iou = self._calculate_iou(region, kept_region)
                
                # If red vs blue separate comments, do not suppress unless one literally contains the other (nested)
                if (reg_color == "red" and kept_color == "blue") or (reg_color == "blue" and kept_color == "red"):
                    if c_reg_in_kept > 0.85 or c_kept_in_reg > 0.85:
                        is_duplicate = True
                        break
                    continue
                
                # If candidate is contained in an existing kept whole comment (containment > 35%) or high IoU
                if c_reg_in_kept > 0.35 or c_kept_in_reg > 0.35 or iou > iou_threshold:
                    # Absorb and expand kept bounding box to encompass the full comment area
                    kept_region.x0 = min(kept_region.x0, region.x0)
                    kept_region.y0 = min(kept_region.y0, region.y0)
                    kept_region.x1 = max(kept_region.x1, region.x1)
                    kept_region.y1 = max(kept_region.y1, region.y1)
                    # If kept_region was generic and candidate is colored, promote label
                    if kept_color in ("other", "yellow") and reg_color in ("red", "blue", "green"):
                        kept_region.label = region.label
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                keep.append(region)
        
        return keep
    
    def _calculate_containment(self, small_box: BoundingBoxDTO, large_box: BoundingBoxDTO) -> float:
        """Calculate what fraction of small_box is contained inside large_box."""
        if small_box.x1 <= large_box.x0 or large_box.x1 <= small_box.x0 or small_box.y1 <= large_box.y0 or large_box.y1 <= small_box.y0:
            return 0.0
        xi_min = max(small_box.x0, large_box.x0)
        yi_min = max(small_box.y0, large_box.y0)
        xi_max = min(small_box.x1, large_box.x1)
        yi_max = min(small_box.y1, large_box.y1)
        inter_area = max(0.0, xi_max - xi_min) * max(0.0, yi_max - yi_min)
        small_area = (small_box.x1 - small_box.x0) * (small_box.y1 - small_box.y0)
        return (inter_area / small_area) if small_area > 0 else 0.0

    def _calculate_iou(self, box1: BoundingBoxDTO, box2: BoundingBoxDTO) -> float:
        """Calculate Intersection over Union between two bounding boxes with fast rejection."""
        # Fast bounding box disjoint test
        if box1.x1 <= box2.x0 or box2.x1 <= box1.x0 or box1.y1 <= box2.y0 or box2.y1 <= box1.y0:
            return 0.0
            
        # Intersection
        xi_min = max(box1.x0, box2.x0)
        yi_min = max(box1.y0, box2.y0)
        xi_max = min(box1.x1, box2.x1)
        yi_max = min(box1.y1, box2.y1)
        
        inter_width = max(0.0, xi_max - xi_min)
        inter_height = max(0.0, yi_max - yi_min)
        inter_area = inter_width * inter_height
        if inter_area <= 0.0:
            return 0.0
        
        # Union
        box1_area = (box1.x1 - box1.x0) * (box1.y1 - box1.y0)
        box2_area = (box2.x1 - box2.x0) * (box2.y1 - box2.y0)
        union_area = box1_area + box2_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0

