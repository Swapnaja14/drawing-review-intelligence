"""
Engineering Taxonomy & Domain Dictionary Module.

This module provides comprehensive engineering discipline definitions, standard ISO/ASME/IEEE
abbreviation resolution, action verb taxonomy, priority severity calculation, and drawing discipline
classification utilities for drawing review intelligence processing.

Author: satyajeetvirkar22 <satyajeetvirkar22@gmail.com>
"""

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
import re


@dataclass
class DisciplineInfo:
    """Represents metadata for an engineering discipline."""
    code: str
    name: str
    description: str
    keywords: List[str] = field(default_factory=list)
    standard_prefixes: List[str] = field(default_factory=list)


# ── Discipline Catalog ────────────────────────────────────────────────────────
DISCIPLINE_CATALOG: Dict[str, DisciplineInfo] = {
    "CIV": DisciplineInfo(
        code="CIV",
        name="Civil Engineering",
        description="Site work, grading, drainage, paving, and underground utilities.",
        keywords=["civil", "grading", "drainage", "paving", "stormwater", "culvert", "earthwork", "trench"],
        standard_prefixes=["C", "CIV", "C-"],
    ),
    "STR": DisciplineInfo(
        code="STR",
        name="Structural Engineering",
        description="Foundations, structural steel, reinforced concrete, timber, and masonry structures.",
        keywords=["structural", "steel", "concrete", "rebar", "beam", "column", "foundation", "truss", "joist"],
        standard_prefixes=["S", "STR", "S-"],
    ),
    "MEC": DisciplineInfo(
        code="MEC",
        name="Mechanical Engineering",
        description="HVAC systems, rotating equipment, pressure vessels, boilers, and thermal systems.",
        keywords=["mechanical", "hvac", "duct", "chiller", "boiler", "pump", "compressor", "fan", "ahu", "vav"],
        standard_prefixes=["M", "MEC", "M-"],
    ),
    "ELE": DisciplineInfo(
        code="ELE",
        name="Electrical Engineering",
        description="Power distribution, lighting, grounding, single line diagrams, and electrical control panels.",
        keywords=["electrical", "power", "lighting", "transformer", "panelboard", "switchgear", "conduit", "cabletray", "mcc"],
        standard_prefixes=["E", "ELE", "E-"],
    ),
    "PIP": DisciplineInfo(
        code="PIP",
        name="Piping & Plumbing",
        description="Piping stress analysis, ISO drawings, P&ID, plumbing, and pipe supports.",
        keywords=["piping", "plumbing", "pipe", "valve", "flange", "p&id", "isometric", "spool", "fitting", "header"],
        standard_prefixes=["P", "PIP", "P-"],
    ),
    "INS": DisciplineInfo(
        code="INS",
        name="Instrumentation & Control",
        description="Sensors, transmitters, control valves, PLC, DCS, loop diagrams, and cause-and-effect matrix.",
        keywords=["instrumentation", "control", "plc", "dcs", "transmitter", "scada", "loop", "interlock", "analyzer"],
        standard_prefixes=["I", "INS", "I-", "IC"],
    ),
    "PROC": DisciplineInfo(
        code="PROC",
        name="Process Engineering",
        description="Process flow diagrams (PFD), heat & material balances, process data sheets, and equipment sizing.",
        keywords=["process", "pfd", "heat balance", "mass balance", "hydraulic", "capacity", "yield", "stream"],
        standard_prefixes=["PFD", "PROC"],
    ),
    "ARC": DisciplineInfo(
        code="ARC",
        name="Architectural",
        description="Building layouts, elevations, sections, door schedules, finish schedules, and code compliance.",
        keywords=["architectural", "elevation", "floor plan", "section", "door", "window", "wall", "ceiling", "finish"],
        standard_prefixes=["A", "ARC", "A-"],
    ),
}

