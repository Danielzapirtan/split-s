import argparse
import sys
import os
import fitz  # PyMuPDF
import google.generativeai as genai
from typing import List, Dict, Tuple
import re

def extract_text_from_pdf(pdf_path: str) -> Tuple[str, List[Dict]]:
    """
    Extract text from PDF with page numbers for context.
    Returns full text and list of page-wise text chunks.
    """
    try:
        doc = fitz.open(pdf_path)
        full_text = ""
        pages_text = []
        
        for page_num, page in enumerate(doc, 1):
            text = page.get_text()
            full_text += text + "\n\n"
            pages_text.append({
                "page": page_num,
                "text": text[:3000]  # Store first 3000 chars per page for context
            })
        
        doc.close()
        return full_text, pages_text
    except Exception as e:
        print(f"Error reading PDF: {e}", file=sys.stderr)
        sys.exit(1)

def sample_text_evenly(pages_text: List[Dict], max_chars: int = 15000) -> str:
    """
    Sample text evenly across pages to stay within token limits.
    """
    total_pages = len(pages_text)
    sampled_text = []
    
    # Distribute sampling across pages
    chars_per_page = max_chars // total_pages if total_pages > 0 else max_chars
    
    for page_info in pages_text:
        page_text = page_info["text"]
        if len(page_text) > chars_per_page:
            # Take beginning and end of long pages
            half = chars_per_page // 2
            sampled = f"[Page {page_info['page']}] ... {page_text[:half]} ... {page_text[-half:]} ..."
        else:
            sampled = f"[Page {page_info['page']}] {page_text}"
        sampled_text.append(sampled)
    
    # Join and trim if still too long
    result = "\n\n".join(sampled_text)
    if len(result) > max_chars:
        result = result[:max_chars] + "..."
    
    return result

def generate_toc_with_gemini(pdf_text: str, api_key: str) -> str:
    """
    Generate detailed TOC using Gemini API with minimal token usage.
    """
    # Configure Gemini
    genai.configure(api_key=api_key)
    
    # Use the most cost-effective model
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
    # Optimized prompt for minimal token usage
    prompt = f"""Analyze this academic chapter and create a detailed Table of Contents with section numbers.

CRITICAL RULES:
1. Use numbers with dots (e.g., 1, 1.1, 1.1.1, 2, 2.1, etc.)
2. Use AI to find section titles in the PDF even if they had not be numbered there

Output ONLY the TOC, no explanations.

CHAPTER TEXT:
{pdf_text}"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API error: {e}", file=sys.stderr)
        sys.exit(1)

def parse_and_format_toc(toc_text: str) -> str:
    """
    Clean and format the TOC output.
    """
    lines = toc_text.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Remove markdown formatting
        line = re.sub(r'[*_#]', '', line)
        
        # Ensure proper numbering format
        if re.match(r'^\d+(\.\d+)*\s+', line):
            formatted_lines.append(line)
        elif line:
            # If line doesn't start with numbers, try to infer
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)

def main():
    parser = argparse.ArgumentParser(
        description='Generate detailed TOC from PDF chapter using Gemini API'
    )
    parser.add_argument(
        '--pdf',
        required=True,
        help='Path to the PDF file'
    )
    parser.add_argument(
        '--api-key',
        help='Gemini API key (or set GEMINI_API_KEY environment variable)'
    )
    parser.add_argument(
        '--output',
        help='Output file (default: print to stdout)'
    )
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("Error: Gemini API key required. Set GEMINI_API_KEY env var or use --api-key", 
              file=sys.stderr)
        sys.exit(1)
    
    # Check if PDF exists
    if not os.path.exists(args.pdf):
        print(f"Error: PDF file not found: {args.pdf}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Processing PDF: {args.pdf}", file=sys.stderr)
    
    # Extract text from PDF
    print("Extracting text from PDF...", file=sys.stderr)
    full_text, pages_text = extract_text_from_pdf(args.pdf)
    
    # Sample text intelligently to minimize API quota usage
    print("Sampling text for API processing...", file=sys.stderr)
    sampled_text = sample_text_evenly(pages_text, max_chars=12000)  # ~3000 tokens
    
    # Generate TOC with Gemini
    print("Generating TOC with Gemini API...", file=sys.stderr)
    toc_raw = generate_toc_with_gemini(sampled_text, api_key)
    
    # Format the TOC
    toc_formatted = parse_and_format_toc(toc_raw)
    
    # Output results
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(toc_formatted)
        print(f"TOC written to: {args.output}", file=sys.stderr)
    else:
        print(toc_formatted)
    
    print("Done!", file=sys.stderr)

if __name__ == "__main__":
    main()
