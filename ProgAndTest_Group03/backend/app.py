from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pymysql, pymysql.cursors
import hashlib, jwt, datetime
from functools import wraps
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, SECRET_KEY, DEBUG, PORT

app = Flask(__name__)
CORS(app, origins='*', allow_headers=['Content-Type','Authorization'], methods=['GET','POST','PUT','DELETE','OPTIONS'])

# DB 
def get_db():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor, autocommit=False
    )

def qone(sql, p=()):
    conn = get_db()
    try:
        with conn.cursor() as c: c.execute(sql, p); return c.fetchone()
    finally: conn.close()

def qall(sql, p=()):
    conn = get_db()
    try:
        with conn.cursor() as c: c.execute(sql, p); return c.fetchall()
    finally: conn.close()

def exe(sql, p=()):
    conn = get_db()
    try:
        with conn.cursor() as c: c.execute(sql, p); conn.commit(); return c.lastrowid
    except: conn.rollback(); raise
    finally: conn.close()

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def ser(row):
    """Convert datetime objects to string for JSON."""
    if not row: return row
    out = {}
    for k, v in row.items():
        out[k] = v.strftime('%Y-%m-%d %H:%M:%S') if hasattr(v, 'strftime') else v
    return out

def ser_list(rows): return [ser(r) for r in (rows or [])]

