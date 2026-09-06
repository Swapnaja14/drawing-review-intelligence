"""
src/ai/dataset_generator.py
Dataset generation, mining from raw drawings, and stratified train/val/test splitting
for DistilBERT 13-class engineering review error classification.
"""

import os
import sys
import random
import csv
from pathlib import Path
from typing import List, Dict, Tuple
import pymupdf as fitz

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Deterministic seed for reproducible dataset splits
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DRAWINGS_DIR = PROJECT_ROOT / "dataset" / "raw_drawings"
DATA_DRAWINGS_DIR = PROJECT_ROOT / "data" / "drawings"
OUTPUT_DIR = PROJECT_ROOT / "dataset" / "classification_dataset"

# 13 Engineering Error Categories from Specification
CATEGORIES = [
    "Technical",
    "Drafting",
    "Dimension",
    "Cosmetic",
    "Standards",
    "Coordination",
    "Documentation",
    "Revision",
    "Calculation",
    "Feasibility",
    "Material",
    "Notes",
    "BOM"
]

CATEGORY_TO_ID = {cat: idx for idx, cat in enumerate(CATEGORIES)}
ID_TO_CATEGORY = {idx: cat for idx, cat in enumerate(CATEGORIES)}

# Reviewer initial patterns found in real engineering markups
REVIEWER_INITIALS = ["-JDM", "-JCM", "-BEK", "-RJY", "-JJD", "-MWR", "-UCC", "By: BreKol", "By: VSM", ""]

# Action prefixes
ACTION_PREFIXES = ["VERIFY", "UPDATE", "CHECK", "REVISE", "CONFIRM", "INDICATE", "LOCATE", "SHOW", "REMOVE", "ADD", "DO NOT"]


