import tempfile
from pathlib import Path

from docx import Document


from knowledge_system.ingestion.docx_loader import load_docx


def test_docx_loader():
    with tempfile.TemporaryDirectory() as temporary_directory:
        docx_path = Path(temporary_directory) / "notes.docx"
        document = Document()
        document.add_paragraph("A persistent research knowledge system.")
        document.core_properties.author = "Jarvis Researcher"
        document.save(docx_path)

        loaded = load_docx(docx_path)

    assert loaded["filename"] == "notes.docx"
    assert "persistent research knowledge" in loaded["content"]
    assert loaded["metadata"]["document_type"] == "docx"
    assert loaded["metadata"]["author"] == "Jarvis Researcher"


if __name__ == "__main__":
    test_docx_loader()
    print("DOCX loader test passed.")
