from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "mini-corpus"


def client_for(tmp_path: Path, corpus: Path | None = None) -> TestClient:
    corpus_dir = corpus or (tmp_path / "empty-corpus")
    corpus_dir.mkdir(exist_ok=True)
    return TestClient(create_app(data_dir=tmp_path / "data", corpus_dir=corpus_dir, fixture_dir=FIXTURES))


def scan(client: TestClient):
    response = client.post("/api/documents/scan")
    assert response.status_code == 202
    documents = client.get("/api/documents").json()
    assert len(documents) == 2
    return documents


def test_scan_is_idempotent_and_extracts_page_text(tmp_path):
    client = client_for(tmp_path)
    first = scan(client)
    second = scan(client)
    assert [item["id"] for item in first] == [item["id"] for item in second]
    response = client.get(f"/api/documents/{first[0]['id']}/pages/1")
    assert response.status_code == 200
    assert "programma" in response.json()["text"]
    assert client.get(f"/api/documents/{first[0]['id']}/pages/0").status_code == 422


def test_review_requires_confirmed_page_evidence(tmp_path):
    client = client_for(tmp_path)
    documents = scan(client)
    setup = {
        "description": "A funded implementation programme with verified evidence.",
        "schema": {"type": "object", "properties": {"objective": {"type": "string"}}},
    }
    assert client.put("/api/program-setup", json=setup).status_code == 200
    created = client.post("/api/programs", json={"name_en": "Clean Air Programme", "classification": "environment", "field_values": {"objective": "Reduce emissions"}, "status": "draft", "confidence": "high"})
    assert created.status_code == 201
    program = created.json()
    assert client.patch(f"/api/programs/{program['id']}", json={"status": "reviewed"}).status_code == 422
    clean_air = next(item for item in documents if "schone-lucht" in item["filename"])
    evidence = {"document_id": clean_air["id"], "page_number": 1, "quote_nl": "De gemeente start het programma Schone Lucht.", "reviewer_confirmed": True}
    assert client.post(f"/api/programs/{program['id']}/evidence", json=evidence).status_code == 200
    reviewed = client.patch(f"/api/programs/{program['id']}", json={"status": "reviewed"})
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "reviewed"


def test_malformed_pdf_is_recorded_without_crashing_scan(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "broken.pdf").write_bytes(b"not a PDF")
    client = client_for(tmp_path, corpus)
    response = client.post("/api/documents/scan")
    assert response.status_code == 202
    documents = client.get("/api/documents").json()
    assert len(documents) == 1
    assert documents[0]["extraction_status"] == "failed"
