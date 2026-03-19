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


# =========================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================

def normalize_filename(name: str) -> str:
    name = (name or "").strip()
    name = name.replace("\\", "/").split("/")[-1]
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name


def parse_names_txt(file_bytes: bytes) -> Tuple[List[Tuple[str, int]], List[str]]:
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
            errors.append(f"Строка {line_num}: формат должен быть filename.pdf,3")
            continue

        filename_part, pages_part = parts

        if not filename_part:
            errors.append(f"Строка {line_num}: пустое имя файла")
            continue

        try:
            pages_count = int(pages_part)
            if pages_count <= 0:
                raise ValueError
        except:
            errors.append(f"Строка {line_num}: неверное количество страниц")
            continue

        entries.append((normalize_filename(filename_part), pages_count))

    return entries, errors


def split_pdf(pdf_bytes: bytes, entries: List[Tuple[str, int]]):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    total_pages = len(reader.pages)
    expected_pages = sum(p for _, p in entries)

    if total_pages != expected_pages:
        raise ValueError(
            f"Ошибка: в PDF {total_pages} страниц, а по names.txt нужно {expected_pages}"
        )

    current_page = 0
    zip_buffer = io.BytesIO()

    logs = []

    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        for filename, page_count in entries:
            writer = PdfWriter()

            start = current_page
            end = current_page + page_count

            for p in range(start, end):
                writer.add_page(reader.pages[p])

            pdf_bytes_out = io.BytesIO()
            writer.write(pdf_bytes_out)
            pdf_bytes_out.seek(0)

            zipf.writestr(filename, pdf_bytes_out.read())

            logs.append(f"{filename} → страницы {start+1}-{end}")

            current_page = end

    zip_buffer.seek(0)
    return zip_buffer.read(), logs


# =========================
# ИНТЕРФЕЙС
# =========================

st.title("📄 Разделение PDF по names.txt")

st.write("Загрузи PDF и файл names.txt (имя файла + количество страниц).")

with st.expander("📘 Как заполнить names.txt", expanded=True):
    st.code(
"""686-Matgramotnost1.pdf,3
687-Matgramotnost2.pdf,3
688-Matgramotnost3.pdf,2
689-Matgramotnost4.pdf,5"""
    )

    st.write("Правила:")
    st.write("- одна строка = один PDF")
    st.write("- формат: имя,количество_страниц")
    st.write("- можно без .pdf")
    st.write("- страницы идут подряд")

# шаблон
template = """686-Matgramotnost1.pdf,3
687-Matgramotnost2.pdf,3
688-Matgramotnost3.pdf,3
689-Matgramotnost4.pdf,3
"""

st.download_button(
    "⬇️ Скачать шаблон names.txt",
    data=template.encode("utf-8"),
    file_name="names_template.txt"
)

pdf_file = st.file_uploader("📄 Загрузи PDF", type=["pdf"])
names_file = st.file_uploader("📄 Загрузи names.txt", type=["txt"])

if st.button("🚀 Обработать", disabled=not (pdf_file and names_file)):
    try:
        pdf_bytes = pdf_file.read()
        names_bytes = names_file.read()

        entries, errors = parse_names_txt(names_bytes)

        if errors:
            st.error("Ошибки в names.txt:")
            for e in errors:
                st.write("-", e)
            st.stop()

        zip_bytes, logs = split_pdf(pdf_bytes, entries)

        st.success("Готово!")

        st.download_button(
            "⬇️ Скачать ZIP",
            data=zip_bytes,
            file_name="result.zip",
            mime="application/zip"
        )

        st.code("\n".join(logs))

    except Exception as e:
        st.error(str(e))
