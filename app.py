# app.py

import argparse
import json
import re
from collections import defaultdict

import pdfplumber
from sklearn.feature_extraction.text import TfidfVectorizer


# -------------------------
# Heuristics
# -------------------------

HEADING_PATTERNS = [
    r"^(chapter|capitolul)\s+\d+",
    r"^\d+\.",
    r"^\d+\.\d+",
    r"^\d+\.\d+\.\d+",
]

MAX_HEADING_WORDS = 18
MIN_HEADING_SIZE_DELTA = 0.5


def is_heading(text, size, avg_size):
    t = text.strip()
    if not t:
        return False

    if len(t.split()) > MAX_HEADING_WORDS:
        return False

    for p in HEADING_PATTERNS:
        if re.match(p, t.lower()):
            return True

    if size >= avg_size + MIN_HEADING_SIZE_DELTA:
        return True

    if t.isupper():
        return True

    return False


def clean_line(text):
    return re.sub(r"\s+", " ", text).strip()


# -------------------------
# PDF Parsing
# -------------------------

def extract_lines(pdf_path):
    lines = []
    sizes = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            words = page.extract_words(extra_attrs=["size", "fontname"])

            current_line = []
            current_y = None

            for w in words:
                if current_y is None:
                    current_y = w["top"]

                if abs(w["top"] - current_y) > 3:
                    if current_line:
                        text = " ".join([x["text"] for x in current_line])
                        avg_size = sum(x["size"] for x in current_line) / len(current_line)
                        lines.append((clean_line(text), avg_size, page_num))
                        sizes.append(avg_size)
                    current_line = []
                    current_y = w["top"]

                current_line.append(w)

            if current_line:
                text = " ".join([x["text"] for x in current_line])
                avg_size = sum(x["size"] for x in current_line) / len(current_line)
                lines.append((clean_line(text), avg_size, page_num))
                sizes.append(avg_size)

    global_avg = sum(sizes) / len(sizes) if sizes else 10
    return lines, global_avg


# -------------------------
# Summarization
# -------------------------

def summarize_block(text, n_sent=2):
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) <= n_sent:
        return text

    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(sentences)
    scores = X.sum(axis=1)

    ranked = sorted(
        [(i, scores[i, 0]) for i in range(len(sentences))],
        key=lambda x: x[1],
        reverse=True,
    )

    selected = sorted(i for i, _ in ranked[:n_sent])
    return " ".join(sentences[i] for i in selected)


# -------------------------
# TOC Builder
# -------------------------

def detect_level(text):
    m = re.match(r"^(\d+(\.\d+)*)", text)
    if m:
        return m.group(1).count(".") + 1

    if text.isupper():
        return 1

    return 2


def build_toc(lines, avg_size, summarize=False):
    toc = []
    stack = []

    current_block = []
    current_node = None

    for text, size, page in lines:
        if is_heading(text, size, avg_size):
            if current_node and summarize:
                current_node["summary"] = summarize_block(" ".join(current_block))
            current_block = []

            level = detect_level(text)
            node = {
                "title": text,
                "page": page + 1,
                "level": level,
                "children": [],
            }

            while stack and stack[-1]["level"] >= level:
                stack.pop()

            if stack:
                stack[-1]["children"].append(node)
            else:
                toc.append(node)

            stack.append(node)
            current_node = node
        else:
            current_block.append(text)

    if current_node and summarize:
        current_node["summary"] = summarize_block(" ".join(current_block))

    return toc


# -------------------------
# CLI / Input
# -------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", help="Path to PDF")
    parser.add_argument("--out", default="toc.json")
    parser.add_argument("--summarize", action="store_true")

    args = parser.parse_args()

    pdf_path = args.pdf or input("PDF path: ").strip()
    out_path = args.out or input("Output file [toc.json]: ").strip() or "toc.json"

    if args.summarize:
        summarize = True
    else:
        s = input("Summarize paragraphs? (y/n): ").lower().strip()
        summarize = s == "y"

    lines, avg_size = extract_lines(pdf_path)
    toc = build_toc(lines, avg_size, summarize)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(toc, f, ensure_ascii=False, indent=2)

    print(f"Saved TOC to {out_path}")


if __name__ == "__main__":
    main()