from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
import requests
import json
import os

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path)

print(f"[DEBUG] Loading .env from: {env_path}")
print(f"[DEBUG] API_URL = {os.getenv('API_URL')}")
print(f"[DEBUG] API_KEY loaded = {'Yes' if os.getenv('API_KEY') else 'No'}")
print(f"[DEBUG] MODEL = {os.getenv('MODEL')}")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25MB tối đa cho upload


@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File quá lớn (tối đa 25MB). Vui lòng dùng file nhỏ hơn."}), 413


API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")
MODEL   = os.getenv("MODEL")

CRITERIA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "criteria_store.json")

# ── Tuning constants (xử lý file dài) ─────────────────────────────────────────
SINGLE_CALL_MAX_CHARS = 28000    # <= ngưỡng này: 1 call full-text (Light)
CHUNK_SIZE_CHARS      = 14000    # kích thước mỗi chunk khi map-reduce
CHUNK_OVERLAP_CHARS   = 800      # overlap giữa các chunk
HARD_CAP_CHARS        = 200000   # cap cứng, vượt sẽ cắt + cảnh báo
MAX_WORKERS           = 4        # số chunk gọi LLM song song


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_criteria_store() -> dict:
    with open(CRITERIA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_criteria_store(store: dict):
    with open(CRITERIA_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def call_llm(messages: list, max_tokens: int = 8000, temperature: float = 0.1) -> str:
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 0.95,
        "presence_penalty": 0,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    resp = requests.post(API_URL, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return content or ""


def build_prompt(criteria: str, contract: str) -> str:
    return f"""Bạn là chuyên gia pháp lý. Hãy đọc kỹ TỪNG tiêu chí bên dưới, sau đó tìm trong hợp đồng xem điều khoản đó có tồn tại không và nội dung có khớp không.

===TIÊU CHÍ XÉT DUYỆT===
{criteria}

===NỘI DUNG HỢP ĐỒNG===
{contract}

===HƯỚNG DẪN ĐÁNH GIÁ===
Với TỪNG tiêu chí, hãy:
1. Tìm điều khoản tương ứng trong hợp đồng
2. So sánh chi tiết (số liệu, tỷ lệ %, số ngày, điều kiện...)
3. Đánh giá theo đúng quy tắc sau:
   - "DAT"   : hợp đồng CÓ điều khoản này VÀ nội dung/số liệu KHỚP ĐÚNG với tiêu chí
   - "SAI"   : hợp đồng CÓ điều khoản này NHƯNG số liệu/giá trị/nội dung KHÁC với tiêu chí
   - "THIEU" : hợp đồng KHÔNG CÓ điều khoản này hoặc không đề cập đến

===NGUYÊN TẮC CỐT LÕI: KHÔNG SUY ĐOÁN===
- Chỉ kết luận dựa trên nội dung CÓ THẬT trong hợp đồng. KHÔNG suy luận, KHÔNG phỏng đoán, KHÔNG tự điền thông tin không có.
- Khi KHÔNG chắc chắn về bất kỳ điểm nào (điều khoản, vị trí, con số) -> để TRỐNG ("") hoặc kết luận "THIEU", TUYỆT ĐỐI KHÔNG đoán bừa.
- Thà bỏ trống còn hơn điền sai.

===QUY TẮC ĐỌC SỐ (RẤT QUAN TRỌNG)===
- Đọc số ĐÚNG NGUYÊN VĂN như viết trong hợp đồng. Số 0 đứng đầu KHÔNG bị bỏ: "03 ngày" = 3 (ba) ngày, "05" = 5, KHÔNG được hiểu thành 0.
- KHÔNG làm tròn, KHÔNG đổi đơn vị, KHÔNG diễn giải lại con số.
- So sánh số với tiêu chí theo GIÁ TRỊ thực: "03 ngày" và "3 ngày" và "ba ngày" là BẰNG NHAU -> nếu tiêu chí yêu cầu 3 ngày thì đây là DAT.
- Chỉ kết luận SAI khi giá trị thực sự khác (vd tiêu chí 3 ngày nhưng hợp đồng ghi 5 ngày).
- Trong ket_qua_thuc_te, ghi lại con số y như trong hợp đồng (giữ nguyên "03 ngày" nếu hợp đồng viết vậy).

===QUY TẮC TRÍCH DẪN & VỊ TRÍ (chống dẫn sai điều)===
- trich_dan PHẢI là câu/đoạn TRÍCH NGUYÊN VĂN copy y hệt từ hợp đồng (để người dùng dò lại được). TUYỆT ĐỐI KHÔNG diễn giải lại, KHÔNG tự bịa nội dung không có trong hợp đồng.
- vi_tri (vd "Điều 5.2", "Khoản 3", "Mục II") CHỈ được ghi khi nhãn điều/khoản đó XUẤT HIỆN NGAY TẠI hoặc NGAY TRƯỚC đoạn bạn trích dẫn trong hợp đồng. Phải là số điều/khoản có thật, đọc trực tiếp từ văn bản.
- TUYỆT ĐỐI KHÔNG suy đoán số điều khoản. Nếu đoạn trích không kèm nhãn điều/khoản rõ ràng, hoặc bạn không chắc chắn 100% đoạn trích thuộc điều nào -> để vi_tri = "" (rỗng). Dẫn sai điều còn tệ hơn không dẫn.

===QUY TẮC BẮT BUỘC===
- Nếu không tìm thấy điều khoản trong hợp đồng -> ket_qua = "THIEU", ket_qua_thuc_te = "Không có trong hợp đồng", trich_dan = "", vi_tri = ""
- Nếu số liệu/tỷ lệ/số ngày thực sự khác nhau về giá trị -> ket_qua = "SAI"
- Chỉ dùng "DAT" khi nội dung khớp hoàn toàn
- ket_qua chỉ được là một trong ba giá trị: DAT, SAI, THIEU

===OUTPUT===
Chỉ trả về JSON hợp lệ, không có text thừa, không có markdown:
{{"items":[{{"stt":1,"tieu_chi":"nội dung tiêu chí","ket_qua_mong_doi":"giá trị yêu cầu theo tiêu chí","ket_qua_thuc_te":"nội dung thực tế trong hợp đồng hoặc Không có trong hợp đồng","trich_dan":"câu trích NGUYÊN VĂN từ hợp đồng hoặc rỗng","vi_tri":"vị trí điều khoản vd Điều 5 hoặc rỗng","ket_qua":"DAT hoặc SAI hoặc THIEU","ghi_chu":"lý do ngắn nếu SAI hoặc THIEU"}}],"tong_ket":{{"dat":0,"thieu":0,"sai":0,"tong":0,"ket_luan":"DAT hoặc KHONG_DAT","tom_tat":"tóm tắt ngắn các vấn đề"}}}}"""


import re as _re


def _norm_for_match(s: str) -> str:
    """Chuẩn hóa để so khớp chuỗi con: gộp khoảng trắng, bỏ phân biệt hoa/thường."""
    return _re.sub(r"\s+", " ", str(s or "")).strip().lower()


def _flexible_span(haystack: str, needle: str):
    """Tìm (start, end) của needle trong haystack, bỏ qua khác biệt khoảng trắng &
    hoa/thường. Trả None nếu không thấy. Offset tính theo haystack gốc."""
    needle = (needle or "").strip()
    if not needle or not haystack:
        return None
    parts = [p for p in _re.split(r"\s+", needle) if p]
    pattern = r"\s+".join(_re.escape(p) for p in parts)
    if not pattern:
        return None
    m = _re.search(pattern, haystack, _re.IGNORECASE)
    return (m.start(), m.end()) if m else None


def _flexible_find(haystack: str, needle: str) -> int:
    """Vị trí bắt đầu của needle trong haystack (linh hoạt), -1 nếu không thấy."""
    span = _flexible_span(haystack, needle)
    return span[0] if span else -1


# Nhãn điều/khoản — CHỈ nhận khi nằm ĐẦU DÒNG (tiêu đề thật), để không vớ nhầm
# tham chiếu chéo giữa câu ("...theo quy định tại Điều 12..."). Gồm biến thể không dấu.
_VITRI_HEADING_RE = _re.compile(
    r"^[ \t]*((?:điều|dieu|chương|chuong|phần|phan|article|section"
    r"|khoản|khoan|mục|muc|clause)\s*\d+(?:[.\d]*\d)?)",
    _re.IGNORECASE | _re.MULTILINE,
)

# Nhãn cấp "điều" (cha) vs cấp "khoản/mục" (con) để ghép vị trí phân cấp.
_MAJOR_KW = ("điều", "dieu", "chương", "chuong", "phần", "phan", "article", "section")


def _is_major(label: str) -> bool:
    low = label.lower()
    return any(low.startswith(k) for k in _MAJOR_KW)


def _derive_vi_tri(contract: str, trich_dan: str, max_back: int = 15000) -> str:
    """Suy vị trí điều khoản TỪ VĂN BẢN GỐC, không tin model đoán.

    Tìm vị trí đoạn trích, dò ngược lên TIÊU ĐỀ điều khoản gần nhất nằm ĐẦU DÒNG
    (bỏ qua tham chiếu chéo giữa câu). Ghép 'Điều cha + Khoản con' nếu có.
    Không có tiêu đề trong phạm vi -> trả "" (không bịa vị trí).
    """
    pos = _flexible_find(contract, trich_dan)
    if pos < 0:
        return ""
    window_start = max(0, pos - max_back)
    before = contract[window_start:pos]

    headings = [(m.start(), _re.sub(r"\s+", " ", m.group(1)).strip())
                for m in _VITRI_HEADING_RE.finditer(before)]
    if not headings:
        # Tiêu đề có thể nằm ngay đầu đoạn trích (vd dòng "Điều 5. ...")
        m = _VITRI_HEADING_RE.match("\n" + contract[pos:pos + 80])
        return _re.sub(r"\s+", " ", m.group(1)).strip() if m else ""

    # Tiêu đề cấp "điều" gần nhất = điều khoản chứa đoạn trích
    major = None
    for start, label in headings:
        if _is_major(label):
            major = (start, label)
    if major is None:
        return headings[-1][1]  # chỉ có nhãn con -> trả nhãn con gần nhất

    # Nhãn con gần đoạn trích nhất, nằm SAU tiêu đề điều cha
    minor = None
    for start, label in headings:
        if start > major[0] and not _is_major(label):
            minor = label
    return f"{major[1]}, {minor}" if minor else major[1]


# ── Đối chiếu SỐ xác định (deterministic) — chống typo "0" vs "03", model chấm nhầm ──
# Toàn bộ so khớp BỎ DẤU (diacritic-insensitive) để chịu được "ngay"/"ngày",
# "thang"/"tháng"... cả khi hợp đồng/đề xuất viết không dấu.

import unicodedata as _ud


def _strip_diacritics(s: str) -> str:
    s = _ud.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if _ud.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D").lower()


# Số tiếng Việt 0-99 (dạng KHÔNG DẤU)
_VN_ONES = {"khong": 0, "mot": 1, "hai": 2, "ba": 3, "bon": 4, "tu": 4,
            "nam": 5, "lam": 5, "sau": 6, "bay": 7, "tam": 8, "chin": 9}

# Đơn vị quan tâm (key hiển thị có dấu) -> regex KHÔNG DẤU nhận diện
_UNIT_RE = {
    "ngày": r"ngay", "tháng": r"thang", "năm": r"nam", "tuần": r"tuan",
    "giờ": r"gio", "%": r"%|phan\s*tram", "tin": r"tin", "đồng": r"dong|vnd",
}

# Cụm số bằng chữ KHÔNG DẤU (vd "ba", "muoi lam", "hai muoi mot")
_WORDNUM = (r"(?:khong|mot|hai|ba|bon|tu|nam|lam|sau|bay|tam|chin|muoi)"
            r"(?:\s+(?:muoi|mot|hai|ba|bon|tu|nam|lam|sau|bay|tam|chin))*")


def _vn_words_to_int(s: str):
    toks = [t for t in _re.split(r"\s+", (s or "").strip()) if t]  # s đã bỏ dấu
    if not toks:
        return None
    if toks[0] == "muoi":                       # mười = 10[+ones]
        return 10 + (_VN_ONES.get(toks[1], 0) if len(toks) > 1 else 0)
    if len(toks) >= 2 and toks[1] == "muoi":    # X mươi [Y]
        v = _VN_ONES.get(toks[0], 0) * 10
        return v + (_VN_ONES.get(toks[2], 0) if len(toks) >= 3 else 0)
    if len(toks) == 1:
        return _VN_ONES.get(toks[0])
    return None


def _num_token_to_int(tok: str):
    tok = (tok or "").strip()
    if _re.match(r"\d", tok):
        tok = _re.sub(r"[.,](?=\d{3}\b)", "", tok)   # bỏ dấu phân cách nghìn 5.000 -> 5000
        digits = _re.sub(r"[^\d]", "", tok)
        return int(digits) if digits else None
    return _vn_words_to_int(tok)


def _extract_unit_values(text: str) -> dict:
    """Trả {đơn vị: set(số)} cho số ĐỨNG NGAY TRƯỚC đơn vị (cho phép '(ba)' xen giữa).

    Bỏ dấu trước khi khớp. Bám đơn vị để không so nhầm số điều khoản/ngày tháng lạc.
    """
    text = _strip_diacritics(text)
    out = {}
    # CHỈ bắt số dạng chữ số (digit) để tránh nhập nhằng từ-số sau khi bỏ dấu
    # (vd "từ"->"tu" trùng "tư"=4). Phần "(ba)" trong "03 (ba)" được bỏ qua.
    numpat = r"(\d[\d.,]*)"
    for unit, ure in _UNIT_RE.items():
        pat = numpat + r"\s*(?:\([^)]*\))?\s*(?:" + ure + r")"
        for m in _re.finditer(pat, text):
            v = _num_token_to_int(m.group(1))
            if v is not None:
                out.setdefault(unit, set()).add(v)
    return out


def _number_mismatch(crit_text: str, cite_text: str):
    """So số theo đơn vị giữa tiêu chí và trích dẫn. Trả (đơn vị, set tiêu chí, set
    hợp đồng) nếu CÙNG đơn vị nhưng KHÔNG có giá trị chung; None nếu khớp/không so được."""
    crit_u = _extract_unit_values(crit_text)
    cite_u = _extract_unit_values(cite_text)
    for unit, cvals in crit_u.items():
        avals = cite_u.get(unit)
        if avals and cvals and not (cvals & avals):
            return unit, cvals, avals
    return None


def validate_and_fix(result: dict, contract: str = "", criteria_map: dict = None) -> dict:
    VALID_STATUS = {"DAT", "SAI", "THIEU"}
    criteria_map = criteria_map or {}
    dat = thieu = sai = 0

    for item in result.get("items", []):
        status = str(item.get("ket_qua", "")).strip().upper()
        if status not in VALID_STATUS:
            status = "THIEU"

        thuc_te = str(item.get("ket_qua_thuc_te", "")).strip()
        thuc_te_low = thuc_te.lower()
        # Rỗng / placeholder (so khớp CHÍNH XÁC, tránh "" hay "-" lọt vào mọi chuỗi)
        is_empty = thuc_te_low in ("", "-", "—", "n/a", "na")
        # Cụm từ báo không tìm thấy (so khớp chứa)
        not_found_phrases = ["không có", "không đề cập", "không tìm thấy", "chưa đề cập", "không quy định"]
        is_not_found = any(kw in thuc_te_low for kw in not_found_phrases)
        if (is_empty or is_not_found) and status == "DAT":
            status = "THIEU"
            item["ket_qua_thuc_te"] = "Không có trong hợp đồng"
            item["ghi_chu"] = (item.get("ghi_chu") or "") + " [Auto-fix: không tìm thấy điều khoản]"

        # Đảm bảo luôn có field trích dẫn; THIEU thì xóa trích dẫn (không có để dẫn)
        item.setdefault("trich_dan", "")
        item.setdefault("vi_tri", "")
        if status == "THIEU":
            item["trich_dan"] = ""
            item["vi_tri"] = ""

        # ── Verify trích dẫn & SUY vị trí TỪ VĂN BẢN GỐC (không tin model đoán) ──
        item.pop("trich_start", None)
        item.pop("trich_end", None)
        if contract:
            trich = (item.get("trich_dan") or "").strip()
            span = _flexible_span(contract, trich) if trich else None
            if trich and span is None:
                # Không phải trích nguyên văn -> ẩn trích dẫn (chống bịa)
                item["trich_dan"] = ""
                item["vi_tri"] = ""
            elif span:
                # Trích dẫn hợp lệ -> suy vị trí + lưu offset để tô bên cột trái.
                item["vi_tri"] = _derive_vi_tri(contract, item.get("trich_dan") or "")
                item["trich_start"], item["trich_end"] = span

        # tieu_chi hiển thị lấy từ tiêu chí GỐC (không tin model echo, tránh "0 (b)")
        crit_text = criteria_map.get(item.get("stt"))
        if crit_text:
            item["tieu_chi"] = crit_text

        # ── Đối chiếu SỐ xác định: tiêu chí vs trích dẫn nguyên văn ──
        # Chỉ ép DAT->SAI khi số khác nhau (vd typo "0 ngày" vs yêu cầu "03 ngày");
        # KHÔNG tự ý SAI->DAT (khác biệt có thể do điều kiện/câu chữ ngoài con số).
        if status == "DAT":
            mm = _number_mismatch(crit_text or item.get("tieu_chi") or "",
                                  (item.get("trich_dan") or "").strip())
            if mm:
                unit, cvals, avals = mm
                a = "/".join(str(x) for x in sorted(avals))
                c = "/".join(str(x) for x in sorted(cvals))
                status = "SAI"
                item["ket_qua_thuc_te"] = f"Hợp đồng ghi {a} {unit} (tiêu chí yêu cầu {c} {unit})"
                item["ghi_chu"] = (item.get("ghi_chu") or "") + \
                    f" [Đối chiếu số: hợp đồng {a} {unit} ≠ tiêu chí {c} {unit}]"

        item["ket_qua"] = status
        if status == "DAT":   dat += 1
        elif status == "THIEU": thieu += 1
        else: sai += 1

    total = dat + thieu + sai
    tong_ket = result.get("tong_ket", {})
    tong_ket["dat"]      = dat
    tong_ket["thieu"]    = thieu
    tong_ket["sai"]      = sai
    tong_ket["tong"]     = total
    tong_ket["ket_luan"] = "DAT" if (thieu + sai == 0) else "KHONG_DAT"
    result["tong_ket"]   = tong_ket
    return result


def parse_llm_json(raw: str) -> dict:
    """Làm sạch markdown fence + text thừa rồi parse JSON từ output model.

    Model hay tạo JSON lỗi (nháy kép chưa escape trong giá trị, dấu phẩy thừa,
    output bị cắt...). Thử parse chuẩn trước; lỗi thì dùng json_repair để vá.
    """
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    start = raw.find("{")
    if start >= 0:
        raw = raw[start:]
    # Cắt phần thừa sau dấu } cuối cùng (nếu có)
    end = raw.rfind("}")
    if end >= 0:
        raw = raw[:end + 1]

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: vá JSON lỗi (nháy kép chưa escape, dấu phẩy thừa, thiếu ngoặc...)
        from json_repair import repair_json
        obj = repair_json(raw, return_objects=True)
        if not isinstance(obj, dict):
            raise
        return obj


def analyze_text(criteria: str, contract: str) -> dict:
    """1 LLM call full-text cho 1 đoạn hợp đồng (hoặc 1 chunk)."""
    messages = [
        {
            "role": "user",
            "content": "You are a strict legal contract reviewer. Respond with valid JSON only. Never include markdown or extra text.\n\n"
                       + build_prompt(criteria, contract)
        }
    ]
    raw = call_llm(messages)
    return parse_llm_json(raw)


def _evidence_score(item: dict, contract: str = "") -> tuple:
    """Điểm độ tin cậy của 1 item từ 1 chunk, để gộp map-reduce.

    Ưu tiên: (1) chunk THỰC SỰ tìm thấy điều khoản (DAT/SAI) hơn chunk báo THIEU;
    (2) trích dẫn XÁC MINH ĐƯỢC với hợp đồng (chuỗi con thật) hơn trích dẫn không
    kiểm chứng — loại bản model đọc sai/bịa; (3) trích dẫn dài/đầy đủ hơn.
    """
    status = str(item.get("ket_qua", "")).strip().upper()
    found = 1 if status in ("DAT", "SAI") else 0
    trich = str(item.get("trich_dan") or "")
    verified = 1 if (contract and trich and _flexible_find(contract, trich) >= 0) else 0
    quote_len = len(trich)
    actual_len = len(str(item.get("ket_qua_thuc_te") or ""))
    return (found, verified, quote_len, actual_len)


def merge_chunk_results(chunk_results: list, contract: str = "") -> dict:
    """Gộp kết quả từ nhiều chunk theo stt, chọn chunk có bằng chứng đáng tin nhất."""
    # best[stt] = item có điểm bằng chứng cao nhất qua các chunk
    best = {}
    for res in chunk_results:
        if not res:
            continue
        for item in res.get("items", []):
            stt = item.get("stt")
            if stt is None:
                continue
            score = _evidence_score(item, contract)
            prev = best.get(stt)
            if prev is None or score > prev["_score"]:
                best[stt] = {**item, "_score": score}

    # Lắp lại theo thứ tự stt, bỏ field nội bộ _score
    items = []
    for stt in sorted(best.keys()):
        it = best[stt]
        it.pop("_score", None)
        items.append(it)

    return {"items": items}


def build_summary(result: dict) -> str:
    """Sinh tóm tắt deterministic từ các tiêu chí SAI/THIEU (không gọi LLM)."""
    sai, thieu = [], []
    for it in result.get("items", []):
        tc = (it.get("tieu_chi") or f"Tiêu chí {it.get('stt')}").strip()
        if it.get("ket_qua") == "SAI":
            sai.append(tc)
        elif it.get("ket_qua") == "THIEU":
            thieu.append(tc)

    if not sai and not thieu:
        return "Hợp đồng đáp ứng toàn bộ tiêu chí xét duyệt."

    parts = []
    if sai:
        parts.append(f"{len(sai)} tiêu chí sai/lệch giá trị: " + "; ".join(sai))
    if thieu:
        parts.append(f"{len(thieu)} tiêu chí thiếu: " + "; ".join(thieu))
    return ". ".join(parts) + "."


# ── P1: Định vị theo tiêu chí (retrieval) cho văn bản lớn ─────────────────────

RETRIEVE_WINDOW_CHARS = 5000   # độ rộng đoạn ngữ cảnh gửi kèm mỗi tiêu chí

# Từ dừng tiếng Việt phổ biến — loại khỏi từ khóa truy xuất cho đỡ nhiễu.
_STOPWORDS = set((
    "và của các được trong khi nếu hoặc cho tại theo đến trên dưới với một những "
    "là có không này đó khi sau trước mỗi bằng về như đã sẽ cũng thì mà nên bên "
    "phải tin ngày tháng năm giá đơn"
).split())


def _keywords(text: str) -> list:
    """Trích từ khóa: số/% (trọng số cao) + token chữ >=4 ký tự, bỏ từ dừng."""
    toks = _re.findall(r"\d+(?:[.,]\d+)*%?|[^\W\d_]{4,}", (text or "").lower())
    return [t for t in toks if t not in _STOPWORDS]


def split_criteria(criteria: str):
    """Tách bộ tiêu chí thành (lời dẫn chung, [(stt, nội dung tiêu chí)...]).

    Nhận diện dòng đánh số '1.', '2)'... Dòng không đánh số nối vào tiêu chí trước;
    nếu xuất hiện trước mọi tiêu chí thì coi là lời dẫn chung (áp cho mọi tiêu chí).
    """
    preamble, crits = [], []
    for ln in (criteria or "").split("\n"):
        s = ln.strip()
        if not s:
            continue
        m = _re.match(r"(\d+)\s*[.)]\s*(.+)", s)
        if m:
            crits.append([int(m.group(1)), m.group(2).strip()])
        elif crits:
            crits[-1][1] += " " + s
        else:
            preamble.append(s)
    return "\n".join(preamble), [(stt, txt) for stt, txt in crits]


def retrieve_window(contract: str, criterion: str, max_chars: int = RETRIEVE_WINDOW_CHARS) -> str:
    """Lấy đoạn hợp đồng liên quan nhất tới 1 tiêu chí, theo ranh giới đoạn văn.

    Chấm điểm từng đoạn theo số lần xuất hiện từ khóa (số/% trọng số x3), chọn
    đoạn cao điểm nhất rồi mở rộng sang các đoạn lân cận tới ~max_chars để giữ
    đủ ngữ cảnh (điều khoản không bị cắt ngang như khi chia chunk mù).
    """
    if len(contract) <= max_chars:
        return contract
    kws = _keywords(criterion)
    paras = contract.split("\n")
    if not kws:
        return contract[:max_chars]

    scores = []
    for p in paras:
        pl = p.lower()
        scores.append(sum(pl.count(k) * (3 if k[0].isdigit() else 1) for k in kws))

    best_i = max(range(len(paras)), key=lambda i: scores[i])
    if scores[best_i] == 0:
        return contract[:max_chars]

    # Mở rộng quanh đoạn tốt nhất, ưu tiên phía có điểm cao hơn
    lo = hi = best_i
    size = len(paras[best_i])
    while size < max_chars and (lo > 0 or hi < len(paras) - 1):
        left = scores[lo - 1] if lo > 0 else -1
        right = scores[hi + 1] if hi < len(paras) - 1 else -1
        if right >= left and hi < len(paras) - 1:
            hi += 1
            size += len(paras[hi]) + 1
        elif lo > 0:
            lo -= 1
            size += len(paras[lo]) + 1
        else:
            break
    return "\n".join(paras[lo:hi + 1])


# ── Phát hiện rủi ro NGOÀI tiêu chí ───────────────────────────────────────────

def build_risk_prompt(contract: str) -> str:
    return f"""Bạn là luật sư rà soát rủi ro hợp đồng. Tìm các điều khoản BẤT LỢI / RỦI RO cho bên xét duyệt, KỂ CẢ khi không nằm trong tiêu chí. Ví dụ: phạt một chiều, tự động gia hạn, trách nhiệm/bồi thường không giới hạn, đơn phương chấm dứt bất lợi, chuyển nhượng không cần đồng ý, bảo mật/không cạnh tranh quá rộng, luật áp dụng/cơ quan giải quyết tranh chấp bất lợi, điều khoản mập mờ dễ tranh chấp.

===HỢP ĐỒNG===
{contract}

===QUY TẮC===
- CHỈ liệt kê điều khoản CÓ THẬT trong hợp đồng. trich_dan PHẢI là câu NGUYÊN VĂN copy y hệt. KHÔNG bịa, KHÔNG suy đoán.
- Không có rủi ro đáng kể -> trả mảng rỗng [].
- muc_do chỉ nhận: "cao", "trung", "thap".

===OUTPUT=== Chỉ trả JSON, không markdown:
{{"rui_ro":[{{"mo_ta":"mô tả ngắn rủi ro","muc_do":"cao","trich_dan":"câu nguyên văn từ hợp đồng","ghi_chu":"vì sao rủi ro hoặc gợi ý xử lý"}}]}}"""


def detect_risks(contract: str) -> list:
    """Quét toàn văn tìm điều khoản rủi ro; chỉ giữ mục có trích dẫn xác minh được."""
    from file_parser import split_into_chunks
    if not (contract or "").strip():
        return []

    def _one(text):
        try:
            msgs = [{"role": "user",
                     "content": "You are a strict legal risk reviewer. Respond with valid JSON only. No markdown.\n\n"
                                + build_risk_prompt(text)}]
            return parse_llm_json(call_llm(msgs)).get("rui_ro") or []
        except Exception:
            return []

    if len(contract) <= SINGLE_CALL_MAX_CHARS:
        raw_risks = _one(contract)
    else:
        chunks = split_into_chunks(contract, CHUNK_SIZE_CHARS, CHUNK_OVERLAP_CHARS)
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            parts = list(ex.map(_one, chunks))
        raw_risks = [r for part in parts for r in (part or [])]

    out, seen = [], set()
    for r in raw_risks:
        trich = (r.get("trich_dan") or "").strip()
        span = _flexible_span(contract, trich) if trich else None
        if not span or span in seen:   # bỏ rủi ro không trích dẫn được (chống bịa) + trùng
            continue
        seen.add(span)
        mucdo = str(r.get("muc_do", "")).strip().lower()
        r["muc_do"] = mucdo if mucdo in ("cao", "trung", "thap") else "trung"
        r["trich_start"], r["trich_end"] = span
        r["vi_tri"] = _derive_vi_tri(contract, trich)
        out.append(r)

    rank = {"cao": 0, "trung": 1, "thap": 2}
    out.sort(key=lambda x: (rank.get(x["muc_do"], 1), x["trich_start"]))
    return out


# ── Tự nhận diện loại hợp đồng ────────────────────────────────────────────────

def detect_contract_type(contract: str, store: dict) -> str:
    """Đối chiếu đoạn đầu hợp đồng với nhãn các template -> trả key khớp nhất hoặc ''."""
    listing = "\n".join(f"- {k}: {v.get('label','')}" for k, v in store.items())
    prompt = f"""Cho đoạn đầu hợp đồng dưới đây, chọn LOẠI phù hợp nhất trong danh sách. Nếu không chắc chắn, trả key rỗng. Chỉ trả JSON.

===DANH SÁCH LOẠI===
{listing}

===HỢP ĐỒNG (trích)===
{contract[:4000]}

===OUTPUT=== {{"key":"mã loại khớp nhất hoặc rỗng"}}"""
    try:
        msgs = [{"role": "user", "content": "Respond with valid JSON only.\n\n" + prompt}]
        key = (parse_llm_json(call_llm(msgs, max_tokens=200)).get("key") or "").strip()
        return key if key in store else ""
    except Exception:
        return ""


# ── Chuẩn hóa bộ tiêu chí để LLM đối chiếu chính xác hơn (GIỮ NGUYÊN ý nghĩa) ──

def build_criteria_refine_prompt(criteria: str) -> str:
    return f"""Bạn là chuyên gia chuẩn hóa bộ tiêu chí xét duyệt hợp đồng, để một AI khác đối chiếu hợp đồng CHÍNH XÁC hơn về sau.

Nhiệm vụ: viết lại bộ tiêu chí cho RÕ RÀNG, NHẤT QUÁN, DỄ ĐỐI CHIẾU, nhưng TUYỆT ĐỐI GIỮ NGUYÊN Ý NGHĨA.

===TIÊU CHÍ GỐC===
{criteria}

===ĐƯỢC PHÉP (chỉ về cách diễn đạt/cấu trúc)===
- Đánh số nhất quán, mỗi tiêu chí một dòng.
- Nêu rõ giá trị kỳ vọng kèm đơn vị (vd "Thời hạn thanh toán: 30 ngày"), GIỮ NGUYÊN con số/đơn vị gốc.
- Làm rõ từ ngữ mơ hồ, đại từ; bổ sung đơn vị nếu gốc đã hàm ý rõ.
- Giữ cả dạng số lẫn chữ nếu gốc có (vd "03 (ba) ngày").

===TUYỆT ĐỐI KHÔNG===
- KHÔNG thêm/bớt tiêu chí; KHÔNG thêm/bớt bất kỳ yêu cầu nào.
- KHÔNG đổi bất kỳ con số, tỷ lệ %, số ngày, ngưỡng, đơn vị, tên bên, điều kiện nào.
- KHÔNG đổi chiều so sánh (lớn hơn/nhỏ hơn/bằng/không quá); KHÔNG suy diễn, KHÔNG bịa thêm.
- Tiêu chí nào đã rõ thì giữ gần như nguyên văn.

===OUTPUT=== Chỉ trả JSON, không markdown:
{{"improved":"toàn bộ bộ tiêu chí đã chuẩn hóa","notes":["chỉ ghi các thay đổi VỀ DIỄN ĐẠT đã thực hiện"]}}"""


def _criteria_number_diff(orig: str, new: str) -> list:
    """Guardrail: phát hiện số/đơn vị bị đổi giữa bản gốc và bản đề xuất."""
    o = _extract_unit_values(orig)
    n = _extract_unit_values(new)
    warns = []
    for u in sorted(set(o) | set(n)):
        ov, nv = o.get(u, set()), n.get(u, set())
        if ov != nv:
            warns.append(f"Đơn vị '{u}': gốc {sorted(ov)} ≠ đề xuất {sorted(nv)}")
    return warns


def recommend_criteria(criteria: str) -> dict:
    """Trả bản tiêu chí chuẩn hóa + ghi chú + cảnh báo nếu số/đơn vị bị đổi."""
    msgs = [{"role": "user",
             "content": "Respond with valid JSON only. No markdown.\n\n"
                        + build_criteria_refine_prompt(criteria)}]
    data = parse_llm_json(call_llm(msgs, max_tokens=4000))
    improved = (data.get("improved") or "").strip()
    notes = data.get("notes") or []
    warnings = _criteria_number_diff(criteria, improved) if improved else []
    return {"improved": improved, "notes": notes, "warnings": warnings}


def run_analysis(criteria: str, contract: str) -> dict:
    """Phân tích tiêu chí + quét rủi ro (song song); trả kèm văn bản gốc để tô."""
    from file_parser import clean_text

    contract = clean_text(contract)
    truncated = False
    if len(contract) > HARD_CAP_CHARS:
        contract = contract[:HARD_CAP_CHARS]
        truncated = True

    # Phân tích tiêu chí & quét rủi ro chạy song song (2 luồng độc lập)
    with ThreadPoolExecutor(max_workers=2) as ex:
        fut_main = ex.submit(_analyze_main, criteria, contract, truncated)
        fut_risk = ex.submit(detect_risks, contract)
        result = fut_main.result()
        try:
            result["rui_ro"] = fut_risk.result()
        except Exception:
            result["rui_ro"] = []

    result["_contract"] = contract   # để frontend render cột trái + tô trích dẫn
    return result


def _analyze_main(criteria: str, contract: str, truncated: bool) -> dict:
    """Light (1 call) cho file ngắn; định vị theo tiêu chí cho file lớn."""
    from file_parser import split_into_chunks

    # Map stt -> nội dung tiêu chí GỐC (để hiển thị & đối chiếu số xác định)
    _pre, _crits = split_criteria(criteria)
    cmap = {stt: text for stt, text in _crits}

    # Light: 1 call full-text (văn bản ngắn -> không cần định vị)
    if len(contract) <= SINGLE_CALL_MAX_CHARS:
        result = validate_and_fix(analyze_text(criteria, contract), contract, cmap)
        result["_meta"] = {"mode": "single", "chunks": 1, "truncated": truncated}
        return result

    # ── Văn bản lớn: định vị đúng đoạn cho TỪNG tiêu chí rồi đánh giá ──
    preamble, crits = split_criteria(criteria)
    if crits:
        def _analyze_one(crit):
            stt, text = crit
            window = retrieve_window(contract, text)
            sub = (preamble + "\n" if preamble else "") + f"{stt}. {text}"
            try:
                res = analyze_text(sub, window)
            except Exception:
                return None
            items = res.get("items") or []
            if not items:
                return None
            it = items[0]
            it["stt"] = stt            # ép đúng stt gốc
            it["tieu_chi"] = it.get("tieu_chi") or text
            return it

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            items = [it for it in ex.map(_analyze_one, crits) if it]

        result = validate_and_fix({"items": items}, contract, cmap)
        result["tong_ket"]["tom_tat"] = build_summary(result)
        result["_meta"] = {"mode": "retrieval", "chunks": len(crits), "truncated": truncated}
        return result

    # Fallback (không tách được tiêu chí): map-reduce chia chunk như cũ
    chunks = split_into_chunks(contract, CHUNK_SIZE_CHARS, CHUNK_OVERLAP_CHARS)

    def _safe_analyze(chunk):
        try:
            return analyze_text(criteria, chunk)
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        chunk_results = list(ex.map(_safe_analyze, chunks))

    merged = merge_chunk_results(chunk_results, contract)
    merged = validate_and_fix(merged, contract, cmap)
    merged["tong_ket"]["tom_tat"] = build_summary(merged)
    merged["_meta"] = {"mode": "mapreduce", "chunks": len(chunks), "truncated": truncated}
    return merged


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/criteria", methods=["GET"])
def get_criteria():
    """Return all criteria templates (key → label + criteria text)."""
    return jsonify(load_criteria_store())


@app.route("/detect-type", methods=["POST"])
def detect_type():
    """Tự nhận diện loại hợp đồng từ file/text -> trả key + tiêu chí gợi ý."""
    if request.content_type and "multipart" in request.content_type:
        contract = (request.form.get("contract_text") or "").strip()
        f = request.files.get("contract_file")
        if f and f.filename:
            from file_parser import extract_text
            contract = extract_text(f)
    else:
        body = request.get_json(silent=True) or {}
        contract = (body.get("contract") or "").strip()

    if not contract:
        return jsonify({"key": ""})

    store = load_criteria_store()
    try:
        key = detect_contract_type(contract, store)
    except Exception:
        key = ""
    resp = {"key": key}
    if key:
        resp["label"] = store[key].get("label", "")
        resp["criteria"] = store[key].get("criteria", "")
    return jsonify(resp)


@app.route("/analyze", methods=["POST"])
def analyze():
    # Support both multipart (file upload) and JSON
    if request.content_type and "multipart" in request.content_type:
        criteria = (request.form.get("criteria") or "").strip()
        contract = (request.form.get("contract_text") or "").strip()
        f = request.files.get("contract_file")
        if f and f.filename:
            from file_parser import extract_text
            contract = extract_text(f)
            if not contract.strip():
                return jsonify({"error": "Không đọc được nội dung text từ file. Nếu là PDF scan/ảnh, vui lòng dùng file có lớp text hoặc dán nội dung trực tiếp."}), 400
    else:
        body     = request.get_json(silent=True) or {}
        criteria = (body.get("criteria") or "").strip()
        contract = (body.get("contract") or "").strip()

    if not criteria:
        return jsonify({"error": "Vui lòng nhập tiêu chí xét duyệt"}), 400
    if not contract:
        return jsonify({"error": "Vui lòng nhập nội dung hợp đồng"}), 400

    try:
        result = run_analysis(criteria, contract)
        return jsonify(result)

    except requests.exceptions.Timeout:
        return jsonify({"error": "API timeout — vui lòng thử lại"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Lỗi kết nối API: {str(e)}"}), 502
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Không parse được JSON: {str(e)}"}), 500
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "detail": traceback.format_exc()}), 500


# ── Admin routes ──────────────────────────────────────────────────────────────

@app.route("/admin")
def admin():
    store = load_criteria_store()
    return render_template("admin.html", store=store)


@app.route("/admin/recommend", methods=["POST"])
def admin_recommend():
    """1 bước: LLM chuẩn hóa bộ tiêu chí để đối chiếu chính xác hơn (giữ ý nghĩa)."""
    criteria = (request.form.get("criteria") or "").strip()
    if not criteria:
        return jsonify({"error": "Chưa có nội dung tiêu chí"}), 400
    try:
        return jsonify(recommend_criteria(criteria))
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Lỗi kết nối API: {str(e)}"}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/admin/save", methods=["POST"])
def admin_save():
    store = load_criteria_store()
    key   = (request.form.get("key") or "").strip().lower().replace(" ", "_")
    label = (request.form.get("label") or "").strip()
    criteria = (request.form.get("criteria") or "").strip()

    if not key or not label or not criteria:
        return jsonify({"error": "Thiếu thông tin"}), 400

    store[key] = {"label": label, "criteria": criteria}
    save_criteria_store(store)
    return jsonify({"ok": True, "key": key})


@app.route("/admin/delete/<key>", methods=["POST"])
def admin_delete(key):
    store = load_criteria_store()
    if key not in store:
        return jsonify({"error": "Không tìm thấy"}), 404
    del store[key]
    save_criteria_store(store)
    return jsonify({"ok": True})


if __name__ == "__main__":
    print("Contract Review Agent running at http://localhost:5000")
    app.run(debug=True, port=5000)
