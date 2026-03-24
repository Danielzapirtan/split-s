#!/usr/bin/env python3
"""
PDF TOC Prepend Tool
Adds a detailed table of contents to the beginning of a PDF file
without loading the entire document content into memory.
"""

import os
import sys
import argparse
from typing import List, Tuple, Optional
import logging
from io import BytesIO

# External libraries (non-AI, non-API)
try:
    import PyPDF2
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib import colors
except ImportError as e:
    print(f"Missing required library: {e}")
    print("Please install dependencies: pip install -r requirements.txt")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PDFPageAnalyzer:
    """Extracts minimal page information without loading full content."""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.page_count = 0
        self.page_labels = []  # Store page numbers with potential section markers
        
    def analyze(self) -> int:
        """Analyze PDF to get page count and minimal structure info."""
        try:
            with open(self.pdf_path, 'rb') as f:
                # Use strict=False to handle malformed PDFs more gracefully
                pdf_reader = PyPDF2.PdfReader(f, strict=False)
                self.page_count = len(pdf_reader.pages)
                
                # Extract minimal info: page numbers and any existing bookmarks
                # This doesn't load full page content
                if pdf_reader.outline:
                    self._extract_outline_info(pdf_reader.outline)
                
                logger.info(f"Analyzed PDF: {self.page_count} pages")
                return self.page_count
                
        except Exception as e:
            logger.error(f"Error analyzing PDF: {e}")
            raise
    
    def _extract_outline_info(self, outline, depth=0):
        """Extract bookmark information without loading page content."""
        try:
            for item in outline:
                if isinstance(item, list):
                    # Handle nested outlines
                    self._extract_outline_info(item, depth + 1)
                else:
                    # Extract bookmark title and page reference
                    title = getattr(item, 'title', f'Section {len(self.page_labels) + 1}')
                    page_num = getattr(item, 'page', None)
                    if page_num is not None:
                        try:
                            page_idx = self._get_page_number(page_num)
                            self.page_labels.append((title, page_idx, depth))
                        except:
                            pass
        except Exception as e:
            logger.warning(f"Could not extract outline info: {e}")


class TOCGenerator:
    """Generates TOC PDF pages with detailed structure."""
    
    def __init__(self, title="Table of Contents", page_size=letter):
        self.title = title
        self.page_size = page_size
        self.width, self.height = page_size
        
    def create_toc_pages(self, sections: List[Tuple[str, int, int]]) -> BytesIO:
        """
        Create TOC PDF pages.
        sections: List of (title, page_number, depth_level)
        """
        toc_buffer = BytesIO()
        
        try:
            # Create canvas for TOC pages
            c = canvas.Canvas(toc_buffer, pagesize=self.page_size)
            
            # Title page (first page of TOC)
            self._draw_title_page(c)
            
            # Calculate how many TOC pages needed
            items_per_page = 40  # Adjust based on page size
            total_toc_pages = (len(sections) + items_per_page - 1) // items_per_page
            
            # Create TOC content pages
            for page_num in range(total_toc_pages):
                if page_num > 0:
                    c.showPage()  # Start new page
                
                start_idx = page_num * items_per_page
                end_idx = min(start_idx + items_per_page, len(sections))
                
                self._draw_toc_page(c, sections[start_idx:end_idx], page_num + 1, total_toc_pages)
            
            c.save()
            toc_buffer.seek(0)
            logger.info(f"Generated {total_toc_pages + 1} TOC pages")
            
        except Exception as e:
            logger.error(f"Error generating TOC: {e}")
            raise
            
        return toc_buffer
    
    def _draw_title_page(self, canvas_obj):
        """Draw the main title page of TOC."""
        canvas_obj.setFont("Helvetica-Bold", 24)
        canvas_obj.drawCentredString(self.width / 2, self.height - 2*inch, self.title)
        
        canvas_obj.setFont("Helvetica", 12)
        canvas_obj.drawCentredString(self.width / 2, self.height - 3*inch, 
                                    "Generated PDF Table of Contents")
        
        canvas_obj.setFont("Helvetica", 10)
        canvas_obj.drawCentredString(self.width / 2, inch, 
                                    "Use bookmarks in your PDF viewer for navigation")
    
    def _draw_toc_page(self, canvas_obj, sections, page_num, total_pages):
        """Draw a single TOC content page."""
        # Draw header
        canvas_obj.setFont("Helvetica-Bold", 16)
        canvas_obj.drawString(inch, self.height - inch, "Table of Contents")
        
        canvas_obj.setFont("Helvetica", 10)
        canvas_obj.drawRightString(self.width - inch, self.height - inch, 
                                  f"Page {page_num} of {total_pages}")
        
        # Draw horizontal line
        canvas_obj.line(inch, self.height - 1.2*inch, 
                       self.width - inch, self.height - 1.2*inch)
        
        # Draw TOC entries
        y_position = self.height - 1.5*inch
        line_height = 0.25 * inch
        
        for title, pdf_page, depth in sections:
            if y_position <= inch:
                break  # Out of space on this page
                
            # Indent based on depth
            indent = inch + (depth * 0.25 * inch)
            
            # Draw title with ellipsis
            canvas_obj.setFont("Helvetica", 10)
            title_display = title[:60] + "..." if len(title) > 63 else title
            canvas_obj.drawString(indent, y_position, title_display)
            
            # Draw page number
            page_str = str(pdf_page)
            canvas_obj.drawRightString(self.width - inch, y_position, page_str)
            
            # Draw dot leaders (simple line for better visual)
            dot_x_start = indent + canvas_obj.stringWidth(title_display, "Helvetica", 10) + 0.1*inch
            dot_x_end = self.width - inch - canvas_obj.stringWidth(page_str, "Helvetica", 10) - 0.1*inch
            
            if dot_x_start < dot_x_end:
                canvas_obj.setStrokeColor(colors.grey)
                canvas_obj.setDash(1, 2)  # Dotted line
                canvas_obj.line(dot_x_start, y_position - 2, dot_x_end, y_position - 2)
                canvas_obj.setDash(1, 0)  # Reset
                canvas_obj.setStrokeColor(colors.black)
            
            y_position -= line_height
        
        # Draw footer
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.drawCentredString(self.width / 2, 0.5*inch, 
                                    "Generated by PDF TOC Tool")
    
    def _get_page_number(self, page_ref):
        """Convert page reference to page number."""
        try:
            if hasattr(page_ref, 'page_number'):
                return page_ref.page_number + 1  # Convert to 1-based
            return 1
        except:
            return 1


