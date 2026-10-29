from pathlib import Path
import json
import shutil
import pytest
from policy_search.ingest import Chunk,extract_pages,chunk_pages,ingest
from policy_search.search import SearchIndex,ABSTAIN
from policy_search.api import APIClient

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def index():return SearchIndex(ingest(sorted((ROOT/"samples/text").glob("*.md"))))

def test_chunk_boundaries_preserve_source_pages():
    chunks=chunk_pages([(3,"one two three four five six seven","text"),(4,"eight nine","text")],"test.md",max_words=4,overlap=1)
    assert len(chunks)==3 and chunks[-1].page==4
    assert chunks[0].source=="test.md" and len({chunk.id for chunk in chunks})==3

def test_supported_answer_has_retrievable_page_citation(index):
    result=index.answer("How many days do I have for standard returns?")
    assert "30 days" in result["answer"]
    assert "returns.md · p. 1" in result["citations"]
    assert not result["abstained"]

def test_unrelated_and_empty_queries_abstain(index):
    assert index.answer("Who won the cricket tournament yesterday?")["abstained"]
    assert index.answer("")["answer"]==ABSTAIN

def test_related_but_unsupported_policy_questions_abstain(index):
    assert index.answer("What is the international delivery price?")["abstained"]
    assert index.answer("What warranty period applies to the rechargeable lamp?")["abstained"]

def test_faiss_search_limits_k_and_checks_backend(index):
    assert len(index.search("delivery",k=100))<=len(index.chunks)
    with pytest.raises(ValueError):index.search("delivery",k=0)
    with pytest.raises(ValueError):SearchIndex(index.chunks,"mystery")

def test_duplicate_filenames_rejected(tmp_path):
    a=tmp_path/"a";b=tmp_path/"b";a.mkdir();b.mkdir()
    for root in [a,b]:(root/"policy.md").write_text("Return within 30 days.")
    with pytest.raises(ValueError,match="unique"):ingest([a/"policy.md",b/"policy.md"])

def test_llm_invalid_citation_causes_abstention(index,monkeypatch):
    monkeypatch.setenv("LLM_API_KEY","test-key-not-real")
    monkeypatch.setattr(APIClient,"answer",lambda self,q,h:{"answer":"Unverified claim","citations":["invented.pdf · p. 99"],"abstain":False})
    assert index.answer("standard returns",mode="llm")["abstained"]

def test_llm_valid_citation_adapter(index,monkeypatch):
    monkeypatch.setenv("LLM_API_KEY","test-key-not-real")
    monkeypatch.setattr(APIClient,"answer",lambda self,q,h:{"answer":"Returns are accepted within 30 days.","citations":[h[0]["citation"]],"abstain":False})
    assert not index.answer("standard returns",mode="llm")["abstained"]

def test_live_api_is_explicit_and_https_only(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY",raising=False)
    with pytest.raises(ValueError,match="LLM_API_KEY"):APIClient()
    monkeypatch.setenv("LLM_API_KEY","test-key-not-real");monkeypatch.setenv("LLM_BASE_URL","http://example.invalid/v1")
    with pytest.raises(ValueError,match="HTTPS"):APIClient()

@pytest.mark.skipif(not shutil.which("tesseract"),reason="Tesseract is an optional system dependency")
def test_real_image_only_pdf_uses_ocr_and_preserves_page():
    pages=extract_pages(ROOT/"samples/pdf/product_guide.pdf")
    page=next(row for row in pages if row[0]==2)
    assert page[2]=="ocr" and "5V 2A" in page[1]
    index=SearchIndex(ingest([ROOT/"samples/pdf/product_guide.pdf"]))
    result=index.answer("What adapter charges the rechargeable lamp?")
    assert "product_guide.pdf · p. 2" in result["citations"]