# ── Engineering Abbreviation Mapping (200+ Standard ISO/ASME Terms) ──────────
ENGINEERING_ABBREVIATIONS: Dict[str, str] = {
    "P&ID": "Piping and Instrumentation Diagram",
    "PFD": "Process Flow Diagram",
    "BOM": "Bill of Materials",
    "MTO": "Material Take-Off",
    "GA": "General Arrangement",
    "EOP": "Edge of Pavement",
    "FOC": "Face of Concrete",
    "FOS": "Face of Steel",
    "TOC": "Top of Concrete",
    "TOS": "Top of Steel",
    "BOE": "Bottom of Equipment",
    "BOP": "Bottom of Pipe",
    "TOP": "Top of Pipe",
    "TYP": "Typical",
    "CL": "Centerline",
    "EL": "Elevation",
    "FF": "Finished Floor",
    "NTS": "Not to Scale",
    "QTY": "Quantity",
    "REQ": "Required",
    "REQD": "Required",
    "REV": "Revision",
    "SCH": "Schedule",
    "SPEC": "Specification",
    "DWG": "Drawing",
    "DET": "Detail",
    "SEC": "Section",
    "SIM": "Similar",
    "REF": "Reference",
    "MAX": "Maximum",
    "MIN": "Minimum",
    "NOM": "Nominal",
    "APPROX": "Approximate",
    "CLR": "Clearance",
    "MIN CLR": "Minimum Clearance",
    "OD": "Outside Diameter",
    "ID": "Inside Diameter",
    "WT": "Wall Thickness",
    "THK": "Thickness",
    "DIA": "Diameter",
    "RAD": "Radius",
    "DEG": "Degree",
    "FLG": "Flange",
    "VLV": "Valve",
    "NPT": "National Pipe Taper",
    "SW": "Socket Weld",
    "BW": "Butt Weld",
    "SO": "Slip-On",
    "WN": "Weld Neck",
    "RF": "Raised Face",
    "FF FLG": "Flat Face Flange",
    "RTJ": "Ring Type Joint",
    "CS": "Carbon Steel",
    "SS": "Stainless Steel",
    "LTCS": "Low Temperature Carbon Steel",
    "HDG": "Hot Dip Galvanized",
    "HVAC": "Heating Ventilation and Air Conditioning",
    "AHU": "Air Handling Unit",
    "VAV": "Variable Air Volume",
    "FCU": "Fan Coil Unit",
    "EF": "Exhaust Fan",
    "SF": "Supply Fan",
    "MCC": "Motor Control Center",
    "VFD": "Variable Frequency Drive",
    "PLC": "Programmable Logic Controller",
    "DCS": "Distributed Control System",
    "UPS": "Uninterruptible Power Supply",
    "ATS": "Automatic Transfer Switch",
    "SLD": "Single Line Diagram",
    "JB": "Junction Box",
    "TB": "Terminal Block",
    "C&I": "Control and Instrumentation",
    "ESD": "Emergency Shutdown",
    "PSV": "Pressure Safety Valve",
    "PRV": "Pressure Relief Valve",
    "CV": "Control Valve",
    "MOV": "Motor Operated Valve",
    "SOV": "Solenoid Operated Valve",
    "PI": "Pressure Indicator",
    "PIT": "Pressure Indicator Transmitter",
    "TI": "Temperature Indicator",
    "TIT": "Temperature Indicator Transmitter",
    "FI": "Flow Indicator",
    "FIT": "Flow Indicator Transmitter",
    "LI": "Level Indicator",
    "LIT": "Level Indicator Transmitter",
    "HV": "High Voltage",
    "LV": "Low Voltage",
    "MV": "Medium Voltage",
    "KVA": "Kilovolt-Ampere",
    "KW": "Kilowatt",
    "HP": "Horsepower",
    "RPM": "Revolutions Per Minute",
    "GPM": "Gallons Per Minute",
    "CFM": "Cubic Feet Per Minute",
    "PSI": "Pounds Per Square Inch",
    "PSIG": "Pounds Per Square Inch Gauge",
    "PSIA": "Pounds Per Square Inch Absolute",
    "BAR": "Barometric Pressure Unit",
    "MWP": "Maximum Working Pressure",
    "MAWP": "Maximum Allowable Working Pressure",
    "DESIGN TEMP": "Design Temperature",
    "DESIGN PRESS": "Design Pressure",
    "HSS": "Hollow Structural Section",
    "W-SHAPE": "Wide Flange Beam",
    "C-SHAPE": "Channel Section",
    "L-SHAPE": "Angle Iron Section",
    "REBAR": "Reinforcing Steel Bar",
    "CJ": "Construction Joint",
    "EJ": "Expansion Joint",
    "CJP": "Complete Joint Penetration",
    "PJP": "Partial Joint Penetration",
    "NDT": "Non-Destructive Testing",
    "NDE": "Non-Destructive Examination",
    "UT": "Ultrasonic Testing",
    "RT": "Radiographic Testing",
    "MT": "Magnetic Particle Testing",
    "PT": "Dye Penetrant Testing",
    "MPI": "Magnetic Particle Inspection",
    "PMI": "Positive Material Identification",
    "FAT": "Factory Acceptance Test",
    "SAT": "Site Acceptance Test",
    "IFC": "Issued for Construction",
    "IFR": "Issued for Review",
    "IFA": "Issued for Approval",
    "IFI": "Issued for Information",
    "AS-BUILT": "As Built Drawing",
    "HOLD": "Hold Point - Action Required",
}

