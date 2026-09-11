"""
Report Formatting & Text Layout Utilities.

Provides clean Markdown tables, summary stat card formatting,
and review audit report rendering for drawing review intelligence.

Author: satyajeetvirkar22 <satyajeetvirkar22@gmail.com>
"""

from typing import List, Dict, Any, Optional


def format_markdown_table(headers: List[str], rows: List[List[Any]]) -> str:
    """Generates a clean GitHub-flavored Markdown table from headers and row data.
    
    Args:
        headers: List of column header strings.
        rows: List of row lists.
        
    Returns:
        Formatted Markdown table string.
    """
    if not headers:
        return ""

    # Convert all cell elements to string
    str_rows = [[str(cell) if cell is not None else "" for cell in row] for row in rows]
    
    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in str_rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))

    # Header line
    header_line = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    # Separator line
    separator_line = "| " + " | ".join("-" * col_widths[i] for i in range(len(headers))) + " |"
    
    # Data lines
    data_lines = []
    for row in str_rows:
        padded_cells = [row[i].ljust(col_widths[i]) if i < len(row) else "".ljust(col_widths[i]) for i in range(len(headers))]
        data_lines.append("| " + " | ".join(padded_cells) + " |")

    return "\n".join([header_line, separator_line] + data_lines)


def format_summary_card(title: str, metrics: Dict[str, Any], border_char: str = "=") -> str:
    """Formats a structured summary stat card for terminal logging or plain-text exports.
    
    Args:
        title: Title of the summary card.
        metrics: Dictionary of metric key-value pairs.
        border_char: Character used for border decoration.
        
    Returns:
        Formatted text string.
    """
    lines = []
    width = max(len(title) + 8, 45)
    border = border_char * width
    
    lines.append(border)
    lines.append(f"  {title.upper()}")
    lines.append(border)
    
    for key, val in metrics.items():
        formatted_key = key.replace("_", " ").title()
        lines.append(f"  • {formatted_key:<25}: {val}")
        
    lines.append(border)
    return "\n".join(lines)
