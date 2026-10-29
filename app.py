from pathlib import Path
import tempfile
import hashlib
import streamlit as st
from policy_search.ingest import ingest
from policy_search.search import SearchIndex

st.set_page_config(page_title="Retail Policy Search",page_icon="📚",layout="wide")
st.title("Retail Policy Search Assistant")
st.caption("Find the policy. Read the evidence. Check the page.")
st.sidebar.header("Document workspace")
uploaded=st.sidebar.file_uploader("Use your PDF, TXT or Markdown files",type=["pdf","txt","md"],accept_multiple_files=True)
backend=st.sidebar.selectbox("Embeddings",["local","api"],help="Local uses hashed lexical vectors. API sends document text and questions to the configured provider.")
mode=st.sidebar.selectbox("Answer mode",["offline","llm"],help="Offline quotes source text. LLM sends retrieved excerpts to the configured provider and requires environment variables.")
st.sidebar.caption("Defaults are offline. Sample policies are fictional and are not policies of Trent or any other retailer.")

@st.cache_resource(show_spinner="Reading documents and building the FAISS index…")
def build_index(files,embedding_backend):
    if not files:return SearchIndex(ingest(sorted(Path("samples/text").glob("*.md"))),embedding_backend)
    with tempfile.TemporaryDirectory() as folder:
        paths=[]
        names=[Path(name).name for name,data in files]
        if len(names)!=len(set(names)):raise ValueError("Please use unique document filenames")
        for name,data in files:
            if len(data)>20*1024*1024:raise ValueError("Maximum file size is 20 MB")
            path=Path(folder)/Path(name).name;path.write_bytes(data);paths.append(path)
        return SearchIndex(ingest(paths),embedding_backend)

try:
    payload=tuple((file.name,file.getvalue()) for file in uploaded) if uploaded else ()
    signature=hashlib.sha256(repr((payload,backend,mode)).encode()).hexdigest()
    if st.session_state.get("corpus_signature")!=signature:
        st.session_state.pop("result",None)
        st.session_state["corpus_signature"]=signature
    index=build_index(payload,backend)
except Exception as error:
    st.error(str(error));st.stop()

sources=sorted(set(chunk.source for chunk in index.chunks))
with st.expander(f"Indexed {len(sources)} documents · {len(index.chunks)} passages"):
    for source in sources:
        pages={chunk.page for chunk in index.chunks if chunk.source==source}
        ocr={chunk.page for chunk in index.chunks if chunk.source==source and chunk.extraction=="ocr"}
        st.write(f"{source} — {len(pages)} pages, {len(ocr)} OCR pages")
left,right=st.columns([3,2])
with left:
    with st.form("question"):
        question=st.text_input("Ask a question",placeholder="How many days do I have to return an item?")
        submitted=st.form_submit_button("Search policies",type="primary")
    if submitted and question.strip():
        try:
            result=index.answer(question,mode=mode)
            st.session_state["result"]=result
        except Exception as error:st.error(str(error))
    if "result" in st.session_state:
        result=st.session_state["result"]
        if result["abstained"]:st.warning(result["answer"])
        else:
            st.subheader("Answer")
            st.write(result["answer"])
            st.caption(" · ".join(result["citations"]))
        for hit in result["evidence"]:
            with st.expander(f"{hit['citation']} · relevance {hit['score']:.2f}"):
                st.write(hit["text"])
                st.caption(f"Extracted with {hit['extraction']}")
with right:
    st.subheader("Source overview")
    selected=st.selectbox("Document",sources)
    st.write(index.summarize(selected))
    st.caption("This is a short extractive overview, not a complete policy summary. Open the source before acting on exceptions.")
