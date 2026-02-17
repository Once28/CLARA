"""
Convert Clinical Trial Protocol PDFs to Raw Text Files for Model Inputs
"""

"""
Parse clinical trial protocol PDFs into raw text files.

Extracts text from each PDF in a directory and saves as .txt files,
ready to be pasted into RIP or fed into the pipeline programmatically.

Usage:
    # Parse all PDFs in a directory:
    python parse_protocols.py --input ./protocols --output ./parsed

    # Parse a single PDF:
    python parse_protocols.py --input ./protocols/NCT03196180_Prot_SAP_000.pdf --output ./parsed

    # Extract only specific sections relevant to FDA/CFR protocol auditing:
    python parse_protocols.py --input ./protocols --output ./parsed --sections

    # Output as JSON (one file per PDF with metadata):
    python parse_protocols.py --input ./protocols --output ./parsed --format json

Dependencies:
    pip install pymupdf
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: 'PyMuPDF' is required. Install it with: pip install pymupdf")
    sys.exit(1)


# Sections that are most relevant for FDA/CFR protocol auditing (Part 11, 50, 312, etc.).
# These keywords are matched against section headings in the protocol.
REGULATORY_SECTION_KEYWORDS = [
    # Data management and electronic records
    r"data\s+management",
    r"data\s+handling",
    r"data\s+collection",
    r"data\s+entry",
    r"data\s+quality",
    r"data\s+integrity",
    r"data\s+storage",
    r"data\s+retention",
    r"data\s+monitoring",
    r"electronic\s+data",
    r"electronic\s+record",
    r"electronic\s+case\s+report",
    r"e?crf",
    r"case\s+report\s+form",
    r"source\s+data",
    r"source\s+document",
    # Signatures and consent
    r"electronic\s+signature",
    r"informed\s+consent",
    r"consent\s+process",
    # Audit and compliance
    r"audit\s+trail",
    r"quality\s+assurance",
    r"quality\s+control",
    r"monitoring\s+plan",
    r"regulatory\s+compliance",
    r"regulatory\s+requirement",
    r"record\s+keeping",
    r"record\s+retention",
    # System validation
    r"system\s+validation",
    r"computer\s+system",
    r"software\s+validation",
    # Confidentiality and access
    r"confidentiality",
    r"access\s+control",
    r"user\s+access",
    r"security",
    r"password",
    # Sponsor and site responsibilities
    r"sponsor\s+responsibilit",
    r"investigator\s+responsibilit",
    r"site\s+responsibilit",
]

SECTION_PATTERN = re.compile(
    r"(" + "|".join(REGULATORY_SECTION_KEYWORDS) + r")",
    re.IGNORECASE,
)

# Pattern to detect section headings (e.g., "10.1 Data Management" or "SECTION 5: INFORMED CONSENT")
HEADING_PATTERN = re.compile(
    r"^[\s]*"
    r"(?:(?:section|appendix)\s*)?"
    r"(?:\d+\.?\d*\.?\d*\.?\s+)?"
    r"([A-Z][A-Za-z\s,/&\-\(\)]+)"
    r"\s*$",
    re.MULTILINE,
)


def extract_text_from_pdf(pdf_path):
    """Extract all text from a PDF file using PyMuPDF."""
    doc = fitz.open(pdf_path)
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if text.strip():
            pages.append({
                "page": page_num + 1,
                "text": text,
            })
    doc.close()
    return pages


def pages_to_full_text(pages):
    """Combine all pages into a single text string."""
    parts = []
    for p in pages:
        parts.append(f"--- Page {p['page']} ---")
        parts.append(p["text"])
    return "\n".join(parts)


def extract_sections(full_text):
    """
    Split the full text into sections based on detected headings.
    Returns a list of {"heading": str, "content": str} dicts.
    """
    lines = full_text.split("\n")
    sections = []
    current_heading = "PREAMBLE"
    current_lines = []

    for line in lines:
        # Check if this line looks like a section heading
        stripped = line.strip()
        if (
            stripped
            and len(stripped) < 120
            and not stripped.endswith(".")
            and re.match(r"^(?:\d+\.?\d*\.?\d*\.?\s+)?[A-Z]", stripped)
            and sum(1 for c in stripped if c.isupper()) > len(stripped) * 0.3
        ):
            # Save previous section
            if current_lines:
                sections.append({
                    "heading": current_heading,
                    "content": "\n".join(current_lines),
                })
            current_heading = stripped
            current_lines = []
        else:
            current_lines.append(line)

    # Save last section
    if current_lines:
        sections.append({
            "heading": current_heading,
            "content": "\n".join(current_lines),
        })

    return sections


def filter_regulatory_sections(sections):
    """Filter sections to only those relevant to FDA/CFR protocol auditing."""
    relevant = []
    for section in sections:
        heading_lower = section["heading"].lower()
        content_preview = section["content"][:500].lower()
        combined = heading_lower + " " + content_preview

        if SECTION_PATTERN.search(combined):
            relevant.append(section)

    return relevant


def extract_nct_id(filename):
    """Try to extract NCT ID from filename."""
    match = re.search(r"(NCT\d{8})", filename, re.IGNORECASE)
    return match.group(1) if match else None


def clean_text(text):
    """Clean extracted text: fix common PDF extraction artifacts."""
    # Collapse multiple blank lines
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    # Fix hyphenated line breaks (e.g., "investi-\ngator" -> "investigator")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # Remove form feed characters
    text = text.replace("\x0c", "\n")
    return text.strip()


def process_single_pdf(pdf_path, output_dir, extract_sections_flag, output_format):
    """Process a single PDF and write output files."""
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    nct_id = extract_nct_id(pdf_path.name) or pdf_path.stem

    # Extract text
    try:
        pages = extract_text_from_pdf(pdf_path)
    except Exception as e:
        return {"file": pdf_path.name, "status": "FAIL", "error": str(e)}

    if not pages:
        return {"file": pdf_path.name, "status": "SKIP", "error": "No text extracted"}

    full_text = pages_to_full_text(pages)
    full_text = clean_text(full_text)
    total_pages = len(pages)
    total_chars = len(full_text)

    if output_format == "json":
        # JSON output with metadata
        output = {
            "nct_id": nct_id,
            "source_file": pdf_path.name,
            "total_pages": total_pages,
            "total_characters": total_chars,
        }

        if extract_sections_flag:
            sections = extract_sections(full_text)
            regulatory = filter_regulatory_sections(sections)
            output["all_sections_count"] = len(sections)
            output["regulatory_sections_count"] = len(regulatory)
            output["regulatory_sections"] = [
                {"heading": s["heading"], "content": s["content"]}
                for s in regulatory
            ]
            # Also include full text for reference
            output["full_text"] = full_text
        else:
            output["full_text"] = full_text

        out_path = output_dir / f"{nct_id}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

    else:
        # Plain text output
        if extract_sections_flag:
            sections = extract_sections(full_text)
            regulatory = filter_regulatory_sections(sections)

            # Write full text
            full_path = output_dir / f"{nct_id}_full.txt"
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(full_text)

            # Write regulatory sections only
            if regulatory:
                reg_path = output_dir / f"{nct_id}_regulatory_sections.txt"
                with open(reg_path, "w", encoding="utf-8") as f:
                    f.write(f"# Regulatory-Relevant Sections from {nct_id}\n")
                    f.write(f"# Extracted {len(regulatory)} of {len(sections)} total sections\n")
                    f.write(f"# Source: {pdf_path.name}\n")
                    f.write("=" * 80 + "\n\n")
                    for section in regulatory:
                        f.write(f"## {section['heading']}\n")
                        f.write("-" * 60 + "\n")
                        f.write(section["content"])
                        f.write("\n\n" + "=" * 80 + "\n\n")

            return {
                "file": pdf_path.name,
                "nct_id": nct_id,
                "status": "OK",
                "pages": total_pages,
                "chars": total_chars,
                "sections": len(sections),
                "regulatory_sections": len(regulatory),
            }
        else:
            out_path = output_dir / f"{nct_id}.txt"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(full_text)

    return {
        "file": pdf_path.name,
        "nct_id": nct_id,
        "status": "OK",
        "pages": total_pages,
        "chars": total_chars,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Parse clinical trial protocol PDFs into raw text"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to a PDF file or directory of PDFs"
    )
    parser.add_argument(
        "--output", "-o",
        default="./parsed",
        help="Output directory for text files (default: ./parsed)"
    )
    parser.add_argument(
        "--sections", "-s",
        action="store_true",
        help="Extract and filter sections relevant to FDA/CFR protocol auditing"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["txt", "json"],
        default="txt",
        help="Output format: txt (default) or json"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect PDF files
    if input_path.is_file() and input_path.suffix.lower() == ".pdf":
        pdf_files = [input_path]
    elif input_path.is_dir():
        pdf_files = sorted(input_path.glob("*.pdf"))
    else:
        print(f"Error: {input_path} is not a PDF file or directory")
        sys.exit(1)

    if not pdf_files:
        print(f"No PDF files found in {input_path}")
        sys.exit(1)

    print(f"Found {len(pdf_files)} PDF(s)")
    print(f"Output directory: {output_dir.resolve()}")
    print(f"Section extraction: {'ON' if args.sections else 'OFF'}")
    print(f"Output format: {args.format}")
    print()

    # Header
    if args.sections:
        print(f"{'NCT ID':<18} {'Status':<8} {'Pages':>6} {'Chars':>9} {'Sections':>9} {'Regulatory':>11}")
    else:
        print(f"{'NCT ID':<18} {'Status':<8} {'Pages':>6} {'Chars':>9}")
    print("-" * 72)

    # Process each PDF
    results = []
    for pdf_path in pdf_files:
        result = process_single_pdf(pdf_path, output_dir, args.sections, args.format)
        results.append(result)

        if result["status"] == "OK":
            if args.sections and "regulatory_sections" in result:
                print(
                    f"{result.get('nct_id','?'):<18} "
                    f"{result['status']:<8} "
                    f"{result['pages']:>6} "
                    f"{result['chars']:>9,} "
                    f"{result.get('sections', '?'):>9} "
                    f"{result.get('regulatory_sections', '?'):>11}"
                )
            else:
                print(
                    f"{result.get('nct_id','?'):<18} "
                    f"{result['status']:<8} "
                    f"{result['pages']:>6} "
                    f"{result['chars']:>9,}"
                )
        else:
            print(f"{result.get('nct_id', result['file']):<18} {result['status']:<8} {result.get('error', '')}")

    # Summary
    ok = sum(1 for r in results if r["status"] == "OK")
    print("-" * 72)
    print(f"\nProcessed: {ok}/{len(results)} PDFs successfully")
    print(f"Output: {output_dir.resolve()}")

    if args.sections:
        total_reg = sum(r.get("regulatory_sections", 0) for r in results if r["status"] == "OK")
        print(f"Total regulatory sections extracted: {total_reg}")

    # Write manifest
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()