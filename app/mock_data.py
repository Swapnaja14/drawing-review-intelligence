"""
Mock data for UCC AI Drawing Review Comment Analyzer.
Provides realistic engineering drawing comment datasets for all screens.
"""
from dataclasses import dataclass, field
from typing import List, Optional
import random

# ── Project records ──────────────────────────────────────────────────────────

@dataclass
class Project:
    id: str
    name: str
    drawings: int
    comments: int
    status: str          # "Active", "Complete", "On Hold"
    progress: int        # 0–100
    last_modified: str
    engineer: str

PROJECTS: List[Project] = [
    Project("PRJ-001", "UCC Site-4 Expansion",       48, 312, "Active",   78, "2026-07-28", "A. Mehta"),
    Project("PRJ-002", "Refinery Unit-7 Upgrade",    32, 197, "Active",   55, "2026-07-25", "S. Nair"),
    Project("PRJ-003", "Pipeline Corridor North",    61, 408, "Complete", 100, "2026-07-10", "R. Kapoor"),
    Project("PRJ-004", "Compressor Station Alpha",   19, 121, "On Hold",  33, "2026-07-05", "T. Patel"),
    Project("PRJ-005", "LNG Terminal Phase-2",       74, 523, "Active",   62, "2026-07-30", "V. Singh"),
    Project("PRJ-006", "Water Treatment Facility",   27, 184, "Complete", 100, "2026-06-20", "D. Rao"),
    Project("PRJ-007", "Offshore Platform Mod",      41, 291, "Active",   41, "2026-07-29", "J. Sharma"),
]

# ── KPI totals ────────────────────────────────────────────────────────────────

KPI = {
    "total_projects":   7,
    "drawings_processed": 302,
    "comments_detected":  2036,
    "accuracy":          91.4,
    "trend_projects":   "+2",
    "trend_drawings":  "+18",
    "trend_comments":  "+143",
    "trend_accuracy":  "+0.8",
}

# ── Comment / OCR records ─────────────────────────────────────────────────────

CATEGORIES = ["Dimensional", "Structural", "Electrical", "Material", "Documentation", "Other"]
STATUSES   = ["Pending", "Approved", "Rejected", "Flagged"]

@dataclass
class Comment:
    id: str
    project_id: str
    drawing_no: str
    page: int
    ocr_text: str
    category: str
    confidence: float     # 0.0–1.0
    status: str
    bbox: tuple           # (x, y, w, h) normalised 0–1
    reviewer: Optional[str]
    timestamp: str

_raw_comments = [
    ("C-0001","PRJ-001","UCC-E-101",1,"MIN WALL THICKNESS 6MM PER ASME B31.3 §304","Dimensional",0.97,"Approved",(0.12,0.23,0.28,0.04),"A. Mehta","2026-07-28 09:14"),
    ("C-0002","PRJ-001","UCC-E-101",1,"SEE DETAIL B FOR NOZZLE SCHEDULE","Documentation",0.88,"Approved",(0.55,0.40,0.22,0.03),"A. Mehta","2026-07-28 09:18"),
    ("C-0003","PRJ-001","UCC-E-102",2,"WELD TYPE E70XX SMAW ALL AROUND","Structural",0.76,"Pending",(0.08,0.61,0.30,0.04),None,"2026-07-28 10:02"),
    ("C-0004","PRJ-001","UCC-E-103",1,"INSULATION: 50MM MINERAL WOOL","Material",0.92,"Approved",(0.42,0.18,0.25,0.03),"A. Mehta","2026-07-28 10:45"),
    ("C-0005","PRJ-001","UCC-E-104",3,"CONDUIT TRAY 150×75 GI PERFORATED","Electrical",0.65,"Flagged",(0.20,0.55,0.35,0.04),None,"2026-07-28 11:23"),
    ("C-0006","PRJ-001","UCC-E-104",3,"GROUNDING LUG 16MM² COPPER","Electrical",0.83,"Pending",(0.60,0.70,0.20,0.03),None,"2026-07-28 11:25"),
    ("C-0007","PRJ-002","RU7-P-201",1,"PIPE SCHEDULE 80, GRADE A53","Material",0.91,"Approved",(0.15,0.30,0.28,0.04),"S. Nair","2026-07-25 14:10"),
    ("C-0008","PRJ-002","RU7-P-201",2,"FLANGE RATING ANSI 150# RF","Dimensional",0.94,"Approved",(0.50,0.45,0.24,0.03),"S. Nair","2026-07-25 14:22"),
    ("C-0009","PRJ-002","RU7-P-202",1,"TIE-IN POINT KP 12+450","Documentation",0.58,"Flagged",(0.08,0.72,0.32,0.04),None,"2026-07-25 15:05"),
    ("C-0010","PRJ-002","RU7-P-203",4,"SUPPORT TYPE 'C' AT 3M INTERVALS","Structural",0.79,"Pending",(0.35,0.28,0.30,0.04),None,"2026-07-25 15:40"),
    ("C-0011","PRJ-003","PL-N-301",1,"CATHODIC PROTECTION: IMPRESSED CURRENT","Electrical",0.96,"Approved",(0.10,0.20,0.35,0.04),"R. Kapoor","2026-07-10 08:55"),
    ("C-0012","PRJ-003","PL-N-301",2,"COATING SYSTEM DFT 300µM EPOXY+PU","Material",0.89,"Approved",(0.48,0.55,0.28,0.03),"R. Kapoor","2026-07-10 09:10"),
    ("C-0013","PRJ-003","PL-N-302",1,"HYDRO TEST PRESSURE 1.5× DESIGN","Structural",0.72,"Rejected",(0.18,0.65,0.26,0.04),"R. Kapoor","2026-07-10 09:45"),
    ("C-0014","PRJ-004","CS-A-401",1,"ANCHOR BOLT 4× M30 GRADE 8.8","Dimensional",0.85,"Pending",(0.30,0.35,0.22,0.03),None,"2026-07-05 11:00"),
    ("C-0015","PRJ-005","LNG-T-501",1,"CRYOGENIC INSULATION PERLITE FILL","Material",0.98,"Approved",(0.05,0.15,0.40,0.04),"V. Singh","2026-07-30 10:20"),
    ("C-0016","PRJ-005","LNG-T-502",3,"EMERGENCY SHUT-OFF VALVE (ESDV)","Electrical",0.87,"Pending",(0.55,0.60,0.28,0.04),None,"2026-07-30 11:05"),
    ("C-0017","PRJ-005","LNG-T-503",2,"BOIL-OFF GAS (BOG) RETURN LINE DN200","Dimensional",0.93,"Approved",(0.22,0.40,0.32,0.04),"V. Singh","2026-07-30 11:50"),
    ("C-0018","PRJ-006","WT-F-601",1,"DOSING PUMP CAPACITY 120 L/H","Mechanical",0.70,"Flagged",(0.40,0.50,0.28,0.03),None,"2026-06-20 14:30"),
    ("C-0019","PRJ-007","OP-M-701",1,"DECK PLATE 10MM A36 NON-SLIP SURFACE","Structural",0.81,"Pending",(0.12,0.42,0.35,0.04),None,"2026-07-29 09:00"),
    ("C-0020","PRJ-007","OP-M-702",2,"HANDRAIL H=1100MM SS316L","Dimensional",0.88,"Approved",(0.50,0.30,0.25,0.03),"J. Sharma","2026-07-29 09:30"),
]

