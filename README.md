# Contract Review Agent

AI agent kiểm tra **Hợp đồng / Phụ lục** theo bộ tiêu chí xét duyệt đã thiết lập: tự động đối chiếu nội dung, phát hiện điều khoản chưa phù hợp, đưa ra cảnh báo kèm giải thích và gợi ý phương án điều chỉnh.

Ứng dụng web (Flask) tích hợp LLM, triển khai trên **GreenNode AgentBase**.

▶️ **[Xem video demo (59s)](./Contract%20Review%20Agent.mp4)**

---

## Tính năng

- 📤 **Tải lên hợp đồng** dạng `PDF` hoặc `DOCX`, tự động trích xuất nội dung.
- 🔎 **Tự động nhận diện loại hợp đồng** dựa trên bộ tiêu chí đã lưu.
- ⚖️ **Đối chiếu & phân tích** từng điều khoản với tiêu chí bằng LLM — chỉ ra mục **Đạt / Chưa đạt / Thiếu**, kèm lý do và đề xuất chỉnh sửa.
- 🛠️ **Trang quản trị** (`/admin`) để thêm/sửa/xóa bộ tiêu chí, có hỗ trợ LLM gợi ý tiêu chí.
- 🌐 REST API gọn nhẹ, sẵn sàng đóng gói Docker.

## Công nghệ

| Thành phần | Mô tả |
|-----------|-------|
| Backend | Python 3.12, Flask, Gunicorn |
| Đọc tài liệu | `pypdf`, `pdfplumber`, `python-docx` |
| LLM | API tương thích OpenAI (VNG MaaS) — cấu hình qua biến môi trường |
| Triển khai | Docker, GreenNode AgentBase (port 8080) |

## Cấu trúc thư mục

```
.
├── app.py                 # Flask app: routes, gọi LLM, logic đối chiếu
├── file_parser.py         # Trích xuất văn bản từ PDF/DOCX
├── criteria_store.json    # Kho tiêu chí xét duyệt theo từng loại hợp đồng
├── templates/
│   ├── index.html         # Giao diện tải lên & xem kết quả review
│   └── admin.html         # Giao diện quản trị tiêu chí
├── cr_login.py            # Lấy token đăng nhập Container Registry (AgentBase)
├── iam_login.py           # Lấy IAM token (VNG Cloud)
├── gen_docx.js            # Tạo file DOCX mẫu (tiện ích)
├── gen_docx2.js           # Tạo file DOCX mẫu (tiện ích)
├── Dockerfile             # Đóng gói image (gunicorn, port 8080)
├── agentbase.yaml         # Cấu hình deploy GreenNode AgentBase
├── push.bat               # Tag & push image lên Container Registry
├── requirements.txt
└── vid_assets/            # Script dựng video giới thiệu sản phẩm
    ├── gen_assets.ps1     # Tạo title/panel/icon bằng PowerShell + System.Drawing
    ├── filter.txt         # Kịch bản ffmpeg (cắt/ghép/chèn text theo timeline)
    └── strings.txt        # Nội dung chữ tiếng Việt cho video
```

## Biến môi trường

| Biến | Mô tả |
|------|-------|
| `API_URL` | Endpoint LLM (chat/completions) |
| `MODEL` | Tên model (ví dụ `minimax/minimax-m2.5`) |
| `API_KEY` | Khóa API LLM — **đặt qua Secret, không hardcode** |

Tham khảo `.env.example`. Tạo file `.env` ở local (đã được `.gitignore`).

## Chạy ở máy local

```bash
pip install -r requirements.txt
cp .env.example .env        # rồi điền API_URL / MODEL / API_KEY
python app.py               # chạy dev server tại http://localhost:5000
```

Chạy kiểu production (giống môi trường deploy):

```bash
python -m gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 180 app:app
```

## Triển khai (GreenNode AgentBase)

```bash
docker build -t contract-review:v2 .
push.bat                    # tag & push image lên Container Registry
```

Cấu hình runtime trong `agentbase.yaml` (flavor, port 8080, visibility, secret `API_KEY`).

## API

| Method | Endpoint | Chức năng |
|--------|----------|-----------|
| `GET`  | `/` | Giao diện tải lên & review |
| `GET`  | `/health` | Health check |
| `GET`  | `/criteria` | Lấy toàn bộ bộ tiêu chí |
| `POST` | `/detect-type` | Nhận diện loại hợp đồng từ nội dung |
| `POST` | `/analyze` | Đối chiếu hợp đồng với tiêu chí, trả kết quả review |
| `GET`  | `/admin` | Trang quản trị tiêu chí |
| `POST` | `/admin/recommend` | LLM gợi ý tiêu chí |
| `POST` | `/admin/save` | Lưu bộ tiêu chí |
| `POST` | `/admin/delete/<key>` | Xóa một bộ tiêu chí |

## Video giới thiệu

▶️ **[Xem video demo — Contract Review Agent.mp4](./Contract%20Review%20Agent.mp4)** (59 giây)

> Bấm vào link trên để mở trình phát video của GitHub.

Thư mục `vid_assets/` chứa script dựng video demo bằng **ffmpeg** + **PowerShell**. Chỉ gồm script và nội dung — media nặng và nhạc nền (royalty-free, CC BY) không được đưa lên repo. Nếu dùng nhạc khi phát hành cần ghi credit tác giả.

---

> Lưu ý: các file chứa thông tin nhạy cảm (`.env`, `.greennode.json`, `iam-credentials.json`) đã được loại khỏi repo qua `.gitignore`.
