"""Extract page-aware text and OCR image-only PDF pages."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib
import re
import shutil
from pypdf import PdfReader

@dataclass(frozen=True)
class Chunk:
    id: str
    source: str
    page: int
    text: str
    extraction: str

    def to_dict(self):return asdict(self)

def extract_pages(path,max_pages=50):
    path=Path(path)
    if path.stat().st_size>20*1024*1024:raise ValueError("Maximum input size is 20 MB")
    if path.suffix.lower() in {".txt",".md"}:
        pages=path.read_text(encoding="utf-8").split("\f")
        if len(pages)>max_pages:raise ValueError(f"Maximum page count is {max_pages}")
        return [(index+1,text.strip(),"text") for index,text in enumerate(pages) if text.strip()]
    if path.suffix.lower()!=".pdf":raise ValueError("Supported documents: PDF, TXT, MD")
    reader=PdfReader(path)
    if reader.is_encrypted:raise ValueError("Encrypted PDFs are not supported")
    if len(reader.pages)>max_pages:raise ValueError(f"Maximum page count is {max_pages}")
    pages=[]
    for index,page in enumerate(reader.pages):
        text=(page.extract_text() or "").strip();method="pdf_text"
        if len(re.sub(r"\s","",text))<30:
            if not shutil.which("tesseract"):
                raise RuntimeError("This PDF requires OCR. Install Tesseract or use the Docker image.")
            import pypdfium2 as pdfium
            import pytesseract
            with pdfium.PdfDocument(path) as document:
                bitmap=document[index].render(scale=2.5)
                try:text=pytesseract.image_to_string(bitmap.to_pil(),lang="eng",timeout=30).strip()
                finally:bitmap.close()
            method="ocr"
        if text:pages.append((index+1,text,method))
    if not pages:raise ValueError("No readable text extracted")
    return pages

def chunk_pages(pages,source,max_words=110,overlap=20):
    if max_words<1 or overlap<0 or overlap>=max_words:raise ValueError("Invalid chunk window")
    result=[]
    for page,text,method in pages:
        words=text.split()
        for start in range(0,len(words),max_words-overlap):
            passage=" ".join(words[start:start+max_words])
            if not passage:continue
            identity=hashlib.sha256(f"{source}:{page}:{start}:{passage}".encode()).hexdigest()[:16]
            result.append(Chunk(identity,source,page,passage,method))
            if start+max_words>=len(words):break
    return result

def ingest(paths):
    chunks=[]
    if len(paths)>20:raise ValueError("Maximum 20 documents per index")
    names=[Path(path).name for path in paths]
    if len(names)!=len(set(names)):raise ValueError("Document filenames must be unique for unambiguous citations")
    for path in paths:chunks.extend(chunk_pages(extract_pages(path),Path(path).name))
    if not chunks:raise ValueError("No documents to index")
    return chunks
