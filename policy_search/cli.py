import argparse
import json
from pathlib import Path
from .ingest import ingest
from .search import SearchIndex

ROOT=Path(__file__).resolve().parents[1]
RESOURCES=Path(__file__).resolve().parent/"resources"
DEFAULT_DOCS=ROOT/"samples/text" if (ROOT/"samples/text").exists() else RESOURCES/"text"
QUESTIONS=ROOT/"evaluation/questions.json" if (ROOT/"evaluation/questions.json").exists() else RESOURCES/"questions.json"

def evaluate(output):
    cases=json.loads(QUESTIONS.read_text())
    index=SearchIndex(ingest(sorted(DEFAULT_DOCS.glob("*.md"))))
    rows=[]
    for case in cases:
        result=index.answer(case["question"])
        hit=any(e["source"]==case.get("source") and e["page"]==case.get("page") for e in result["evidence"])
        keyword=any(term.lower() in result["answer"].lower() for term in case.get("answer_contains",[]))
        rows.append({**case,"answer":result["answer"],"abstained":result["abstained"],
            "retrieval_hit_at_3":hit if case["answerable"] else None,
            "answer_keyword_pass":keyword if case["answerable"] else None,
            "correct_abstention":result["abstained"] if not case["answerable"] else None,
            "citations":result["citations"]})
    known=[row for row in rows if row["answerable"]];unknown=[row for row in rows if not row["answerable"]]
    summary={"mode":"offline lexical embeddings + FAISS + extractive answers","questions":len(rows),
        "answerable_questions":len(known),"unanswerable_questions":len(unknown),
        "retrieval_recall_at_3":sum(row["retrieval_hit_at_3"] for row in known)/len(known),
        "answer_keyword_pass_rate":sum(row["answer_keyword_pass"] for row in known)/len(known),
        "unanswerable_abstention_rate":sum(row["correct_abstention"] for row in unknown)/len(unknown),
        "minimum_cosine_score":.16,"llm_api_tested_live":False,
        "warning":"Small fixed development set, not an unbiased benchmark. Keyword checks are not semantic accuracy; inspect the per-question answers."}
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    (output/"evaluation.json").write_text(json.dumps({"summary":summary,"questions":rows},indent=2)+"\n")
    print(json.dumps(summary,indent=2))

def main(argv=None):
    parser=argparse.ArgumentParser(description="Page-cited retail policy retrieval")
    commands=parser.add_subparsers(dest="command",required=True)
    ask=commands.add_parser("ask");ask.add_argument("question")
    ask.add_argument("--documents",type=Path,default=DEFAULT_DOCS)
    ask.add_argument("--mode",choices=["offline","llm"],default="offline")
    ask.add_argument("--embeddings",choices=["local","api"],default="local")
    test=commands.add_parser("evaluate");test.add_argument("--output",default="reports")
    args=parser.parse_args(argv)
    if args.command=="evaluate":evaluate(args.output);return
    paths=sorted(path for path in args.documents.iterdir() if path.suffix.lower() in {".pdf",".md",".txt"})
    result=SearchIndex(ingest(paths),backend=args.embeddings).answer(args.question,mode=args.mode)
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