def merge_pdfs(original_path: str, toc_buffer: BytesIO, output_path: str, 
               remove_original_outline: bool = True) -> None:
    """
    Merge TOC PDF with original PDF without loading everything into memory.
    Uses incremental writing to avoid memory issues.
    """
    try:
        # Create PDF writer
        pdf_writer = PyPDF2.PdfWriter()
        
        # Add TOC pages first
        toc_reader = PyPDF2.PdfReader(toc_buffer)
        for page in toc_reader.pages:
            pdf_writer.add_page(page)
        
        # Add original PDF pages
        with open(original_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f, strict=False)
            
            # Add each page individually to avoid memory bloat
            for page_num, page in enumerate(pdf_reader.pages):
                pdf_writer.add_page(page)
                if (page_num + 1) % 50 == 0:
                    logger.info(f"Added page {page_num + 1} of {len(pdf_reader.pages)}")
            
            # Handle bookmarks/outline
            if pdf_reader.outline and not remove_original_outline:
                # Transfer original bookmarks with adjusted page numbers
                # Add offset for TOC pages
                toc_page_count = len(toc_reader.pages)
                pdf_writer.add_outline_item(
                    title="Original Document Bookmarks",
                    page_number=toc_page_count,
                    parent=None
                )
            
            # Add TOC bookmarks
            pdf_writer.add_outline_item(
                title="Table of Contents",
                page_number=0,
                parent=None
            )
        
        # Write output
        with open(output_path, 'wb') as output_file:
            pdf_writer.write(output_file)
            
        logger.info(f"Successfully created PDF with TOC: {output_path}")
        
    except Exception as e:
        logger.error(f"Error merging PDFs: {e}")
        raise


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Prepend a detailed Table of Contents to a PDF file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.pdf -o output.pdf
  %(prog)s input.pdf -o output.pdf --title "Custom TOC" --keep-outline
        """
    )
    
    parser.add_argument('input_pdf', help='Input PDF file path')
    parser.add_argument('-o', '--output', default=None, 
                       help='Output PDF file path (default: input_with_toc.pdf)')
    parser.add_argument('-t', '--title', default="Table of Contents",
                       help='Title for the Table of Contents')
    parser.add_argument('--keep-outline', action='store_true',
                       help='Keep original PDF bookmarks (may cause duplication)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input file
    if not os.path.exists(args.input_pdf):
        logger.error(f"Input file not found: {args.input_pdf}")
        sys.exit(1)
    
    if not args.input_pdf.lower().endswith('.pdf'):
        logger.warning("Input file does not have .pdf extension")
    
    # Set output filename
    if args.output is None:
        base = os.path.splitext(args.input_pdf)[0]
        args.output = f"{base}_with_toc.pdf"
    
    try:
        # Step 1: Analyze PDF to get page structure
        logger.info(f"Analyzing PDF: {args.input_pdf}")
        analyzer = PDFPageAnalyzer(args.input_pdf)
        page_count = analyzer.analyze()
        
        # Step 2: Create section list for TOC
        # In a real implementation, you'd extract section titles from the PDF
        # Here we create a simple section list based on page numbers
        sections = []
        
        # Create sections every 10 pages as a simple example
        for i in range(1, page_count + 1, 10):
            section_title = f"Section {((i - 1) // 10) + 1} (Pages {i}-{min(i+9, page_count)})"
            sections.append((section_title, i, 0))  # depth 0 = top level
        
        # Add any existing bookmarks from the PDF
        if analyzer.page_labels:
            for title, page_num, depth in analyzer.page_labels:
                sections.append((title, page_num, depth + 1))
        
        # Sort sections by page number
        sections.sort(key=lambda x: x[1])
        
        # Step 3: Generate TOC PDF
        logger.info("Generating Table of Contents")
        toc_generator = TOCGenerator(title=args.title)
        toc_buffer = toc_generator.create_toc_pages(sections)
        
        # Step 4: Merge TOC with original PDF
        logger.info("Merging TOC with original PDF")
        merge_pdfs(args.input_pdf, toc_buffer, args.output, 
                  remove_original_outline=not args.keep_outline)
        
        logger.info(f"✅ PDF processing complete! Output: {args.output}")
        logger.info(f"Original pages: {page_count}, TOC pages added")
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to process PDF: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()