import uuid
import pytest
from app.database.connection import DatabaseClient
from app.reports.builder import generate_report, load_report


def persisted(tmp_path, dataset):
    db=DatabaseClient('sqlite',str(tmp_path/'db.sqlite'))
    run_id=str(uuid.uuid4()); db.create_run(run_id,'website','https://northloom.example/')
    db.save_dataset(run_id,dataset)
    return db,run_id


def test_immutable_database_roundtrip(tmp_path,dataset):
    db,run_id=persisted(tmp_path,dataset)
    assert db.get_dataset(run_id)==dataset
    assert load_report(db,run_id)['company']['industry']=='Fashion & Apparel'
    with pytest.raises(Exception): db.save_dataset(run_id,dataset)


def test_invalid_report_blocked(tmp_path,dataset):
    dataset['validation']['passed']=False
    db,run_id=persisted(tmp_path,dataset)
    with pytest.raises(ValueError): load_report(db,run_id)


def test_pdf_generation(tmp_path,dataset):
    from pypdf import PdfReader
    db,run_id=persisted(tmp_path,dataset)
    path=generate_report(db,run_id,tmp_path/'report.pdf')
    reader=PdfReader(path)
    text=' '.join(p.extract_text() for p in reader.pages)
    assert 'North Loom' in text and '42.50' in text
    assert all(len(p.extract_text().strip())>30 for p in reader.pages)
    assert len(reader.pages)>=2


def test_worker_claim_is_single_use(tmp_path):
    db=DatabaseClient('sqlite',str(tmp_path/'jobs.db'))
    run_id=str(uuid.uuid4()); db.create_run(run_id,'website','https://example.com/')
    assert db.claim_next_run()==run_id
    assert db.claim_next_run() is None


def test_supabase_failure_does_not_fall_back_to_sqlite(tmp_path,monkeypatch):
    db=DatabaseClient('supabase',str(tmp_path/'must-not-exist.sqlite'))
    def unavailable(): raise RuntimeError('Supabase unavailable')
    monkeypatch.setattr(db,'remote',unavailable)
    with pytest.raises(RuntimeError): db.create_run(str(uuid.uuid4()),'website','https://example.com/')
    assert not (tmp_path/'must-not-exist.sqlite').exists()
