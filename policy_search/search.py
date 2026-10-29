"""Normalized vectors + exact FAISS cosine search, with source-bound answers."""
from dataclasses import asdict
import re
import faiss
import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer,ENGLISH_STOP_WORDS
import snowballstemmer
from .api import APIClient

ABSTAIN="I could not find enough support in these documents to answer that question."
STEMMER=snowballstemmer.stemmer("english")
QUESTION_WORDS={"long","soon","many","much","need","using","use","apply","applies","tell","please","does","did","would","could"}
ALIASES={"temperature":"degrees","cost":"price","costs":"price"}

def terms(text):
    words=[ALIASES.get(word,word) for word in re.findall(r"\b[a-z0-9]+\b",text.lower())
           if word not in ENGLISH_STOP_WORDS and word not in QUESTION_WORDS]
    return STEMMER.stemWords(words)

class SearchIndex:
    def __init__(self,chunks,backend="local"):
        if not chunks:raise ValueError("Index needs at least one chunk")
        if backend not in {"local","api"}:raise ValueError("Embedding backend must be local or api")
        self.chunks=chunks;self.backend=backend
        # Transparent offline baseline: hashed lexical embeddings, not a neural semantic model.
        self.vectorizer=HashingVectorizer(n_features=2048,alternate_sign=False,tokenizer=terms,
            token_pattern=None,ngram_range=(1,2),norm="l2",lowercase=False)
        self.vocabulary=set(word for chunk in chunks for word in terms(chunk.text))
        self.api=APIClient() if backend=="api" else None
        vectors=self.embed([chunk.text for chunk in chunks])
        self.index=faiss.IndexFlatIP(vectors.shape[1]);self.index.add(vectors)

    def embed(self,texts):
        vectors=self.api.embed(texts) if self.api else self.vectorizer.transform(texts).toarray().astype(np.float32)
        vectors=np.ascontiguousarray(vectors,dtype=np.float32)
        if vectors.ndim!=2 or len(vectors)!=len(texts) or not np.isfinite(vectors).all():
            raise ValueError("Invalid embedding response")
        faiss.normalize_L2(vectors)
        return vectors

    def search(self,question,k=3,min_score=.16):
        if not question.strip():return []
        if k<1:raise ValueError("k must be positive")
        scores,positions=self.index.search(self.embed([question]),min(k,len(self.chunks)))
        result=[]
        for score,position in zip(scores[0],positions[0]):
            if position<0 or score<min_score:continue
            chunk=self.chunks[int(position)]
            result.append({**asdict(chunk),"score":float(score),"citation":f"{chunk.source} · p. {chunk.page}"})
        return result

    def answer(self,question,mode="offline",k=3,min_score=.16):
        if mode not in {"offline","llm"}:raise ValueError("Answer mode must be offline or llm")
        hits=self.search(question,k,min_score)
        if not hits:return {"answer":ABSTAIN,"citations":[],"abstained":True,"mode":mode,"evidence":[]}
        # Conservative offline guard: unfamiliar concepts (e.g. warranty) cannot
        # be answered simply because another word (e.g. lamp) matches a passage.
        # This intentionally sacrifices paraphrase recall; it is not entailment.
        unknown=set(terms(question))-self.vocabulary
        if mode=="offline" and unknown:
            return {"answer":ABSTAIN,"citations":[],"abstained":True,"mode":mode,"evidence":hits,
                    "note":"Some query concepts are absent from the corpus; offline mode abstains conservatively."}
        if mode=="llm":
            response=(self.api or APIClient()).answer(question,hits)
            answer=response.get("answer");citations=response.get("citations");abstain=response.get("abstain")
            valid={hit["citation"] for hit in hits}
            supported=(abstain is False and isinstance(answer,str) and bool(answer.strip())
                and isinstance(citations,list) and bool(citations)
                and all(isinstance(c,str) and c in valid for c in citations))
            if not supported:
                return {"answer":ABSTAIN,"citations":[],"abstained":True,"mode":mode,"evidence":hits,
                        "note":"Model response abstained or failed citation validation."}
            # Citation validation does not prove entailment. Show evidence for human verification.
            return {"answer":answer,"citations":list(dict.fromkeys(citations)),"abstained":False,"mode":mode,"evidence":hits}
        # Quote exact source sentences. This cannot introduce new factual claims, but
        # retrieval can still be irrelevant; the evaluation reports such failures.
        candidates=[]
        for hit in hits:
            sentences=re.split(r"(?<=[.!?])\s+",hit["text"])
            scores=(self.vectorizer.transform(sentences) @ self.vectorizer.transform([question]).T).toarray().ravel()
            for sentence,score in zip(sentences,scores):
                if score>0:candidates.append((float(score),sentence,hit["citation"]))
        candidates.sort(key=lambda item:item[0],reverse=True)
        chosen=[];seen=set()
        for score,sentence,citation in candidates:
            if sentence in seen:continue
            chosen.append((sentence,citation));seen.add(sentence)
            if len(chosen)==2:break
        if not chosen:return {"answer":ABSTAIN,"citations":[],"abstained":True,"mode":mode,"evidence":hits}
        return {"answer":"\n\n".join(f"{sentence} [{citation}]" for sentence,citation in chosen),
            "citations":list(dict.fromkeys(citation for _,citation in chosen)),"abstained":False,"mode":mode,"evidence":hits}

    def summarize(self,source,max_sentences=3):
        chunks=[chunk for chunk in self.chunks if chunk.source==source]
        if not chunks:raise ValueError("Unknown source")
        result=[];seen=set()
        for chunk in chunks:
            for sentence in re.split(r"(?<=[.!?])\s+",chunk.text):
                if sentence not in seen:
                    result.append(f"{sentence} [{source} · p. {chunk.page}]");seen.add(sentence)
                    break
            if len(result)>=max_sentences:break
        return "\n\n".join(result)