def get_domain_templates() -> Dict[str, List[str]]:
    """Rich domain comment templates across all 13 engineering error categories."""
    return {
        "Technical": [
            "Incorrect member size for {member}: upgrade {beam_type} to {beam_type2} for span load",
            "Missing connection detail at column {col_tag} and beam {beam_tag} intersection",
            "Wrong weld callout: replace fillet weld with {weld_type} on moment connection",
            "Part number wrong on {equip} bracket mounting assembly: shows {part_num} instead of {part_num2}",
            "ECN number missing on engineering change detail for {assembly}",
            "Machining symbol missing on flange mating face surface finish requirement",
            "Incorrect tolerance specified on hole pattern for {equip} baseplate",
            "Verify structural connection capacity: shear tab bolt count insufficient",
            "Check weld symbol pitch and staggered spacing on stiffener plate",
            "Missing moment connection plate weld size callout on detail {det_num}",
            "Incorrect nozzle flange connection rating {flg_rating} on vessel {equip}",
            "Machining finish symbol Ra 3.2 missing on shaft seal landing",
            "ECN no missing on revised gusset plate detail",
            "Part number mismatch between assembly drawing and sub-assembly detail",
            "Wrong weld symbol: field weld flag indicated instead of shop weld",
            "Incorrect pipe schedule {sch} specified for design pressure {press} PSI",
            "Missing stiffener plate connection at high stress beam junction",
            "Weld size undersized: 1/4 inch fillet weld specified but 3/8 inch required for base metal thickness",
            "Wrong bolt grade specified on structural shear connection: specify A325 instead of standard bolts",
            "Check equipment nozzle load connection details on {equip} inlet flange",
        ],
        "Drafting": [
            "Line overlap observed between dimension extension line and centerline on grid {grid1}",
            "Missing hidden line for underground conduit duct bank on plan view",
            "Incorrect drawing scale: indicated scale {scale} does not match graphic bar scale",
            "Wrong projection views: Section {sec_letter} projection is inverted from plan",
            "Section cut symbol on sheet {sht1} points in wrong viewing direction",
            "Leader line crossing dimension string: reroute leader to detail bubble",
            "Detail bubble {det_num} missing sheet cross-reference on elevation view",
            "Missing dashed hidden line representing equipment clearance envelope",
            "Hatch pattern missing in concrete foundation section cut",
            "Line weight for piping header too thin: distinguish from background grid lines",
            "Isometric drawing view orientation misaligned with plan coordinates",
            "Overlapping text and leader lines obscuring nozzle callout on {equip}",
            "Missing match line callout on sheet {sht1} for continuation on sheet {sht2}",
            "Wrong view orientation: detail shows left elevation instead of right elevation",
            "Drafting error: dimension line cuts through equipment outline",
            "Centerline missing on symmetric equipment foundation pad detail",
            "Arrowhead missing on section cut callout marker",
            "Drafting view mismatch: isometric view shows valve that is omitted on plan view",
            "Missing break line symbol on truncated pipe spool run",
            "Hidden lines showing as solid lines in elevation section view",
        ],
        "Dimension": [
            "Incorrect dimension: overall length shows {dim1} but sum of segment callouts is {dim2}",
            "Missing dimension from column grid {grid1} to pump centerline",
            "CL EL {elev} callout missing for pipe centerline on elevation view",
            "Center-to-center dimension between nozzles N1 and N2 is missing",
            "Incorrect elevation callout: TOC shows {elev1} but Section shows {elev2}",
            "Dimension string does not close: {dim1} discrepancy at wall interface",
            "Missing radial clearance dimension around valve handwheel",
            "Provide missing coordinate dimensions X, Y, Z for pipe support shoe {shoe_tag}",
            "Nozzle projection dimension missing from vessel outer shell",
            "Incorrect distance between anchor bolt centers on foundation template",
            "Missing vertical clearance dimension below overhead monorail beam",
            "Check pipe spool cut length dimension: account for gasket thickness",
            "Dimension callout from survey monument datum is missing on plot plan",
            "Tolerance callout +/- 1/16\" missing on overall skid length dimension",
            "Verify missing setback dimension from property boundary line",
            "Dimension extension line detached from reference feature on plan view",
            "Discrepancy in pipe diameter callout: 6 inch indicated on plan but 8 inch on elevation",
            "Missing radius dimension on elbow bend curvature callout",
            "Overall height dimension missing from skid base frame to top of vessel nozzle",
            "Anchor bolt projection dimension from top of grout missing",
        ],
        "Cosmetic": [
            "Text alignment in general notes section is jagged: align left margins",
            "Font size too small on valve tag callouts: increase to standard 2.5mm",
            "Spelling error in note 3: 'reciever' should be corrected to 'receiver'",
            "Typo error in title: 'structral' should be 'structural'",
            "Text overlapping with drawing border at lower right corner",
            "Font style inconsistent: use standard Romans font throughout sheet",
            "Typo in note 7: 'feedeer' corrected to 'feeder'",
            "Spelling mistake in coating spec note: 'galvanise' should be 'galvanized'",
            "Text callout rotated at odd angle: align horizontally for readability",
            "Typo error: 'temparature' spelled incorrectly in instrument schedule",
            "Text justification misaligned in equipment table column",
            "Font height inconsistent between sheet title and drawing subtitle",
            "Typo in general note: 'valvue' should read 'valve'",
            "Cosmetic cleanup: remove stray CAD dots and unreferenced text fragments",
            "Spelling error: 'pressur' missing 'e' in pipe line description",
            "Inconsistent capitalization in equipment callouts: use all uppercase",
            "Text overlapping dimension leader arrow: adjust text box position",
            "Typo error in title block: 'ENGINEERINGG' misspelled with double G",
            "Font thickness too heavy making small numerical tags illegible",
            "Misaligned column text in revision history table",
        ],
        "Standards": [
            "Incorrect symbol used for check valve: per ISA-5.1 standard replace with standard symbol",
            "Codal issue: stair handrail height {dim1} does not meet OSHA/IBC standard minimum 42 inches",
            "Welding symbol not compliant with AWS A2.4 standard notation",
            "P&ID symbology does not conform to company drafting standard STD-001",
            "Electrical schematic symbols do not follow IEEE / IEC standard convention",
            "Hazardous area classification boundary symbol missing per NFPA 497 standard",
            "Flange facing standard designation RF vs FF non-compliant with ASME B16.5",
            "Safety relief valve symbol does not comply with API 526 standard representation",
            "Structural steel member designation format violates AISC standard naming",
            "Pipe hanger support symbol non-compliant with MSS SP-58 standard",
            "Geometric tolerancing GD&T frame symbol missing datum reference per ASME Y14.5",
            "Emergency exit signage symbol not per ISO 7010 safety sign standard",
            "Codal compliance issue: aisle clearance width below NFPA minimum 36 inches",
            "Standard compliance: instrumentation tag format does not follow ISA-5.1 naming rule",
            "ASME code stamp requirement symbol missing from pressure vessel nameplate callout",
            "Non-standard abbreviation used: replace 'VLV' with standard abbreviation per project code",
            "Safety shower symbol orientation violates ANSI Z358.1 specification",
            "Pipe schedule standard callout non-compliant with ASME B36.10M",
            "Standard electrical grounding symbol missing at transformer neutral connection",
            "Codal issue: egress platform landing dimensions violate NFPA 101 Life Safety Code",
        ],
        "Coordination": [
            "Clash with piping: 6 inch CS line conflicts with electrical cable tray at grid {grid1}",
            "Clash with civil/structural: HVAC duct penetrates structural moment frame beam",
            "Clash with electrical: conduit bank routes directly through valve operating envelope",
            "Coordinate with piping department: verify nozzle orientation matches P&ID {pid_num}",
            "Inter-discipline clash: pipe support bracket interferes with instrument junction box {jb_tag}",
            "Coordinate with civil lead: concrete pad size insufficient for new pump skid footprint",
            "System clash: cable ladder obstructs access to emergency shower station",
            "Coordinate with mechanical: equipment nozzle loads exceed allowable piping interface limits",
            "Clash detected in 3D model between fire protection sprinkler header and structural brace",
            "Coordinate electrical power feed routing with underground drainage piping",
            "Interference between crane hook travel envelope and lighting fixture layout",
            "Coordinate tie-in point TP-{tie_in} location between piping and battery limit package",
            "Inter-discipline interference: structural diagonal bracing blocks instrument transmitter display",
            "Clash between gravity drain line slope and underground electrical duct bank",
            "Coordinate with architectural team: wall penetration sleeve location conflicts with column",
            "Piping and structural clash: pipe flange hits bottom flange of W12 beam",
            "Coordinate HVAC supply register location with overhead cable tray run",
            "Clash with equipment access: motor removal path blocked by adjacent process line",
            "Coordinate instrument air supply line routing with control valve manifold",
            "Interference between flare header expansion loop and existing pipe rack column",
        ],
        "Documentation": [
            "Title block incomplete: project number and drawing revision letter missing",
            "Missing client drawing reference number in master title block",
            "Engineer and checker approval signatures and dates missing in sign-off block",
            "Drawing title does not match master document register index",
            "Missing sheet reference callout: 'See companion sheet {dwg_ref} for continuation'",
            "Title block scale box shows 'NTS' but drawing is plotted to scale 1:50",
            "Project code and CAD drawing file name missing from title block margin",
            "Incomplete documentation: missing reference standard specification document number",
            "Drawing status stamp missing: stamp 'ISSUED FOR CONSTRUCTION' before release",
            "Sheet number indicates sheet 2 of 4 but total drawing set has 5 sheets",
            "Client logo and project title missing from cover sheet title block",
            "Documentation hold: pending vendor certified drawing attachment",
            "Drawing cross-reference index table incomplete on cover sheet",
            "Missing engineer of record professional seal and signature in title block",
            "Title block CAD layer locked with outdated contractor company name",
            "Document distribution stamp incomplete: missing transmittal number",
            "Drawing release status still marked 'DRAFT': update to 'APPROVED FOR CONSTRUCTION'",
            "Missing reference drawing numbers for electrical tie-in in documentation block",
            "Project work order number missing in document control block",
            "Drawing index sheet list does not match actual sheets included in package",
        ],
        "Revision": [
            "Revision cloud missing around modified nozzle connection at grid {grid1}",
            "Revision table not updated: add Rev B description 'Incorporated client comments'",
            "Revision symbol delta-2 missing near relocated drain valve",
            "Revision triangle tag on plan view does not match revision table entry",
            "Missing revision cloud on bill of materials row 4 modified quantity",
            "Revision history block missing date and initial for Revision C",
            "Previous revision cloud Rev A must be removed before issuing Rev B",
            "Revision note missing: reference ECN-4081 in revision description column",
            "Delta revision symbol missing on updated elevation callout",
            "Revision cloud incomplete: does not fully enclose modified piping spool",
            "Revision status in title block says Rev 1 but revision table lists Rev 2",
            "Revision block shows Rev 0 date but drawing contains Rev 1 markups",
            "Missing revision triangle tag next to revised beam size on framing plan",
            "Revision cloud overlaps drawing title block: reposition cloud boundary",
            "Revision table row entry missing reviewer initials and approval date",
            "Multiple revisions mixed on sheet: clear Rev 1 clouds and keep only Rev 2 changes",
            "Revision description vague: replace 'Revisions' with detailed change description",
            "Delta symbol callout 3 missing on sheet 2 revision history table",
            "Revision cloud drawn with wrong line weight: must follow revision standard style",
            "Revision issue status changed from IFD to IFC but revision table not updated",
        ],
        "Calculation": [
            "Design inconsistency: pressure drop calculation does not match line sizing on P&ID",
            "Structural beam size W14x90 inconsistent with design calculation sheet CALC-ST-101",
            "Pump head calculation mismatch between data sheet and process flow diagram",
            "Calculation error: thermal expansion stress exceeds allowable code stress on line {line_num}",
            "Foundation pile load capacity inconsistent with geotechnical soil report calculation",
            "Cable voltage drop calculation exceeds 3% allowable limit for 480V feeder",
            "Design calculation inconsistency: vessel wall thickness calculation requires 12mm not 10mm",
            "Relief valve sizing calculation sheet indicates orifice area 0.50 sq in but drawing shows 0.38",
            "Wind load overturning moment calculation inconsistent with anchor bolt sizing",
            "Flow rate calculation discrepancy between PFD heat & material balance and line schedule",
            "Short circuit current rating calculation does not support specified breaker kAIC rating",
            "Pipe span deflection calculation exceeds L/240 criteria under hydrostatic test load",
            "Hydraulic gradient calculation discrepancy on gravity sewer line slope",
            "Seismic anchor load calculation inconsistent with baseplate anchor embedment depth",
            "Thermal relief calculation missing for trapped liquid segment on line {line_num}",
            "Design calculation inconsistency: heat loss calculation requires 50mm insulation not 25mm",
            "Structural truss member buckling calculation does not verify unbraced length",
            "Vessel nozzle reinforcement pad area calculation insufficient for external piping moment",
            "Transformer sizing calculation does not account for continuous motor starting kVA",
            "Bearing pressure calculation under footing exceeds allowable soil bearing capacity",
        ],
        "Feasibility": [
            "Erection feasibility issue: column splice location inaccessible for mobile crane hook",
            "Fabrication feasibility: weld joint between thick plates cannot be reached with welding gun",
            "Maintenance accessibility: insufficient clearance to pull heat exchanger tube bundle",
            "Erection sequence conflict: beam cannot be installed after vessel is set on foundation",
            "Fabrication issue: minimum bend radius on 1/2\" structural plate will cause cracking",
            "Valve handwheel location unreachable from operating platform: add chain wheel operator",
            "Flange bolting accessibility: clearance between flange and vessel wall too tight for torque wrench",
            "Rigging and lifting lug placement causes center of gravity tilt during erection",
            "Equipment transport feasibility: skid width exceeds maximum roadway shipping clearance",
            "Pump maintenance feasibility: motor cannot be removed without dismantling overhead piping",
            "Field assembly feasibility: provide bolted splice instead of field full-penetration weld",
            "Accessibility issue: transmitter display not readable from operating floor",
            "Erection clearance: overhead crane hook cannot reach pump for maintenance removal",
            "Fabrication feasibility: tight pipe spool geometry cannot be hot-dip galvanized without pooling",
            "Constructability issue: anchor bolt template cannot be installed due to rebar congestion",
            "Valve operation feasibility: hand lever hits structural column when opening valve",
            "Maintenance feasibility: filter basket cannot be removed without disconnecting piping",
            "Field weld accessibility: joint located inside enclosed box beam cannot be inspected",
            "Transport limit: modular unit height {dim1} exceeds railway overpass clearance",
            "Erection feasibility: provide temporary lifting lugs for modular frame transport",
        ],
        "Material": [
            "Incorrect material specified: line requires {pipe_mat} instead of carbon steel for corrosive service",
            "Material grade mismatch: structural plates show ASTM A36 instead of high-strength A992",
            "Gasket material specified is incompatible with process fluid: change to PTFE / Spiral Wound",
            "Fastener material callout incorrect: specify ASTM A193 Gr. B7 studs with 2H heavy hex nuts",
            "Wrong valve body material: specify 316L stainless steel for acid injection line",
            "Anchor bolt material must be hot-dip galvanized ASTM F1554 Grade 55",
            "Pipe insulation material specification missing on high temperature steam line",
            "Material callout for baseplate shows mild steel: revise to ASTM A572 Gr 50",
            "Incorrect O-ring elastomer material: specify Viton for hydrocarbon service",
            "Reinforcing bar rebar grade must be ASTM A615 Grade 60 per structural spec",
            "Material specification discrepancy between piping line list and isometric drawing",
            "Incorrect material: 304SS specified where 316L required for chloride stress corrosion",
            "Grout material callout must specify non-shrink cementitious grout per project standard",
            "Structural beam material callout missing ASTM specification standard on drawing",
            "Tubing material callout incorrect: specify seamless 316SS instrument tubing",
            "Wrong gasket material: graphite filled spiral wound required for steam service",
            "Material grade inconsistency: pipe schedule shows SS304 but fittings show carbon steel",
            "Flange material must match pipe material specification ASTM A105 for CS lines",
            "Corrosion allowance material buffer omitted in wall thickness specification",
            "Material specification required for cable tray: hot-dip galvanized steel vs aluminum",
        ],
        "Notes": [
            "Incorrect general note 4: field verification of existing foundation elevation is mandatory",
            "Update notes: add note regarding post-weld heat treatment PWHT requirement",
            "General note 2 references obsolete specification document 01-SPEC-1998: update to Rev 2026",
            "Note callout on sheet 1 contradicts note 6 on companion drawing {dwg_ref}",
            "Add mandatory safety note: 'Do not energize equipment prior to interlock validation'",
            "Update note 8: specify paint and protective coating system per client specification",
            "Note discrepancy: note states galvanize all steel but detail indicates painted finish",
            "Add environmental note regarding secondary containment dike drainage valve operation",
            "Note 5 wording unclear: revise to state clearly 'All dimensions are in millimeters unless noted'",
            "General notes page says scan survey date 06/19/25: please clarify survey reference note",
            "Update general note 12 regarding torque requirements for structural high-strength bolts",
            "Incorrect note: reference to hydrotest pressure in note 3 contradicts line schedule",
            "Add note: 'All sharp edges and burrs must be ground smooth prior to painting'",
            "General note 7 missing requirement for non-destructive examination NDT of critical welds",
            "Update piping notes to include minimum slope requirement on condensate headers",
            "Note reference error: detail refers to note 15 but notes list only goes up to note 11",
            "Add general note specifying concrete minimum 28-day compressive strength 4000 PSI",
            "General note regarding field touch-up paint missing from structural drawing",
            "Revise note 1 to reference the latest geotechnical site investigation report",
            "Mandatory note missing: 'Contractor shall verify all tie-in dimensions prior to fabrication'",
        ],
        "BOM": [
            "Incorrect part number in BOM item {bom_item}: catalog number does not match manufacturer spec",
            "BOM quantity mismatch: drawing shows 4 support brackets but BOM lists quantity 2",
            "BOM description incorrect: item 7 description says gate valve but graphic shows globe valve",
            "Material take-off MTO line item missing for pipe reducer on line {line_num}",
            "BOM item table missing unit weight and total weight column entries",
            "Incorrect flange rating listed in bill of materials table for item 12",
            "BOM part number typo: replace vendor code XYZ-100 with XYZ-200",
            "Spare parts list in bill of materials does not include replacement gasket sets",
            "BOM table column for material grade is blank for items 3 through 8",
            "Discrepancy between BOM item count and callout bubble count on assembly view",
            "Update bill of materials BOM to reflect latest revision of piping component schedule",
            "BOM item 5 size callout shows 4 inch but isometric drawing shows 6 inch pipe",
            "Missing item tag number in BOM schedule column for temperature transmitter",
            "Bill of materials quantity error: 16 bolts required per flange pair but BOM lists 8",
            "Incorrect manufacturer name listed in bill of materials for motor starter unit",
            "BOM description missing valve actuator model and air supply pressure rating",
            "Part number in bill of materials table does not match vendor certified cut sheet",
            "MTO discrepancy: structural framing schedule omitted W10x49 beam material take-off",
            "BOM item table row 9 missing ASTM material specification number",
            "Update BOM item descriptions to match standard SAP catalog naming conventions",
        ]
    }


