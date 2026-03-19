import io
import zipfile
from typing import List, Tuple

import streamlit as st
from pypdf import PdfReader, PdfWriter


st.set_page_config(
    page_title="PDF Splitter by names.txt",
    page_icon="📄",
    layout="centered"
)


def normalize_filename(name: str) -> str:
    name = (name or "").strip()
    name = name.replace("\\", "/").split("/")[-1]
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name


def parse_names_txt(file_bytes: bytes) -> Tuple[List[Tuple[str, int]], List[str]]:
    """
    Формат names.txt:
    filename.pdf,3
    another_file.pdf,5
    """
    text = file_bytes.decode("utf-8", errors="replace")
    lines = text.splitlines()

    entries: List[Tuple[str, int]] = []
    errors: List[str] = []

    for line_num, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        if not line:
            continue

        parts = [p.strip() for p in line.split(",")]

        if len(parts) != 2:
            errors.append(
                f"Строка {line_num}: неверный формат. Нужно так: filename.pdf,3"
            )
            continue

        filename_part, pages_part = parts

        if not filename_part:
            errors.append(f"Строка {line_num}: пустое имя файла")
            continue

        try:
            pages_count = int(pages_part)
            if pages_count <= 0:
                raise ValueError
        except ValueError:
            errors.append(
                f"Строка {line_num}: количество страниц должно быть целым числом больше 0"
            )
            continue

        entries.append((normalize_filename(filename_part), pages_count))

    return entries, errors


def split_pdf_by_variable_pages(pdf_bytes: bytes, entries: List[Tuple[str, int]]) -> Tuple[bytes, List[str]]:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    total_pages = len(reader.pages)
    expected_pages = sum(page_count for _, page_count in entries)

    logs = [
        f"Всего страниц в PDF: {total_pages}",
        f"Всего файлов в names.txt: {len(entries)}",
        f"Всего страниц по names.txt: {expected_pages}",
    ]

    if total_pages != expected_pages:
        raise ValueError(
            f"Количество страниц не совпадает: в PDF {total_pages}, а по names.txt требуется {expected_pages}."
        )

    current_page = 0
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        for filename, page_count in entries:
            writer = PdfWriter()
            start_page = current_page
            end_page = current_page + page_count

            for page_num in range(start_page, end_page):
                writer.add_page(reader.pages[page_num])

            out_pdf = io.BytesIO()
            writer.write(out_pdf)
            out_pdf.seek(0)

            zipf.writestr(filename, out_pdf.read())

            logs.append(
                f"Создан файл: {filename} | страницы {start_page + 1}-{end_page}"
            )

            current_page = end_page

    zip_buffer.seek(0)
    return zip_buffer.read(), logs


st.title("📄 Разделение PDF по names.txt")
st.write(
    "Загрузи один общий PDF и файл `names.txt`, где для каждого документа указаны имя файла и количество страниц."
)

with st.expander("Как заполнить файл names.txt", expanded=True):
    st.markdown(
        """
### Формат файла

Каждая строка должна быть записана так:

```txt
имя_файла.pdf,количество_страниц
