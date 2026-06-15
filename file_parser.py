import io
import re
from collections import Counter


def extract_text(file_storage) -> str:
    filename = (file_storage.filename or "").lower()
    data = file_storage.read()

    if filename.endswith(".pdf"):
        raw = _parse_pdf(data)
    elif filename.endswith(".docx"):
        raw = _parse_docx(data)
    else:
        try:
            raw = data.decode("utf-8")
        except UnicodeDecodeError:
            raw = data.decode("latin-1", errors="replace")

    return clean_text(raw)


def _parse_pdf(data: bytes) -> str:
    """Rút text PDF. Ưu tiên pdfplumber (trung thực hơn, ít rớt ký tự như '03'->'0'),
    fallback pypdf nếu pdfplumber lỗi/không có."""
    # 1) pdfplumber (pdfminer) — bám layout, giữ đúng số/khoảng trắng
    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                t = page.extract_text(x_tolerance=1.5, y_tolerance=3) or ""
                if t.strip():
                    pages.append(t)
        text = "\n".join(pages)
        if text.strip():
            return text
    except Exception as e:
        print(f"[_parse_pdf] pdfplumber lỗi, fallback pypdf: {e}")

    # 2) Fallback pypdf
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() for page in reader.pages]
    text = "\n".join(p for p in pages if p)

    # Cảnh báo PDF scan/ảnh (không có lớp text) -> rút ra rỗng
    if not text.strip():
        print("[_parse_pdf] CẢNH BÁO: PDF không có lớp text (có thể là bản scan/ảnh).")
    return text


def _parse_docx(data: bytes) -> str:
    """Rút text DOCX ĐẦY ĐỦ: gồm cả phần chèn theo-dõi-thay-đổi (w:ins), hyperlink,
    smartTag và bảng — bỏ phần đã xóa (w:delText).

    python-docx `paragraph.text` chỉ đọc run con trực tiếp nên BỎ SÓT text trong
    w:ins/hyperlink/field -> gây rớt ký tự (vd '03 (ba)' bị track-changes -> '0 (b)').
    Ở đây duyệt toàn bộ <w:t> nên lấy đúng nội dung sau khi chấp nhận thay đổi.
    """
    from docx import Document
    from docx.oxml.ns import qn

    doc = Document(io.BytesIO(data))
    T, TAB, BR, P = qn("w:t"), qn("w:tab"), qn("w:br"), qn("w:p")

    lines = []
    for p in doc.element.body.iter(P):
        buf = []
        for node in p.iter():
            if node.tag == T:
                buf.append(node.text or "")      # gồm cả w:ins; KHÔNG gồm w:delText
            elif node.tag == TAB:
                buf.append("\t")
            elif node.tag == BR:
                buf.append("\n")
        line = "".join(buf)
        if line.strip():
            lines.append(line)

    text = "\n".join(lines)
    if text.strip():
        return text

    # Fallback: cách cũ nếu duyệt XML không ra gì
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


# Dòng số trang: CHỈ xóa khi có tiền tố chữ ("Trang 3", "Page 3/20") hoặc bị bao
# bởi gạch ngang ("- 3 -"). TUYỆT ĐỐI KHÔNG xóa dòng chỉ chứa số trần ("5000",
# "85", "5001") — đó thường là số liệu/giá trị hợp đồng (mất sẽ gây miss context).
_PAGE_NUM_RE = re.compile(
    r"^\s*(?:"
    r"[-–—]\s*\d+\s*[-–—]"                       # - 3 -
    r"|(?:trang|page|tr\.)\s*\d+(?:\s*/\s*\d+)?"  # Trang 3 / Page 3/20
    r")\s*$",
    re.IGNORECASE,
)