def fill_template(template: str) -> str:
    """Fills template placeholders with realistic engineering data."""
    pipe_sizes = ['2"', '3"', '4"', '6"', '8"', '10"', '12"', '16"', '20"']
    pipe_mats = ['CS', 'SS304', 'SS316L', 'Alloy 20', 'Hastelloy C276', 'Duplex 2205', 'Carbon Steel']
    equips = ['V-101', 'P-204A/B', 'E-301', 'T-502', 'C-100', 'TK-401', 'HEX-102', 'Pump Skid']
    pid_nums = ['M-009', 'P-101', 'PID-54718', 'P&ID-201', 'M-015', 'PID-004']
    flg_ratings = ['150#', '300#', '600#', '900#', '1500#']
    schs = ['10', '20', '40', '80', '160', 'STD', 'XS', 'XXS']
    valves = ['Gate', 'Globe', 'Ball', 'Butterfly', 'Check', 'Needle', 'Diaphragm', 'Control']
    flg_types = ['Weld Neck', 'Slip On', 'Blind', 'Socket Weld', 'Lap Joint', 'Threaded']
    lines = ['174005-S12-04-P08', '08-PL-104-CS', '04-ST-201-SS', '12-CW-305-CS', '02-IA-010-CS']
    grids = ['A-1', 'B-3', 'C-5', 'D-2', 'G-7', 'E-4', 'F-6']
    elevs = ["102'-6\"", "345'-11 3/4\"", "114'-0\"", "88'-4 1/2\"", "EL +14.500m", "EL +108.250'"]
    cols = ['C1', 'C4', 'C12', 'B-08', 'W14x90', 'HSS 8x8x1/2']
    pressures = ['50', '150', '300', '600', '1200', '2500']
    trans_tags = ['PT-101', 'TT-204', 'FT-305', 'LT-402', 'PIT-109', 'PDT-015']
    jbs = ['JB-101', 'JB-204', 'JB-A01', 'JB-E12']
    mccs = ['MCC-1', 'MCC-2A', 'MCC-4B', 'MCC-100']
    cables = ['3/C #10 AWG', '4PR #16 AWG SHIELDED', '1C 500 MCM', '12C #14 AWG']
    dwgs = ['C-54718-31-002', 'M-70086-01-004', 'S-70086-01-101', 'E-54725-29-C0-26403']
    members = ['girder G-1', 'column C-12', 'truss chord T-3', 'cross brace B-04', 'purlin P-10']
    beam_types = ['W12x26', 'W14x48', 'W16x57', 'HSS 6x6x3/8', 'C10x20']
    beam_types2 = ['W14x90', 'W18x76', 'W21x83', 'HSS 8x8x1/2', 'W24x104']
    weld_types = ['full penetration CJP groove weld', '3/8\" fillet weld with backing bar', 'complete joint penetration weld', 'all-around fillet weld']
    part_nums = ['BKT-4081-A', 'PL-102-CS', 'FST-882-SS', 'BRG-902']
    part_nums2 = ['BKT-4081-B', 'PL-102-HDG', 'FST-882-B7', 'BRG-904']
    assemblies = ['filter skid base', 'pipe rack anchor frame', 'reboiler saddle', 'valve manifold bracket']
    scales = ['1:50', '1:100', '1/4\" = 1\'-0\"', '1/2\" = 1\'-0\"', '1:20']
    sec_letters = ['A-A', 'B-B', 'C-C', 'D-D', 'E-E']
    shts = ['1', '2', '3', '4', '5']
    dims = ['12\'-6\"', '3450 mm', '8\'-4 1/2\"', '1200 mm', '45\'-0\"', '150 mm', '500 mm']
    det_nums = ['Detail 3', 'Detail B', 'Section 4', 'Detail 12']
    bom_items = ['3', '5', '8', '12', '14', '21']
    shoe_tags = ['PS-101', 'PS-204', 'SH-08', 'SUP-12']

    return template.format(
        pipe_size=random.choice(pipe_sizes),
        pipe_mat=random.choice(pipe_mats),
        equip=random.choice(equips),
        pid_num=random.choice(pid_nums),
        flg_rating=random.choice(flg_ratings),
        sch=random.choice(schs),
        valve_type=random.choice(valves),
        flg_type=random.choice(flg_types),
        line_num=random.choice(lines),
        grid1=random.choice(grids),
        grid2=random.choice(grids),
        elev=random.choice(elevs),
        elev1=random.choice(elevs),
        elev2=random.choice(elevs),
        col_tag=random.choice(cols),
        press=random.choice(pressures),
        trans_tag=random.choice(trans_tags),
        jb_tag=random.choice(jbs),
        mcc_tag=random.choice(mccs),
        cable_tag=random.choice(cables),
        dwg_ref=random.choice(dwgs),
        bw_size=random.choice(pipe_sizes),
        nps=random.choice(pipe_sizes),
        tie_in=f"{random.randint(101, 999)}",
        panel_tag=f"CP-{random.randint(1, 20)}",
        member=random.choice(members),
        beam_type=random.choice(beam_types),
        beam_type2=random.choice(beam_types2),
        beam_tag=random.choice(beam_types),
        weld_type=random.choice(weld_types),
        part_num=random.choice(part_nums),
        part_num2=random.choice(part_nums2),
        assembly=random.choice(assemblies),
        scale=random.choice(scales),
        sec_letter=random.choice(sec_letters),
        sht1=random.choice(shts),
        sht2=random.choice(shts),
        dim1=random.choice(dims),
        dim2=random.choice(dims),
        det_num=random.choice(det_nums),
        bom_item=random.choice(bom_items),
        shoe_tag=random.choice(shoe_tags)
    )


