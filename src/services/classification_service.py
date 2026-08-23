from typing import List, Dict, Any, Optional
from src.core.dtos.classification_dtos import (
    CategoryPredictionDTO,
    ClassificationResultDTO,
    BatchClassificationDTO
)
from src.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

class ClassificationService:
    def __init__(self):
        self.keywords = self._build_category_keywords()
        self.HIGH_CONFIDENCE = 0.85
        self.LOW_CONFIDENCE = 0.60
        
    def _build_category_keywords(self) -> Dict[str, List[str]]:
        return {
            'Piping/Process': ['pipe', 'piping', 'valve', 'flange', 'gasket', 'elbow', 'tee', 'reducer', 'coupling', 'P&ID', 'flowline', 'header', 'manifold', 'nozzle', 'fitting', 'weld', 'socket', 'butt-weld', 'threaded', 'nominal', 'schedule', 'bore', 'pressure', 'temperature', 'flow', 'process', 'fluid', 'steam', 'condensate', 'drain'],
            'Electrical/Instrumentation': ['cable', 'wire', 'conduit', 'junction', 'panel', 'switch', 'breaker', 'transformer', 'motor', 'sensor', 'transmitter', 'controller', 'PLC', 'DCS', 'signal', 'voltage', 'current', 'ampere', 'circuit', 'grounding', 'earthing', 'instrument', 'gauge', 'meter', 'thermocouple', 'RTD', 'control valve', 'actuator'],
            'Structural/Civil': ['beam', 'column', 'foundation', 'concrete', 'rebar', 'steel', 'structural', 'load', 'anchor', 'bolt', 'plate', 'gusset', 'brace', 'truss', 'frame', 'slab', 'footing', 'pile', 'grout', 'weld', 'connection', 'support', 'hanger', 'clip'],
            'Safety/HSE': ['safety', 'hazard', 'fire', 'emergency', 'alarm', 'evacuation', 'PPE', 'guard', 'barrier', 'ventilation', 'toxic', 'flammable', 'explosion', 'HAZOP', 'SIL', 'ESD', 'PSV', 'relief', 'shutdown', 'interlock', 'NFPA', 'OSHA'],
            'Dimensional/Tolerancing': ['dimension', 'tolerance', 'clearance', 'offset', 'alignment', 'elevation', 'coordinate', 'datum', 'GD&T', 'flatness', 'perpendicular', 'parallel', 'concentricity', 'runout', 'position', 'profile', 'angularity', 'symmetry', 'mm', 'inch', 'meter', 'radius', 'diameter'],
            'General/Administrative': ['revision', 'issue', 'approval', 'review', 'comment', 'note', 'reference', 'specification', 'standard', 'code', 'drawing', 'document', 'title', 'date', 'signature', 'stamp', 'mark', 'legend', 'symbol', 'abbreviation', 'general']
        }

    def _rule_based_classify(self, text: str) -> List[CategoryPredictionDTO]:
        predictions = []
        words = text.lower().split()
        
        for category, kws in self.keywords.items():
            matches = [kw for kw in kws if kw.lower() in text.lower()]
            if matches:
                conf = min(1.0, len(matches) / 3.0) 
                predictions.append(CategoryPredictionDTO(category, conf, matches))
            else:
                predictions.append(CategoryPredictionDTO(category, 0.0, []))
                
        return sorted(predictions, key=lambda x: x.confidence, reverse=True)

    def _try_ai_classify(self, text: str) -> Optional[List[CategoryPredictionDTO]]:
        return None

    def classify_comment(self, comment_text: str, comment_id: str = '') -> ClassificationResultDTO:
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
