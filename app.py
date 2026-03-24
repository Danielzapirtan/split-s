import PyPDF2
import re
import random
import os

maxlevel = 1
_MAXVALUE = 20000
input_path = '/content/drive/MyDrive/boox/Chain.pdf'
output_path = '/content/drive/MyDrive/output_dir'

# Fixed: Added random import and proper function
def eval(page):
    value = 0
    text = page.extract_text()
    if re.match(r'^\d+$', text):
        value += 300
        if re.match(r'FIGURE', text):
            value -= 500
    line_0 = text
    if '\n' in text:
        line_0 = text.split('\n')[0]
    if re.match(r'\s*Chapter\s+\d+', line_0):
        value += 900
    if re.match(r'CHAPTER', line_0):
        value += 900
    if re.match(r'^\s*\d+\s', line_0):
        value -= 400
    if re.match(r'\s\d+\s*$', line_0):
        value -= 400
    value += random.randint(0, 98) - 49
    return value

def minimax(reader):
    pagelist = reader.pages
    valuelist = []
    num_chapters = 15
    
    for i, page in enumerate(pagelist):
        value = eval(page)
        valuelist.append([value, i])
    
    valuelist = sorted(valuelist)[:num_chapters]
    chapter_delimiters = []
    for pair in valuelist:
        chapter_delimiters.append(pair[1])
    
    return sorted(chapter_delimiters)

# Fixed: Main execution block
if __name__ == "__main__":
    reader = PyPDF2.PdfReader(input_path)
    pagelist = reader.pages
    chapter_delimiters = minimax(reader)
    
    os.makedirs(output_path, exist_ok=True)
    
    max_pages = len(pagelist)
    num_chapters = len(chapter_delimiters)
    
    for i in range(num_chapters):
        writer = PyPDF2.PdfWriter()
        first_page = chapter_delimiters[i]
        last_page = chapter_delimiters[i + 1] - 1 if i < num_chapters - 1 else max_pages - 1
        
        for page_num in range(first_page, last_page + 1):
            if page_num < max_pages:
                writer.add_page(pagelist[page_num])
        
        chapter_filename = f"{output_path}/chapter_{i+1:03d}.pdf"
        with open(chapter_filename, "wb") as output_file:
            writer.write(output_file)
        
        print(f"Created chapter {i+1}: pages {first_page+1}-{last_page+1}")

print(f"Done! Split PDF into {num_chapters} chapters in {output_path}")