COMMENTS: List[Comment] = [Comment(*r) for r in _raw_comments]

# ── Activity feed ─────────────────────────────────────────────────────────────

ACTIVITIES = [
    {"icon": "fa5s.check-circle",  "color": "#4ADE80", "text": "Comment C-0017 approved",            "time": "2 min ago"},
    {"icon": "fa5s.upload",        "color": "#3E9BFF", "text": "Drawing LNG-T-503 uploaded",          "time": "8 min ago"},
    {"icon": "fa5s.flag",          "color": "#FBBF24", "text": "Comment C-0016 flagged for review",   "time": "15 min ago"},
    {"icon": "fa5s.times-circle",  "color": "#F87171", "text": "Comment C-0013 rejected",             "time": "1 hr ago"},
    {"icon": "fa5s.robot",         "color": "#8B9CFF", "text": "OCR completed: OP-M-702",             "time": "1 hr ago"},
    {"icon": "fa5s.file-export",   "color": "#3E9BFF", "text": "Report exported: PRJ-003",            "time": "3 hr ago"},
    {"icon": "fa5s.user-check",    "color": "#4ADE80", "text": "Review session started: PRJ-005",     "time": "4 hr ago"},
]

# ── Processing jobs ───────────────────────────────────────────────────────────

JOBS = [
    {"name": "LNG-T-501 OCR",          "progress": 100, "status": "Approved"},
    {"name": "OP-M-701 Classification", "progress":  72, "status": "Pending"},
    {"name": "RU7-P-203 OCR",           "progress":  45, "status": "Pending"},
    {"name": "CS-A-401 Upload",         "progress":  10, "status": "Pending"},
]

# ── Analytics data ────────────────────────────────────────────────────────────

MONTHLY_COUNTS = {
    "months":   ["Jan","Feb","Mar","Apr","May","Jun","Jul"],
    "comments": [120,  180,  145,  210,  195,  280,  312],
    "approved": [ 98,  152,  118,  180,  161,  243,  278],
}

CATEGORY_COUNTS = {
    "Dimensional":   412,
    "Structural":    318,
    "Electrical":    287,
    "Material":      241,
    "Documentation": 198,
    "Other":          97,
}

PARETO_DATA = {
    "categories": ["Dimensional","Structural","Electrical","Material","Documentation","Other"],
    "counts":     [412, 318, 287, 241, 198, 97],
    "cumulative": [26.3, 46.6, 64.9, 80.3, 93.0, 100.0],
}

# ── Export history ────────────────────────────────────────────────────────────

EXPORT_HISTORY = [
    {"name":"PRJ-003_Report_2026-07-10.xlsx","format":"Excel","date":"2026-07-10","size":"1.2 MB"},
    {"name":"PRJ-001_Comments_2026-07-28.csv","format":"CSV",  "date":"2026-07-28","size":"84 KB"},
    {"name":"PRJ-005_Summary_2026-07-30.pdf", "format":"PDF",  "date":"2026-07-30","size":"3.4 MB"},
    {"name":"PRJ-002_Report_2026-07-25.xlsx", "format":"Excel","date":"2026-07-25","size":"987 KB"},
]