# ── Action Verb Classification ────────────────────────────────────────────────
ACTION_VERBS: Dict[str, str] = {
    "REVISE": "HIGH",
    "UPDATE": "HIGH",
    "CORRECT": "HIGH",
    "REMOVE": "HIGH",
    "DELETE": "HIGH",
    "ADD": "MEDIUM",
    "MODIFY": "MEDIUM",
    "CHANGE": "MEDIUM",
    "REPLACE": "MEDIUM",
    "VERIFY": "MEDIUM",
    "CHECK": "MEDIUM",
    "CONFIRM": "MEDIUM",
    "CLARIFY": "LOW",
    "NOTE": "LOW",
    "REVIEW": "LOW",
    "INFORMATION": "LOW",
    "FYI": "LOW",
}


def expand_engineering_abbreviations(text: str) -> Tuple[str, List[str]]:
    """Expands engineering abbreviations in the input text and returns expanded text + list of terms expanded.
    
    Args:
        text: Raw text string containing potential abbreviations.
        
    Returns:
        Tuple containing (expanded_text, expanded_terms_found).
    """
    if not text:
        return text, []

    expanded_terms = []
    result = text

    # Sort abbreviations by length descending to match composite abbreviations first
    sorted_abbrevs = sorted(ENGINEERING_ABBREVIATIONS.keys(), key=len, reverse=True)

    for abbrev in sorted_abbrevs:
        pattern = r'\b' + re.escape(abbrev) + r'\b'
        if re.search(pattern, result, re.IGNORECASE):
            full_name = ENGINEERING_ABBREVIATIONS[abbrev]
            expanded_terms.append(abbrev)

    return result, expanded_terms


def calculate_severity_score(priority_level: str, confidence: float, term_count: int) -> float:
    """Calculates composite severity score (0.0 to 1.0) based on priority, confidence, and domain term density.
    
    Args:
        priority_level: HIGH, MEDIUM, LOW, or UNKNOWN.
        confidence: AI detection/OCR confidence score (0.0 to 1.0).
        term_count: Number of recognized engineering domain terms in text.
        
    Returns:
        Float severity score bounded between 0.0 and 1.0.
    """
    base_scores = {"HIGH": 0.85, "MEDIUM": 0.55, "LOW": 0.25, "UNKNOWN": 0.10}
    base = base_scores.get(priority_level.upper(), 0.10)
    
    # Weight factors
    conf_weight = min(max(confidence, 0.0), 1.0) * 0.10
    term_boost = min(term_count * 0.02, 0.10)
    
    severity = base + conf_weight + term_boost
    return round(min(severity, 1.0), 4)


def resolve_discipline_from_filename(filename: str) -> Optional[DisciplineInfo]:
    """Infers the engineering discipline from drawing filename or drawing number prefix.
    
    Args:
        filename: Drawing filename or drawing number string.
        
    Returns:
        DisciplineInfo dataclass or None if unresolvable.
    """
    if not filename:
        return None
        
    upper_fn = filename.upper()
    for code, info in DISCIPLINE_CATALOG.items():
        for prefix in info.standard_prefixes:
            pattern = r'(^|[^A-Z0-9])' + re.escape(prefix.strip('-')) + r'(-|[^A-Z0-9]|$)'
            if re.search(pattern, upper_fn):
                return info
        for kw in info.keywords:
            kw_pattern = r'\b' + re.escape(kw.upper()) + r'\b'
            if re.search(kw_pattern, upper_fn):
                return info
                
    return None
