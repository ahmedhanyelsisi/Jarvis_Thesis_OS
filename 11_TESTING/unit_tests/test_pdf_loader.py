import tempfile
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, StreamObject


from knowledge_system.ingestion.pdf_loader import load_pdf


def test_pdf_loader():
    with tempfile.TemporaryDirectory() as temporary_directory:
        pdf_path = Path(temporary_directory) / "research.pdf"
        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        font_reference = writer._add_object(font)
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {NameObject("/F1"): font_reference}
                )
            }
        )
        content_stream = StreamObject()
        content_stream.set_data(
            b"BT /F1 12 Tf 72 720 Td "
            b"(Artificial intelligence supports education assessment.) Tj ET"
        )
        page[NameObject("/Contents")] = writer._add_object(content_stream)
        writer.add_metadata({"/Author": "Jarvis Researcher"})
        with pdf_path.open("wb") as pdf_file:
            writer.write(pdf_file)

        loaded = load_pdf(pdf_path)

    assert loaded["filename"] == "research.pdf"
    assert "education assessment" in loaded["content"]
    assert loaded["metadata"]["document_type"] == "pdf"
    assert loaded["metadata"]["page_count"] == 1
    assert loaded["metadata"]["author"] == "Jarvis Researcher"


if __name__ == "__main__":
    test_pdf_loader()
    print("PDF loader test passed.")
