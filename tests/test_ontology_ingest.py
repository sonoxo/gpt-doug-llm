from pypdf import PdfWriter

from ontology.ingest import DocumentIngestor
from ontology.store import OntologyStore


def test_pdf_ingestion_is_idempotent(tmp_path):
    pdf = tmp_path / "sample.pdf"

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_blank_page(width=200, height=200)

    with pdf.open("wb") as fh:
        writer.write(fh)

    ontology_root = tmp_path / "ontology"
    ingestor = DocumentIngestor(ontology_root)

    first = ingestor.ingest_pdf(pdf)
    second = ingestor.ingest_pdf(pdf)

    assert first["page_count"] == 2
    assert first["already_ingested"] is False

    assert second["document_id"] == first["document_id"]
    assert second["already_ingested"] is True

    store = OntologyStore(ontology_root)
    status = store.status()

    assert status["documents"] == 1
    assert status["pages"] == 2
