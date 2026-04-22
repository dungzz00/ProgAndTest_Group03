# 🎓 EduMS v3 — Hệ thống Quản lý Sinh viên (MySQL)

---

## ⚡ Cài đặt nhanh (3 bước)

### Bước 1 — Cấu hình MySQL
Mở file `backend/config.py` và chỉnh sửa thông tin kết nối:

```python
DB_HOST     = 'localhost'
DB_PORT     = 3306
DB_USER     = 'root'        # <- thay bằng user MySQL của bạn
DB_PASSWORD = '123456'      # <- thay bằng mật khẩu MySQL của bạn
DB_NAME     = 'edums'       # database sẽ được tự động tạo
```

> **Lưu ý:** Database `edums` sẽ được tự động tạo khi chạy lần đầu.

### Bước 2 — Cài thư viện & chạy Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
```
Backend chạy tại: `http://localhost:5000`

### Bước 3 — Chạy Frontend (terminal mới)
```bash
# Từ thư mục gốc chứa folder sms2/
python -m http.server 8080
```
Mở trình duyệt: **`http://localhost:8080/frontend/index.html`**

---

## 👤 Tài khoản demo

| Vai trò | Email | Mật khẩu |
|---------|-------|-----------|
| Admin | admin@edums.edu | admin123 |
| Giảng viên | teacher1@edums.edu | teacher123 |
| Giảng viên | teacher2@edums.edu | teacher123 |
| Sinh viên | student1@edums.edu | student123 |
| Sinh viên | student2@edums.edu | student123 |
| Sinh viên | student3@edums.edu | student123 |

---

## 📁 Cấu trúc dự án

```
sms2/
├── backend/
│   ├── app.py              # Flask API (MySQL)
│   ├── config.py           # ← Chỉnh thông tin MySQL ở đây
│   └── requirements.txt
├── frontend/
│   ├── index.html          # Trang đăng nhập / đăng ký
│   ├── css/style.css
│   ├── js/app.js
│   └── pages/
│       ├── student.html
│       ├── teacher.html
│       └── admin.html
└── README.md
```

---

## ✅ Tính năng đã hoàn thiện

### Sinh viên
- [x] Dashboard với GPA, số môn đăng ký, thống kê điểm
- [x] Duyệt & đăng ký môn học (kiểm tra sĩ số, trùng lặp)
- [x] Hủy đăng ký môn học
- [x] Xem bảng điểm & GPA tích lũy + tổng tín chỉ
- [x] Cập nhật hồ sơ cá nhân & đổi mật khẩu

### Giảng viên
- [x] Xem danh sách môn học được phân công
- [x] Nhập/cập nhật điểm từng sinh viên (ON DUPLICATE KEY UPDATE)
- [x] Hiển thị điểm cũ, tự tính xếp loại (A/B/C/D)
- [x] Cập nhật hồ sơ cá nhân

### Quản trị viên (Admin)
- [x] Dashboard tổng quan (stats từ MySQL)
- [x] CRUD Sinh viên (thêm/sửa/xóa + kiểm tra email trùng)
- [x] CRUD Giảng viên
- [x] CRUD Môn học (phân công giảng viên, kiểm tra mã trùng)
- [x] Quản lý đăng ký môn học (thêm/hủy, lọc theo trạng thái)
- [x] Không thể xóa chính mình

### Hệ thống
- [x] MySQL thay SQLite hoàn toàn
- [x] Session-based auth với Flask
- [x] CORS đúng cấu hình
- [x] Phân quyền API (student/teacher/admin)
- [x] Password hash SHA-256
- [x] ON DUPLICATE KEY UPDATE cho điểm
- [x] INSERT IGNORE cho đăng ký lại sau khi hủy
- [x] Validate dữ liệu đầu vào ở backend
- [x] Error handling đầy đủ

---

## 🗄️ Cấu trúc Database (MySQL)

```sql
users         (id, full_name, email, password, role, phone, address, created_at)
courses       (id, code, name, description, credits, max_students, teacher_id, semester)
enrollments   (id, student_id, course_id, enrolled_at, status)
grades        (id, student_id, course_id, grade, letter_grade, updated_at)
```

---

## 🔌 API Endpoints

| Method | Endpoint | Quyền | Mô tả |
|--------|----------|-------|-------|
| POST | /api/login | Public | Đăng nhập |
| POST | /api/logout | Auth | Đăng xuất |
| POST | /api/register | Public | Đăng ký |
| GET | /api/me | Auth | Thông tin bản thân |
| PUT | /api/profile | Auth | Cập nhật hồ sơ |
| GET | /api/courses | Auth | Danh sách môn học |
| POST | /api/courses | Admin | Thêm môn học |
| PUT | /api/courses/:id | Admin | Sửa môn học |
| DELETE | /api/courses/:id | Admin | Xóa môn học |
| GET | /api/enrollments | Student | Môn đã đăng ký (bản thân) |
| GET | /api/enrollments/all | Admin | Tất cả đăng ký |
| POST | /api/enroll | Auth | Đăng ký môn học |
| DELETE | /api/enrollments/:id | Auth | Hủy đăng ký |
| GET | /api/grades | Student | Điểm bản thân |
| GET | /api/courses/:id/students | Teacher/Admin | Sinh viên trong lớp |
| POST | /api/grades | Teacher/Admin | Nhập/cập nhật điểm |
| GET | /api/users | Admin | Danh sách users |
| POST | /api/users | Admin | Thêm user |
| PUT | /api/users/:id | Admin | Sửa user |
| DELETE | /api/users/:id | Admin | Xóa user |
| GET | /api/stats | Admin | Thống kê |