# Mốc neo điều khoản — KHÔNG bao giờ bị loại dù lặp lại nhiều lần (giữ vị trí điều).
# Gồm cả biến thể không dấu vì trích xuất PDF đôi khi rớt dấu (Điều -> Dieu).
_CLAUSE_ANCHOR_RE = re.compile(
    r"^\s*(?:điều|dieu|khoản|khoan|mục|muc|chương|chuong|phần|phan"
    r"|article|clause|section)\b",
    re.IGNORECASE,
)


def clean_text(raw: str) -> str:
    """Giảm nhiễu/token: bỏ số trang, header/footer lặp, chuẩn hóa khoảng trắng.

    Nguyên tắc: thà giữ thừa còn hơn xóa nhầm số liệu/điều khoản (chống miss context).
    """
    if not raw:
        return ""

    lines = [ln.strip() for ln in raw.splitlines()]

    # Đếm tần suất các dòng ngắn để phát hiện header/footer lặp.
    # Loại trừ mốc neo điều khoản: "Điều 1"... có thể lặp nhưng không được xóa.
    short_line_freq = Counter(
        ln for ln in lines if ln and len(ln) < 80
    )
    repeated = {
        ln for ln, n in short_line_freq.items()
        if n > 3 and not _CLAUSE_ANCHOR_RE.match(ln)
    }

    removed_pagenum = 0
    removed_repeated = 0
    cleaned = []
    for ln in lines:
        if not ln:
            cleaned.append("")
            continue
        if _PAGE_NUM_RE.match(ln):
            removed_pagenum += 1
            continue
        if ln in repeated:
            removed_repeated += 1
            continue
        cleaned.append(ln)

    # Gộp nhiều dòng trống liên tiếp -> tối đa 1 dòng trống
    result = []
    blank = False
    for ln in cleaned:
        if ln == "":
            if not blank:
                result.append("")
            blank = True
        else:
            result.append(ln)
            blank = False

    # P3: log số dòng đã loại để phát hiện khi cắt nhầm quá tay
    if removed_pagenum or removed_repeated:
        print(f"[clean_text] đã loại {removed_pagenum} dòng số trang, "
              f"{removed_repeated} dòng header/footer lặp")

    return "\n".join(result).strip()


def _sentence_cut(s: str, limit: int) -> int:
    """Tìm điểm cắt <= limit tại ranh giới câu gần nhất (. ! ? ; xuống dòng).

    Tránh cắt giữa câu/giữa số (vd '03 (ba)') khi buộc phải chia đoạn dài.
    Không có ranh giới hợp lý -> cắt cứng tại limit.
    """
    window = s[:limit]
    best = max(
        window.rfind(". "), window.rfind("! "), window.rfind("? "),
        window.rfind("; "), window.rfind("\n"),
    )
    # Chỉ nhận nếu điểm cắt không quá sớm (giữ >=60% chunk), tránh chunk quá ngắn
    if best >= int(limit * 0.6):
        return best + 1
    return limit


def split_into_chunks(text: str, chunk_size: int, overlap: int) -> list:
    """Chia text theo ranh giới đoạn văn, mỗi chunk ~chunk_size ký tự, có overlap."""
    if len(text) <= chunk_size:
        return [text]

    paragraphs = text.split("\n")
    chunks = []
    current = ""

    for para in paragraphs:
        # Nếu thêm đoạn này vẫn trong giới hạn -> nối tiếp
        if len(current) + len(para) + 1 <= chunk_size:
            current = current + "\n" + para if current else para
        else:
            if current:
                chunks.append(current)
            # Bắt đầu chunk mới với phần overlap từ cuối chunk trước
            if overlap > 0 and chunks:
                tail = chunks[-1][-overlap:]
                current = tail + "\n" + para
            else:
                current = para
            # Đoạn đơn lẻ dài hơn chunk_size -> cắt, ưu tiên ranh giới câu
            while len(current) > chunk_size:
                cut = _sentence_cut(current, chunk_size)
                chunks.append(current[:cut])
                current = current[cut - overlap:] if overlap > 0 else current[cut:]

    if current.strip():
        chunks.append(current)

    return chunks
