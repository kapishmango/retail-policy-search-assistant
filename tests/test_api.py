import io
import json
import urllib.error
import numpy as np
import pytest
from policy_search.api import APIClient

def test_embedding_request_and_index_order(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY","test-key-not-real")
    captured=[]
    def fake_open(request,timeout):
        captured.append(json.loads(request.data))
        assert request.full_url=="https://api.openai.com/v1/embeddings"
        return io.BytesIO(json.dumps({"data":[{"index":1,"embedding":[0,1]},{"index":0,"embedding":[1,0]}]}).encode())
    monkeypatch.setattr("urllib.request.urlopen",fake_open)
    np.testing.assert_array_equal(APIClient().embed(["first","second"]),[[1,0],[0,1]])
    assert captured[0]["input"]==["first","second"]

def test_chat_request_round_trip(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY","test-key-not-real");monkeypatch.setenv("LLM_MODEL","test-model")
    def fake_open(request,timeout):
        payload=json.loads(request.data)
        assert payload["model"]=="test-model"
        assert payload["response_format"]=={"type":"json_object"}
        evidence=json.loads(payload["messages"][1]["content"])
        assert evidence["excerpts"][0]["citation"]=="policy.pdf · p. 2"
        answer={"answer":"30 days","citations":["policy.pdf · p. 2"],"abstain":False}
        return io.BytesIO(json.dumps({"choices":[{"message":{"content":json.dumps(answer)}}]}).encode())
    monkeypatch.setattr("urllib.request.urlopen",fake_open)
    result=APIClient().answer("return window?",[{"citation":"policy.pdf · p. 2","text":"Return within 30 days."}])
    assert result["answer"]=="30 days"

def test_service_error_does_not_echo_response_secrets(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY","test-key-not-real")
    def fake_open(request,timeout):
        raise urllib.error.HTTPError(request.full_url,401,"secret server detail",{},None)
    monkeypatch.setattr("urllib.request.urlopen",fake_open)
    with pytest.raises(RuntimeError) as error:APIClient().post("/embeddings",{})
    assert "401" in str(error.value) and "secret" not in str(error.value)