def apply_variations(text: str) -> str:
    """Adds realistic reviewer initials, action prefixes, and casing variations."""
    # 50% chance of adding reviewer initial
    if random.random() < 0.60:
        initial = random.choice(REVIEWER_INITIALS)
        if initial:
            text = f"{text} {initial}".strip()

    # 30% chance of uppercase styling (standard in CAD drawings)
    if random.random() < 0.35:
        text = text.upper()

    return text


def generate_balanced_dataset(samples_per_category: int = 250) -> List[Tuple[str, str, int]]:
    """
    Generates a balanced dataset across all 13 categories.
    Returns: List of (text, category_name, category_id)
    """
    templates = get_domain_templates()
    dataset: List[Tuple[str, str, int]] = []

    for cat in CATEGORIES:
        cat_id = CATEGORY_TO_ID[cat]
        cat_templates = templates.get(cat, [])
        cat_samples: List[str] = []

        while len(cat_samples) < samples_per_category:
            template = random.choice(cat_templates)
            filled = fill_template(template)
            varied = apply_variations(filled)
            cat_samples.append(varied)

        for s in cat_samples[:samples_per_category]:
            dataset.append((s, cat, cat_id))

    random.shuffle(dataset)
    return dataset


def split_and_save_dataset(
    dataset: List[Tuple[str, str, int]],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15
) -> Tuple[int, int, int]:
    """Splits dataset into stratified Train/Val/Test CSV files."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    by_category: Dict[str, List[Tuple[str, str, int]]] = {cat: [] for cat in CATEGORIES}
    for item in dataset:
        by_category[item[1]].append(item)

    train_data = []
    val_data = []
    test_data = []

    for cat, items in by_category.items():
        random.shuffle(items)
        n = len(items)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        train_data.extend(items[:n_train])
        val_data.extend(items[n_train:n_train + n_val])
        test_data.extend(items[n_train + n_val:])

    random.shuffle(train_data)
    random.shuffle(val_data)
    random.shuffle(test_data)

    def write_csv(filepath: Path, rows: List[Tuple[str, str, int]]):
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["text", "category_name", "label"])
            for text, cat_name, label in rows:
                writer.writerow([text, cat_name, label])

    write_csv(OUTPUT_DIR / "train.csv", train_data)
    write_csv(OUTPUT_DIR / "val.csv", val_data)
    write_csv(OUTPUT_DIR / "test.csv", test_data)

    print("\nDataset successfully generated and saved to:", OUTPUT_DIR)
    print(f"  - Categories:     {len(CATEGORIES)} ({', '.join(CATEGORIES)})")
    print(f"  - Train Set:      {len(train_data)} samples ({OUTPUT_DIR / 'train.csv'})")
    print(f"  - Validation Set: {len(val_data)} samples ({OUTPUT_DIR / 'val.csv'})")
    print(f"  - Test Set:       {len(test_data)} samples ({OUTPUT_DIR / 'test.csv'})")
    print(f"  - Total Samples:  {len(dataset)}")

    return len(train_data), len(val_data), len(test_data)


if __name__ == "__main__":
    print("=" * 80)
    print(" [GENERATING 13-CLASS ENGINEERING ERROR CLASSIFICATION DATASET]")
    print("=" * 80)
    data = generate_balanced_dataset(samples_per_category=250)
    split_and_save_dataset(data)
