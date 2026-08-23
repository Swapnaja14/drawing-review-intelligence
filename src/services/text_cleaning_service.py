import re
import difflib
import time
from typing import List, Dict, Any, Tuple
from src.core.dtos.comment_processing_dtos import (
    CleanedCommentDTO,
    CorrectionDTO,
    TextCleaningResultDTO
)
from src.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

class TextCleaningService:
    def __init__(self):
        self.engineering_dict = self._build_engineering_dictionary()
    
    def _build_engineering_dictionary(self) -> Dict[str, str]:
        return {
            'P&ID': 'Piping and Instrumentation Diagram',
            'ANSI': 'American National Standards Institute',
            'HVAC': 'Heating Ventilation and Air Conditioning',
            'NDE': 'Non-Destructive Examination',
            'SS316L': 'Stainless Steel 316L',
            'CS': 'Carbon Steel',
            'GA': 'General Arrangement',
            'BOM': 'Bill of Materials',
            'ISO': 'Isometric',
            'DWG': 'Drawing',
            'REV': 'Revision',
            'SPEC': 'Specification',
            'TOL': 'Tolerance',
            'DIM': 'Dimension',
            'REF': 'Reference',
            'TYP': 'Typical',
            'SHT': 'Sheet',
            'SCH': 'Schedule',
            'NPS': 'Nominal Pipe Size',
            'DN': 'Diameter Nominal',
            'PN': 'Pressure Nominal',
            'ASME': 'American Society of Mechanical Engineers',
            'AWS': 'American Welding Society',
            'API': 'American Petroleum Institute',
            'ASTM': 'American Society for Testing and Materials',
            'NFPA': 'National Fire Protection Association',
            'OSHA': 'Occupational Safety and Health Administration',
            'PPE': 'Personal Protective Equipment',
            'SOP': 'Standard Operating Procedure',
            'QA': 'Quality Assurance',
            'QC': 'Quality Control',
            'NDT': 'Non-Destructive Testing',
            'WPS': 'Welding Procedure Specification',
            'PQR': 'Procedure Qualification Record',
            'MTO': 'Material Take-Off',
            'MOC': 'Management of Change',
            'HAZOP': 'Hazard and Operability Study',
            'SIL': 'Safety Integrity Level',
            'ESD': 'Emergency Shutdown',
            'PSV': 'Pressure Safety Valve',
            'PRV': 'Pressure Relief Valve',
            'PFD': 'Process Flow Diagram',
            'FEED': 'Front End Engineering Design',
            'EPC': 'Engineering Procurement Construction'
        }

    def clean_text(self, raw_text: str) -> CleanedCommentDTO:
        corrections: List[CorrectionDTO] = []
        text = raw_text
        
        # Step 1: Remove OCR noise
        noise_pattern = re.compile(r'([!@#$%\^&*()_+={}\[\]:;"\'<>,.?/\\|`~])\1+')
        if noise_pattern.search(text):
            text = noise_pattern.sub(r'\1', text)
            corrections.append(CorrectionDTO(original=raw_text, corrected=text, correction_type='noise_removal'))

        # Step 2: Normalize whitespace
        new_text = re.sub(r'\s+', ' ', text).strip()
        if text != new_text:
            corrections.append(CorrectionDTO(original=text, corrected=new_text, correction_type='whitespace'))
            text = new_text

        # Step 3: Expand abbreviations
        words = text.split()
        expanded_words = []
        for word in words:
            clean_word = word.strip('.,!?;:')
            if clean_word in self.engineering_dict:
                expanded = self.engineering_dict[clean_word]
                expanded_words.append(word.replace(clean_word, expanded))
                corrections.append(CorrectionDTO(original=clean_word, corrected=expanded, correction_type='abbreviation'))
            else:
                expanded_words.append(word)
        new_text = ' '.join(expanded_words)
        if text != new_text:
            text = new_text

        # Step 4: Fix common OCR errors
        ocr_fixes = [('rn', 'm'), ('0', 'O'), ('1', 'l')]
        new_text = text
        for old, new in ocr_fixes:
            if old in new_text:
                new_text = new_text.replace(old, new)
        
        if text != new_text:
            corrections.append(CorrectionDTO(original=text, corrected=new_text, correction_type='spelling'))
            text = new_text

        similarity = difflib.SequenceMatcher(None, raw_text, text).ratio()
        
        return CleanedCommentDTO(
            original_text=raw_text,
            cleaned_text=text,
            corrections=corrections,
            similarity_score=similarity
        )

    def clean_batch(self, comments: List[Dict[str, Any]], drawing_id: str = '') -> TextCleaningResultDTO:
        start_time = time.time()
        cleaned = []
        texts = []
        
        for comment in comments:
            raw = comment.get('text', '')
            res = self.clean_text(raw)
            cleaned.append(res)
            texts.append(res.cleaned_text)
            
        dups = self.detect_duplicates(texts)
        
        elapsed = (time.time() - start_time) * 1000
        return TextCleaningResultDTO(
            drawing_id=drawing_id,
            total_comments=len(comments),
            cleaned_comments=cleaned,
            duplicates_removed=len(dups),
            processing_time_ms=elapsed
        )

    def detect_duplicates(self, texts: List[str], threshold: float = 0.85) -> List[Tuple[int, int]]:
        duplicates = []
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                ratio = difflib.SequenceMatcher(None, texts[i], texts[j]).ratio()
                if ratio >= threshold:
                    duplicates.append((i, j))
        return duplicates