# JWT AUTH 
def make_token(user_id, role):
    payload = {
        'sub': str(user_id),
        'role': role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def decode_token():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '): return None, None
    try:
        payload = jwt.decode(auth[7:], SECRET_KEY, algorithms=['HS256'])
        return int(payload['sub']), payload['role']
    except: return None, None

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        uid, role = decode_token()
        if not uid: return jsonify({'success': False, 'message': 'No logged in'}), 401
        request.uid = uid; request.role = role
        return f(*args, **kwargs)
    return wrapper

def role_required(*roles):
    def dec(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            uid, role = decode_token()
            if not uid: return jsonify({'success': False, 'message': 'No logged in'}), 401
            if role not in roles: return jsonify({'success': False, 'message': 'Permission denied'}), 403
            request.uid = uid; request.role = role
            return f(*args, **kwargs)
        return wrapper
    return dec

#  INIT DB
def init_db():
    conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER,
                           password=DB_PASSWORD, charset='utf8mb4', autocommit=True)
    with conn.cursor() as c:
        c.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn.close()

    conn = get_db()
    with conn.cursor() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(150) NOT NULL,
            email VARCHAR(150) UNIQUE NOT NULL,
            password VARCHAR(64) NOT NULL,
            role ENUM('student','teacher','admin') NOT NULL,
            phone VARCHAR(20), address VARCHAR(255),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')

        c.execute('''CREATE TABLE IF NOT EXISTS courses (
            id INT AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            credits INT DEFAULT 3,
            max_students INT DEFAULT 40,
            teacher_id INT,
            semester VARCHAR(20),
            FOREIGN KEY(teacher_id) REFERENCES users(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')

        c.execute('''CREATE TABLE IF NOT EXISTS enrollments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT NOT NULL,
            course_id INT NOT NULL,
            enrolled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            status ENUM('active','dropped') DEFAULT 'active',
            UNIQUE KEY uq_enroll(student_id,course_id),
            FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')

        c.execute('''CREATE TABLE IF NOT EXISTS grades (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT NOT NULL,
            course_id INT NOT NULL,
            grade DECIMAL(4,2),
            letter_grade CHAR(2),
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_grade(student_id,course_id),
            FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
        conn.commit()

        # Seed users
        seeds = [
            ('Administrator',  'admin@edums.edu',    'admin123',   'admin'),
            ('Nguyễn Văn An',  'teacher1@edums.edu', 'teacher123', 'teacher'),
            ('Trần Thị Bình',  'teacher2@edums.edu', 'teacher123', 'teacher'),
            ('Lê Văn Cường',   'student1@edums.edu', 'student123', 'student'),
            ('Phạm Thị Dung',  'student2@edums.edu', 'student123', 'student'),
            ('Hoàng Minh Đức', 'student3@edums.edu', 'student123', 'student'),
        ]
        for name, email, pw, role in seeds:
            c.execute("SELECT id FROM users WHERE email=%s", (email,))
            if not c.fetchone():
                c.execute("INSERT INTO users(full_name,email,password,role) VALUES(%s,%s,%s,%s)",
                          (name, email, hash_pw(pw), role))

        conn.commit()

        # Get IDs
        def uid(email):
            c.execute("SELECT id FROM users WHERE email=%s", (email,)); r = c.fetchone(); return r['id'] if r else None

        t1, t2 = uid('teacher1@edums.edu'), uid('teacher2@edums.edu')
        s1, s2, s3 = uid('student1@edums.edu'), uid('student2@edums.edu'), uid('student3@edums.edu')

        course_seeds = [
            ('CS101',   'Lập trình cơ bản',       'Nhập môn lập trình với Python',      3, 40, t1, '2024-1'),
            ('CS201',   'Cấu trúc dữ liệu',        'Các cấu trúc dữ liệu và giải thuật', 3, 35, t1, '2024-1'),
            ('MATH101', 'Giải tích 1',              'Toán cao cấp – Giải tích',           4, 50, t2, '2024-1'),
            ('MATH201', 'Đại số tuyến tính',        'Ma trận và không gian vector',       3, 45, t2, '2024-1'),
            ('CS301',   'Cơ sở dữ liệu',            'Thiết kế và quản lý CSDL',           3, 30, t1, '2024-1'),
            ('ENG101',  'Tiếng Anh chuyên ngành',   'English for IT professionals',       2, 50, t2, '2024-1'),
        ]
        cids = {}
        for code, name, desc, cr, mx, tid, sem in course_seeds:
            c.execute("SELECT id FROM courses WHERE code=%s", (code,))
            row = c.fetchone()
            if not row:
                c.execute("INSERT INTO courses(code,name,description,credits,max_students,teacher_id,semester) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                          (code, name, desc, cr, mx, tid, sem))
                cids[code] = c.lastrowid
            else:
                cids[code] = row['id']
        conn.commit()

        # Enrollments
        enroll_map = {
            s1: ['CS101','CS201','MATH101'],
            s2: ['CS101','MATH101','MATH201'],
            s3: ['CS201','CS301','ENG101'],
        }
        grade_map = {
            (s1,'CS101'): 8.5, (s1,'CS201'): 7.0, (s1,'MATH101'): 6.0,
            (s2,'CS101'): 9.0, (s2,'MATH101'): 7.5, (s2,'MATH201'): 8.0,
            (s3,'CS201'): 6.5, (s3,'CS301'): 8.0,
        }
        for sid, codes in enroll_map.items():
            for code in codes:
                cid = cids.get(code)
                if not cid: continue
                c.execute("INSERT IGNORE INTO enrollments(student_id,course_id) VALUES(%s,%s)", (sid, cid))
        conn.commit()

        def letter(g): return 'A' if g>=8.5 else 'B+' if g>=8.0 else 'B' if g>=7.0 else 'C+' if g>=6.5 else 'C' if g>=5.5 else 'D+' if g>=5.0 else 'D' if g>=4.0 else 'F'
        for (sid, code), g in grade_map.items():
            cid = cids.get(code)
            if not cid: continue
            c.execute("INSERT IGNORE INTO grades(student_id,course_id,grade,letter_grade) VALUES(%s,%s,%s,%s)",
                      (sid, cid, g, letter(g)))
        conn.commit()

    conn.close()
    print(f"[EduMS] MySQL database '{DB_NAME}' ready ✓")

# AUTH ROUTES
@app.route('/api/login', methods=['POST'])
def login():
    d = request.get_json(force=True) or {}
    email = (d.get('email') or '').strip().lower()
    pw    = d.get('password') or ''
    if not email or not pw:
        return jsonify({'success': False, 'message': 'Please enter password and email!'}), 400
    user = qone("SELECT id,full_name,email,role FROM users WHERE email=%s AND password=%s",
                (email, hash_pw(pw)))
    if not user:
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
    token = make_token(user['id'], user['role'])
    return jsonify({'success': True, 'token': token, 'user': ser(user)})

@app.route('/api/register', methods=['POST'])
def register():
    d = request.get_json(force=True) or {}
    name  = (d.get('full_name') or '').strip()
    email = (d.get('email') or '').strip().lower()
    pw    = d.get('password') or ''
    role  = d.get('role', 'student')
    if not name or not email or not pw:
        return jsonify({'success': False, 'message': 'Please fill in all fields.'}), 400
    if len(pw) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters long.'}), 400
    if role not in ('student','teacher'): role = 'student'
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("SELECT id FROM users WHERE email=%s", (email,))
            if c.fetchone(): return jsonify({'success': False, 'message': 'Email is already in use'}), 400
            c.execute("INSERT INTO users(full_name,email,password,role) VALUES(%s,%s,%s,%s)",
                      (name, email, hash_pw(pw), role))
            conn.commit()
        return jsonify({'success': True, 'message': 'Email is already in use'})
    except Exception as e: conn.rollback(); return jsonify({'success': False, 'message': str(e)}), 500
    finally: conn.close()

@app.route('/api/me', methods=['GET'])
@login_required
def me():
    user = qone("SELECT id,full_name,email,role,phone,address FROM users WHERE id=%s", (request.uid,))
    if not user: return jsonify({'success': False}), 401
    return jsonify({'success': True, 'user': ser(user)})

@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    d = request.get_json(force=True) or {}
    name    = (d.get('full_name') or '').strip()
    phone   = (d.get('phone') or '').strip() or None
    address = (d.get('address') or '').strip() or None
    pw      = d.get('password') or ''
    if not name: return jsonify({'success': False, 'message': 'Full name is required'}), 400
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("UPDATE users SET full_name=%s,phone=%s,address=%s WHERE id=%s",
                      (name, phone, address, request.uid))
            if pw:
                if len(pw) < 6: return jsonify({'success': False, 'message': 'Password >= 6 characters'}), 400
                c.execute("UPDATE users SET password=%s WHERE id=%s", (hash_pw(pw), request.uid))
            conn.commit()
        return jsonify({'success': True, 'message': 'Update successfully'})
    except Exception as e: conn.rollback(); return jsonify({'success': False, 'message': str(e)}), 500
    finally: conn.close()

#  COURSES 
@app.route('/api/courses', methods=['GET'])
@login_required
def get_courses():
    rows = qall('''
        SELECT c.*, u.full_name AS teacher_name,
               (SELECT COUNT(*) FROM enrollments e WHERE e.course_id=c.id AND e.status='active') AS enrolled_count
        FROM courses c LEFT JOIN users u ON c.teacher_id=u.id ORDER BY c.code
    ''')
    return jsonify(ser_list(rows))

@app.route('/api/courses', methods=['POST'])
@role_required('admin')
def create_course():
    d = request.get_json(force=True) or {}
    code = (d.get('code') or '').strip().upper()
    name = (d.get('name') or '').strip()
    if not code or not name: return jsonify({'success': False, 'message': 'Course code and course name are required'}), 400
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("SELECT id FROM courses WHERE code=%s", (code,))
            if c.fetchone(): return jsonify({'success': False, 'message': 'Course code already exists'}), 400
            c.execute("INSERT INTO courses(code,name,description,credits,max_students,teacher_id,semester) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                      (code, name, d.get('description') or None, int(d.get('credits') or 3),
                       int(d.get('max_students') or 40), d.get('teacher_id') or None, d.get('semester') or None))
            conn.commit()
        return jsonify({'success': True})
    except Exception as e: conn.rollback(); return jsonify({'success': False, 'message': str(e)}), 500
    finally: conn.close()

@app.route('/api/courses/<int:cid>', methods=['PUT'])
@role_required('admin')
def update_course(cid):
    d = request.get_json(force=True) or {}
    name = (d.get('name') or '').strip()
    if not name: return jsonify({'success': False, 'message': 'Course name is required'}), 400
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("UPDATE courses SET name=%s,description=%s,credits=%s,max_students=%s,teacher_id=%s,semester=%s WHERE id=%s",
                      (name, d.get('description') or None, int(d.get('credits') or 3),
                       int(d.get('max_students') or 40), d.get('teacher_id') or None, d.get('semester') or None, cid))
            conn.commit()
        return jsonify({'success': True})
    except Exception as e: conn.rollback(); return jsonify({'success': False, 'message': str(e)}), 500
    finally: conn.close()

@app.route('/api/courses/<int:cid>', methods=['DELETE'])
@role_required('admin')
def delete_course(cid):
    exe("DELETE FROM courses WHERE id=%s", (cid,))
    return jsonify({'success': True})

# ENROLLMENTS 
@app.route('/api/enrollments', methods=['GET'])
@login_required
def get_my_enrollments():
    rows = qall('''
        SELECT e.id, e.course_id, e.enrolled_at, e.status,
               c.name AS course_name, c.code, c.credits, c.semester,
               u.full_name AS teacher_name,
               g.grade, g.letter_grade
        FROM enrollments e
        JOIN courses c ON e.course_id=c.id
        LEFT JOIN users u ON c.teacher_id=u.id
        LEFT JOIN grades g ON g.student_id=e.student_id AND g.course_id=e.course_id
        WHERE e.student_id=%s AND e.status='active' ORDER BY c.code
    ''', (request.uid,))
    result = ser_list(rows)
    for r in result:
        if r.get('grade') is not None: r['grade'] = float(r['grade'])
    return jsonify(result)

@app.route('/api/enrollments/all', methods=['GET'])
@role_required('admin')
def get_all_enrollments():
    rows = qall('''
        SELECT e.id, e.enrolled_at, e.status, e.student_id, e.course_id,
               u.full_name AS student_name, c.name AS course_name, c.code
        FROM enrollments e
        JOIN users u ON e.student_id=u.id
        JOIN courses c ON e.course_id=c.id
        ORDER BY e.enrolled_at DESC
    ''')
    return jsonify(ser_list(rows))

@app.route('/api/enroll', methods=['POST'])
@login_required
def enroll():
    d = request.get_json(force=True) or {}
    cid = d.get('course_id')
    # Admin can enroll on behalf of student
    sid = d.get('student_id_override') if request.role == 'admin' else request.uid
    if not sid: sid = request.uid
    if not cid: return jsonify({'success': False, 'message': 'Course ID is required'}), 400
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("SELECT id,max_students FROM courses WHERE id=%s", (cid,))
            course = c.fetchone()
            if not course: return jsonify({'success': False, 'message': 'Course not found'}), 404
            c.execute("SELECT COUNT(*) AS cnt FROM enrollments WHERE course_id=%s AND status='active'", (cid,))
            if c.fetchone()['cnt'] >= course['max_students']:
                return jsonify({'success': False, 'message': 'Course is full'}), 400
            c.execute("SELECT id,status FROM enrollments WHERE student_id=%s AND course_id=%s", (sid, cid))
            ex = c.fetchone()
            if ex:
                if ex['status'] == 'active': return jsonify({'success': False, 'message': 'You have already enrolled in this course'}), 400
                c.execute("UPDATE enrollments SET status='active',enrolled_at=NOW() WHERE id=%s", (ex['id'],))
            else:
                c.execute("INSERT INTO enrollments(student_id,course_id) VALUES(%s,%s)", (sid, cid))
            conn.commit()
        return jsonify({'success': True, 'message': 'Enrollment Successfully'})
    except Exception as e: conn.rollback(); return jsonify({'success': False, 'message': str(e)}), 500
    finally: conn.close()

@app.route('/api/enrollments/<int:eid>', methods=['DELETE'])
@login_required
def drop_enrollment(eid):
    conn = get_db()
    try:
        with conn.cursor() as c:
            if request.role == 'admin':
                c.execute("SELECT id FROM enrollments WHERE id=%s", (eid,))
            else:
                c.execute("SELECT id FROM enrollments WHERE id=%s AND student_id=%s", (eid, request.uid))
            if not c.fetchone(): return jsonify({'success': False, 'message': 'Not found'}), 404
            c.execute("UPDATE enrollments SET status='dropped' WHERE id=%s", (eid,))
            conn.commit()
        return jsonify({'success': True})
    except Exception as e: conn.rollback(); return jsonify({'success': False, 'message': str(e)}), 500
    finally: conn.close()

# GRADES
def letter(g): return 'A' if g>=8.5 else 'B+' if g>=8.0 else 'B' if g>=7.0 else 'C+' if g>=6.5 else 'C' if g>=5.5 else 'D+' if g>=5.0 else 'D' if g>=4.0 else 'F'

@app.route('/api/grades', methods=['GET'])
@login_required
def get_my_grades():
    rows = qall('''
        SELECT g.id, g.grade, g.letter_grade, g.updated_at,
               c.id AS course_id, c.name AS course_name, c.code, c.credits
        FROM grades g JOIN courses c ON g.course_id=c.id
        WHERE g.student_id=%s ORDER BY c.code
    ''', (request.uid,))
    result = ser_list(rows)
    for r in result:
        if r.get('grade') is not None: r['grade'] = float(r['grade'])
    return jsonify(result)

@app.route('/api/courses/<int:cid>/students', methods=['GET'])
@role_required('teacher','admin')
def get_course_students(cid):
    if request.role == 'teacher':
        course = qone("SELECT teacher_id FROM courses WHERE id=%s", (cid,))
        if not course or course['teacher_id'] != request.uid:
            return jsonify({'success': False, 'message': 'No permission to view this class'}), 403
    rows = qall('''
        SELECT u.id AS student_id, u.full_name, u.email,
               e.id AS enrollment_id, g.grade, g.letter_grade
        FROM enrollments e
        JOIN users u ON e.student_id=u.id
        LEFT JOIN grades g ON g.student_id=u.id AND g.course_id=%s
        WHERE e.course_id=%s AND e.status='active' ORDER BY u.full_name
    ''', (cid, cid))
    result = ser_list(rows)
    for r in result:
        if r.get('grade') is not None: r['grade'] = float(r['grade'])
    return jsonify(result)

@app.route('/api/grades', methods=['POST'])
@role_required('teacher','admin')
def save_grade():
    d = request.get_json(force=True) or {}
    sid, cid, gval = d.get('student_id'), d.get('course_id'), d.get('grade')
    if sid is None or cid is None or gval is None:
        return jsonify({'success': False, 'message': 'Information is required'}), 400
    try: gval = float(gval)
    except: return jsonify({'success': False, 'message': 'Invalid grade'}), 400
    if not 0 <= gval <= 10: return jsonify({'success': False, 'message': 'The grade must be between 0 and 10'}), 400
    if request.role == 'teacher':
        c = qone("SELECT teacher_id FROM courses WHERE id=%s", (cid,))
        if not c or c['teacher_id'] != request.uid:
            return jsonify({'success': False, 'message': 'You are not allowed to enter grades for this course'}), 403
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute('''INSERT INTO grades(student_id,course_id,grade,letter_grade)
                         VALUES(%s,%s,%s,%s)
                         ON DUPLICATE KEY UPDATE grade=VALUES(grade),letter_grade=VALUES(letter_grade),updated_at=NOW()''',
                      (sid, cid, gval, letter(gval)))
            conn.commit()
        return jsonify({'success': True})
    except Exception as e: conn.rollback(); return jsonify({'success': False, 'message': str(e)}), 500
    finally: conn.close()

#  USERS (ADMIN)
@app.route('/api/users', methods=['GET'])
@role_required('admin')
def get_users():
    role = request.args.get('role')
    if role:
        rows = qall("SELECT id,full_name,email,role,phone,address,created_at FROM users WHERE role=%s ORDER BY full_name", (role,))
    else:
        rows = qall("SELECT id,full_name,email,role,phone,address,created_at FROM users ORDER BY role,full_name")
    return jsonify(ser_list(rows))

@app.route('/api/users', methods=['POST'])
@role_required('admin')
def create_user():
    d = request.get_json(force=True) or {}
    name  = (d.get('full_name') or '').strip()
    email = (d.get('email') or '').strip().lower()
    role  = d.get('role','student')
    pw    = d.get('password') or '123456'
    if not name or not email: return jsonify({'success': False, 'message': 'Missing required information'}), 400
    if role not in ('student','teacher','admin'): return jsonify({'success': False, 'message': 'Invalid role'}), 400
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("SELECT id FROM users WHERE email=%s", (email,))
            if c.fetchone(): return jsonify({'success': False, 'message': 'Email already exists'}), 400
            c.execute("INSERT INTO users(full_name,email,password,role,phone,address) VALUES(%s,%s,%s,%s,%s,%s)",
                      (name, email, hash_pw(pw), role, d.get('phone') or None, d.get('address') or None))
            conn.commit()
        return jsonify({'success': True})
    except Exception as e: conn.rollback(); return jsonify({'success': False, 'message': str(e)}), 500
    finally: conn.close()

@app.route('/api/users/<int:tid>', methods=['PUT'])
@role_required('admin')
def update_user(tid):
    d = request.get_json(force=True) or {}
    name  = (d.get('full_name') or '').strip()
    email = (d.get('email') or '').strip().lower()
    if not name or not email: return jsonify({'success': False, 'message': 'Information is required'}), 400
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("SELECT id FROM users WHERE email=%s AND id!=%s", (email, tid))
            if c.fetchone(): return jsonify({'success': False, 'message': 'This email is already associated with another account'}), 400
            c.execute("UPDATE users SET full_name=%s,email=%s,phone=%s,address=%s WHERE id=%s",
                      (name, email, d.get('phone') or None, d.get('address') or None, tid))
            if d.get('password'):
                c.execute("UPDATE users SET password=%s WHERE id=%s", (hash_pw(d['password']), tid))
            conn.commit()
        return jsonify({'success': True})
    except Exception as e: conn.rollback(); return jsonify({'success': False, 'message': str(e)}), 500
    finally: conn.close()

@app.route('/api/users/<int:tid>', methods=['DELETE'])
@role_required('admin')
def delete_user(tid):
    if tid == request.uid: return jsonify({'success': False, 'message': 'You cannot delete your own account'}), 400
    exe("DELETE FROM users WHERE id=%s", (tid,))
    return jsonify({'success': True})

@app.route('/api/stats', methods=['GET'])
@role_required('admin')
def stats():
    return jsonify({
        'students':    qone("SELECT COUNT(*) AS c FROM users WHERE role='student'")['c'],
        'teachers':    qone("SELECT COUNT(*) AS c FROM users WHERE role='teacher'")['c'],
        'courses':     qone("SELECT COUNT(*) AS c FROM courses")['c'],
        'enrollments': qone("SELECT COUNT(*) AS c FROM enrollments WHERE status='active'")['c'],
    })

@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('frontend', path)

if __name__ == '__main__':
    init_db()
    app.run(debug=DEBUG, port=PORT, host='0.0.0.0')
