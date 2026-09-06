from typing import List, Dict, Any, Optional
from src.core.dtos.classification_dtos import (
    CategoryPredictionDTO,
    ClassificationResultDTO,
    BatchClassificationDTO
)
from src.infrastructure.logging.logger import get_logger
import math

logger = get_logger(__name__)

class ClassificationService:
    def __init__(self):
        self.keywords = self._build_category_keywords()
        self.HIGH_CONFIDENCE = 0.85
        self.LOW_CONFIDENCE = 0.60
        
    def _build_category_keywords(self) -> Dict[str, List[str]]:
        return {
            'Piping/Process': [
                'pipe', 'piping', 'valve', 'flange', 'flg', 'gasket', 'elbow', 'tee', 'reducer', 
                'coupling', 'P&ID', 'P&I', 'PFD', 'BOM', 'MTO', 'NPS', 'DN', 'PN', 'SCH', 'schedule', 
                'SS316L', 'SS304', 'CS', 'flowline', 'header', 'manifold', 'nozzle', 'fitting', 
                'weld', 'socket', 'butt-weld', 'BW', 'SW', 'THD', 'NPT', 'RF', 'FF', 'RTJ', 'SO', 'WN', 'BL',
                'threaded', 'nominal', 'bore', 'pressure', 'temperature', 'flow', 'process', 'fluid', 
                'steam', 'condensate', 'drain', 'spool', 'exp'
            ],
            'Electrical/Instrumentation': [
                'cable', 'wire', 'conduit', 'junction', 'panel', 'switch', 'breaker', 'transformer', 
                'motor', 'sensor', 'transmitter', 'controller', 'PLC', 'DCS', 'SCADA', 'VFD', 
                'signal', 'voltage', 'volt', 'current', 'ampere', 'watt', 'circuit', 'grounding', 
                'earthing', 'GND', 'PE', 'instrument', 'gauge', 'meter', 'thermocouple', 'RTD', 
                'control valve', 'actuator', 'JB', 'MCC', 'loop', 'I/O', 'tag'
            ],
            'Structural/Civil': [
                'beam', 'column', 'foundation', 'concrete', 'rebar', 'steel', 'structural', 
                'load', 'anchor', 'bolt', 'plate', 'gusset', 'brace', 'truss', 'frame', 'slab', 
                'footing', 'pile', 'grout', 'weld', 'connection', 'support', 'hanger', 'clip', 
                'HSS', 'TOC', 'BOS', 'TOS', 'grid', 'baseplate', 'embed'
            ],
            'Safety/HSE': [
                'safety', 'hazard', 'fire', 'emergency', 'alarm', 'evacuation', 'PPE', 'guard', 
                'barrier', 'ventilation', 'toxic', 'flammable', 'explosion', 'HAZOP', 'SIL', 
                'ESD', 'PSV', 'PRV', 'relief', 'shutdown', 'interlock', 'NFPA', 'OSHA'
            ],
            'Dimensional/Tolerancing': [
                'dimension', 'DIM', 'tolerance', 'TOL', 'clearance', 'offset', 'alignment', 
                'elevation', 'EL', 'CL', 'centerline', 'coordinate', 'datum', 'GD&T', 'flatness', 
                'perpendicular', 'parallel', 'concentricity', 'runout', 'position', 'profile', 
                'angularity', 'symmetry', 'mm', 'inch', 'meter', 'radius', 'diameter', 'height', 'width'
            ],
            'General/Administrative': [
                'revision', 'REV', 'issue', 'approval', 'approved', 'review', 'comment', 'note', 
                'reference', 'REF', 'specification', 'SPEC', 'standard', 'code', 'drawing', 'DWG', 
                'document', 'title', 'date', 'signature', 'stamp', 'mark', 'legend', 'symbol', 
                'abbreviation', 'general', 'TYP', 'typical', 'SHT', 'sheet', 'GA', 'ISO'
            ]
        }

    def _rule_based_classify(self, text: str) -> List[CategoryPredictionDTO]:
        """
        Rule-based classification using keyword matching.
        
        Improved algorithm:
        - Exact word matches get full weight (1.0)
        - Partial matches get half weight (0.5)
        - Confidence scales logarithmically (more realistic)
        """
        predictions = []
        text_lower = text.lower()
        words = text_lower.split()
        
        for category, kws in self.keywords.items():
            # Find keyword matches with quality scoring
            matches = []
            match_score = 0.0
            
            for kw in kws:
                kw_lower = kw.lower()
                # Exact word match (higher weight)
                if kw_lower in words:
                    if kw not in matches:
                        matches.append(kw)
                    match_score += 1.0
                # Partial match in text (lower weight)
                elif kw_lower in text_lower:
                    if kw not in matches:
                        matches.append(kw)
                    match_score += 0.5
            
            if matches:
                # Calculate confidence with logarithmic scaling
                # This gives more realistic confidence growth
                # 1 match ≈ 47%, 2 matches ≈ 57%, 3 matches ≈ 65%, 4+ matches ≈ 70%+
                conf = min(1.0, 0.3 + (0.25 * math.log(match_score + 1)))
                predictions.append(CategoryPredictionDTO(category, conf, matches))
            else:
                predictions.append(CategoryPredictionDTO(category, 0.0, []))
                
        return sorted(predictions, key=lambda x: x.confidence, reverse=True)

    def _try_ai_classify(self, text: str) -> Optional[List[CategoryPredictionDTO]]:
        """
        AI model classification (placeholder).
        
        Integration point for machine learning model.
        Replace this method to use trained ML model.
        """
        return None

    def classify_comment(self, comment_text: str, comment_id: str = '') -> ClassificationResultDTO:
        """Classify a single comment into categories"""
        predictions = self._try_ai_classify(comment_text)
        method = 'ai_model'
        
        if not predictions:
            predictions = self._rule_based_classify(comment_text)
            method = 'rule_based'
            
        primary = predictions[0] if predictions else CategoryPredictionDTO('Unknown', 0.0, [])
        alts = predictions[1:] if len(predictions) > 1 else []
        
        requires_review = primary.confidence < self.LOW_CONFIDENCE
        
        return ClassificationResultDTO(
            comment_id=comment_id,
            text=comment_text,
            primary_category=primary,
            alternative_categories=alts,
            classification_method=method,
            requires_human_review=requires_review
        )
        
    def classify_batch(self, comments: List[Dict[str, Any]], drawing_id: str = '') -> BatchClassificationDTO:
        """Classify multiple comments in batch"""
        results = []
        high = 0
        low = 0
        flagged = 0
        
        for c in comments:
            res = self.classify_comment(c.get('text', ''), str(c.get('id', '')))
            results.append(res)
            
            if res.primary_category.confidence >= self.HIGH_CONFIDENCE:
                high += 1
            else:
                low += 1
                
            if res.requires_human_review:
                flagged += 1
                
        return BatchClassificationDTO(
            drawing_id=drawing_id,
            total_classified=len(results),
            results=results,
            high_confidence_count=high,
            low_confidence_count=low,
            flagged_count=flagged
        )
