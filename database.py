# database.py
# ------------------------------------------------------------
# SQLite 데이터베이스 관련 코드를 전부 모아둔 파일입니다.
# - 테이블 스키마 생성(init_db)
# - 각 테이블에 대한 CRUD(생성/조회/수정/삭제) 함수
# 화면(views) 코드에서는 SQL을 직접 쓰지 않고, 이 파일의 함수를 호출하기만 하면 됩니다.
# (이렇게 분리하면 나중에 DB를 PostgreSQL 등으로 바꿀 때 이 파일만 고치면 됩니다.)
# ------------------------------------------------------------

import sqlite3   # 파이썬 표준 SQLite 드라이버 (별도 설치 불필요)
import json      # 리스트/딕셔너리 데이터를 문자열로 저장하기 위해 사용 (예: 핵심개념 목록)
from datetime import datetime
from config import DB_PATH


def get_connection():
    """
    SQLite DB 커넥션(연결 객체)을 만들어 반환합니다.
    - check_same_thread=False : Streamlit은 요청마다 스레드를 다르게 쓸 수 있어서
      기본값(True)으로 두면 "다른 스레드에서 생성된 커넥션" 에러가 날 수 있습니다.
    - row_factory = sqlite3.Row : 조회 결과를 dict처럼 컬럼명으로 접근할 수 있게 해줍니다.
      (예: row["name"] 처럼 사용 가능, row[0] 같은 인덱스 접근보다 훨씬 가독성이 좋음)
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    앱이 처음 실행될 때 한 번 호출되어, 필요한 테이블들을 생성합니다.
    "CREATE TABLE IF NOT EXISTS" 를 사용하므로 이미 테이블이 있으면 아무 일도 하지 않습니다.
    """
    conn = get_connection()
    cur = conn.cursor()  # cursor: SQL 명령을 실행하는 통로 역할을 하는 객체

    # ---------------- users : 학생/교사 계정 ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,   -- 자동 증가하는 고유 번호
            role TEXT NOT NULL,                      -- 'student' 또는 'teacher'
            username TEXT UNIQUE NOT NULL,           -- 로그인 아이디 (중복 불가)
            password_hash TEXT NOT NULL,             -- 해시 처리된 비밀번호 (평문 저장 금지!)
            name TEXT NOT NULL,                      -- 이름
            school TEXT,                             -- 학교명
            grade TEXT,                               -- 학년
            class_no TEXT,                            -- 반
            student_no TEXT,                          -- 번호
            gender TEXT,                               -- 성별 (문항검토 화면에서 사용)
            created_at TEXT NOT NULL
        )
    """)

    # ---------------- assignments : 과제(단원/성취기준/평가문항) ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_name TEXT NOT NULL,                 -- 단원명 (예: 고체지구 - 판구조론)
            achievement_standard TEXT NOT NULL,       -- 성취기준 코드+설명
            title TEXT NOT NULL,                      -- 과제명
            question_text TEXT NOT NULL,              -- 평가문항(서술형 질문)
            core_concepts TEXT,                       -- 핵심개념 목록 (JSON 문자열로 저장)
            deadline TEXT,                             -- 과제 마감일시
            retest_count INTEGER DEFAULT 10,           -- 재검사 문항 수
            example_answer TEXT,                        -- 예시답안 (선택)
            status TEXT DEFAULT '배포전',                -- 배포 상태: '배포전' | '배포중'
            sort_order INTEGER,                          -- 과제 조회 화면에서 교사가 드래그로 정한 순서
            created_by INTEGER,                          -- 생성한 교사의 user id
            created_at TEXT NOT NULL
        )
    """)

    # 기존에 만들어진 DB 파일에는 sort_order 컬럼이 없을 수 있으므로 안전하게 추가합니다.
    # (이미 컬럼이 있으면 sqlite3.OperationalError가 나는데, 그건 무시하고 넘어갑니다.)
    try:
        cur.execute("ALTER TABLE assignments ADD COLUMN sort_order INTEGER")
    except sqlite3.OperationalError:
        pass

    # ---------------- eval_criteria : 평가요소/배점/채점기준 (과제 1:N) ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS eval_criteria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            element_name TEXT NOT NULL,     -- 평가요소 (예: 발산형 경계 설명)
            score INTEGER NOT NULL,          -- 배점
            criteria_text TEXT NOT NULL,      -- 채점기준 서술
            FOREIGN KEY (assignment_id) REFERENCES assignments(id)
        )
    """)

    # ---------------- submissions : 학생의 과제 PDF 제출 기록 ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            pdf_filename TEXT NOT NULL,        -- 저장된 파일명
            pdf_path TEXT NOT NULL,             -- 저장 경로 (uploads/ 하위)
            submitted_at TEXT NOT NULL,
            FOREIGN KEY (assignment_id) REFERENCES assignments(id),
            FOREIGN KEY (student_id) REFERENCES users(id)
        )
    """)

    # ---------------- extra_submissions : AI가 제안한 보충/심화 '추가 과제'를 학생이 선택적으로 제출 ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS extra_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            pdf_filename TEXT NOT NULL,
            pdf_path TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            FOREIGN KEY (assignment_id) REFERENCES assignments(id),
            FOREIGN KEY (student_id) REFERENCES users(id)
        )
    """)

    # ---------------- retest_questions : 과제별 재검사(이해도 확인) 문항 은행 ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS retest_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            question_type TEXT DEFAULT 'mc',    -- 'mc'(객관식) 또는 'short'(단답형)
            choices TEXT,                        -- 객관식 보기 (JSON 문자열 리스트)
            answer TEXT NOT NULL,                 -- 정답
            FOREIGN KEY (assignment_id) REFERENCES assignments(id)
        )
    """)

    # ---------------- retest_assignments : 학생별로 "이 학생에게 배정된 재검사 문항" ----------------
    # AI가 학생 답안을 근거로 문항을 선정했다는 시나리오를 표현하기 위한 매핑 테이블입니다.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS retest_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            ai_reason TEXT,                        -- AI가 이 문항을 고른 이유(근거)
            basis_page INTEGER,                      -- 근거가 된 학생 답안 PDF 페이지 번호
            basis_quote TEXT,                          -- 근거가 된 학생 답안 원문 인용
            FOREIGN KEY (question_id) REFERENCES retest_questions(id)
        )
    """)
    for ddl in (
        "ALTER TABLE retest_assignments ADD COLUMN basis_page INTEGER",
        "ALTER TABLE retest_assignments ADD COLUMN basis_quote TEXT",
        "ALTER TABLE retest_assignments ADD COLUMN distributed_at TEXT",
    ):
        try:
            cur.execute(ddl)
        except sqlite3.OperationalError:
            pass

    # ---------------- retest_results : 학생의 재검사(이해도 확인 시험) 결과 ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS retest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            score INTEGER,                     -- 맞힌 문항 수
            total INTEGER,                      -- 전체 문항 수
            reliability INTEGER,                 -- 과제 신뢰도(%)
            student_answers TEXT,                 -- 학생이 제출한 답 (JSON: {question_id: answer})
            ai_feedback_basis TEXT,                -- AI 피드백 1) 문항 생성 근거
            ai_feedback_judgement TEXT,             -- AI 피드백 2) 이해도 판단 내용 및 근거
            ai_feedback_suggestion TEXT,             -- AI 피드백 3) 보충/심화 제안
            teacher_feedback TEXT,                    -- 교사가 남긴 피드백
            completed_at TEXT,
            result_viewed_at TEXT,                       -- 학생이 결과 확인 화면을 처음 연 시각
            FOREIGN KEY (assignment_id) REFERENCES assignments(id),
            FOREIGN KEY (student_id) REFERENCES users(id)
        )
    """)
    try:
        cur.execute("ALTER TABLE retest_results ADD COLUMN result_viewed_at TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE retest_results ADD COLUMN feedback_distributed_at TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()  # 지금까지의 변경사항(테이블 생성)을 실제 DB 파일에 반영
    conn.close()   # 커넥션 종료 (자원 반납)

    _seed_sample_data()  # 데모 확인이 쉽도록 샘플 데이터를 채워 넣습니다 (이미 있으면 건너뜀)


def _seed_sample_data():
    """
    데이터가 하나도 없을 때만 실행되는 '샘플 데이터 시딩' 함수입니다.
    화면 기획안(pptx)에 나온 예시 데이터를 그대로 넣어서,
    앱을 처음 켜자마자 바로 목록/테이블이 채워진 화면을 확인할 수 있게 해줍니다.
    """
    from auth import hash_password  # 순환 import 방지를 위해 함수 내부에서 import

    conn = get_connection()
    cur = conn.cursor()

    # 이미 유저가 있으면(=이미 시딩된 상태) 아무 것도 하지 않고 종료
    cur.execute("SELECT COUNT(*) as cnt FROM users")
    if cur.fetchone()["cnt"] > 0:
        conn.close()
        return

    now = datetime.now().isoformat(timespec="seconds")

    # --- 교사 계정 1개 생성 (기본 로그인 테스트용: teacher1 / teacher1234) ---
    cur.execute("""
        INSERT INTO users (role, username, password_hash, name, school, created_at)
        VALUES ('teacher', 'teacher1', ?, '김선생', 'A학교', ?)
    """, (hash_password("teacher1234"), now))
    teacher_id = cur.lastrowid

    # --- 학생 계정 여러 명 생성 (기획안 5번 슬라이드 학생목록 그대로) ---
    students = [
        ("student1", "student1234", "김민준", "A학교", "2학년", "3반", "15", "남"),
        ("student2", "student1234", "이서연", "B학교", "2학년", "1반", "07", "여"),
        ("student3", "student1234", "박도윤", "A학교", "2학년", "2반", "22", "남"),
        ("student4", "student1234", "최하은", "B학교", "2학년", "4반", "09", "여"),
        ("student5", "student1234", "정지호", "A학교", "2학년", "1반", "11", "남"),
        ("student6", "student1234", "한소율", "B학교", "2학년", "3반", "05", "여"),
    ]
    student_ids = {}
    for username, pw, name, school, grade, cls, no, gender in students:
        cur.execute("""
            INSERT INTO users (role, username, password_hash, name, school, grade, class_no, student_no, gender, created_at)
            VALUES ('student', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, hash_password(pw), name, school, grade, cls, no, gender, now))
        student_ids[name] = cur.lastrowid

    # --- 과제 1개 생성 (기획안 6~10번 슬라이드: 판 경계 지각변동 서술형 과제) ---
    core_concepts = json.dumps(["판의 경계", "지각변동"], ensure_ascii=False)
    cur.execute("""
        INSERT INTO assignments
            (unit_name, achievement_standard, title, question_text, core_concepts,
             deadline, retest_count, example_answer, status, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "고체지구 - 판구조론",
        "[12지과02-03] 판 경계에서의 지각변동을 설명할 수 있다",
        "판 경계 지각변동 서술형 과제",
        "판 경계에서 발생하는 지각변동 현상을 두 가지 이상 설명하세요.",
        core_concepts,
        "2026-09-30 23:59",
        10,
        "발산형 경계에서는 새로운 해양지각이 생성되며 두 판이 서로 멀어지는 것이 특징이다.",
        "배포중",
        teacher_id,
        now,
    ))
    assignment_id = cur.lastrowid

    # --- 평가요소/배점/채점기준 ---
    criteria = [
        ("발산형 경계 설명", 10, "발산형 경계의 정의와 예시를 정확히 서술함"),
        ("수렴형 경계 설명", 10, "수렴형 경계에서 나타나는 지형을 정확히 서술함"),
        ("변환형 경계 설명", 5, "변환형 경계의 특징과 사례를 서술함"),
    ]
    for name, score, text in criteria:
        cur.execute("""
            INSERT INTO eval_criteria (assignment_id, element_name, score, criteria_text)
            VALUES (?, ?, ?, ?)
        """, (assignment_id, name, score, text))

    # --- 대표 문항 은행 10문항 (기획안 13번 슬라이드) ---
    bank = [
        ("발산형 경계에서 나타나는 대표적인 지형은?", "해령"),
        ("대륙판과 해양판이 만나는 수렴형 경계에서 형성되는 지형은?", "해구"),
        ("변환단층의 대표적인 사례는?", "산안드레아스 단층"),
        ("지진의 규모를 나타내는 단위는?", "리히터 규모"),
        ("굳지 않은 상태로 지표에 분출된 마그마를 무엇이라 하는가?", "용암"),
        ("퇴적암이 형성되는 주요 과정 두 가지는?", "다짐 작용과 교결 작용"),
        ("변성암이 생성되는 주요 요인 두 가지는?", "열과 압력"),
        ("지구 내부 구조 중 액체 상태로 알려진 층은?", "외핵"),
        ("판을 움직이게 하는 주된 원동력은?", "맨틀 대류"),
        ("대륙과 대륙이 충돌할 때 형성되는 지형은?", "습곡산맥"),
    ]
    question_ids = []
    for q_text, ans in bank:
        cur.execute("""
            INSERT INTO retest_questions (assignment_id, question_text, question_type, choices, answer)
            VALUES (?, ?, 'short', NULL, ?)
        """, (assignment_id, q_text, ans))
        question_ids.append(cur.lastrowid)

    # --- 학생 2명에 대한 재검사 결과 샘플 (기획안 14번 슬라이드) ---
    results = [
        ("김민준", 9, 94, "생성하기"),
        ("이서연", 4, 58, "생성하기"),
    ]
    for name, score, reliability, _ in results:
        cur.execute("""
            INSERT INTO retest_results
                (assignment_id, student_id, score, total, reliability, completed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (assignment_id, student_ids[name], score, 10, reliability, now))

    conn.commit()
    conn.close()


# ============================================================
# ---------------------- users 관련 함수 ----------------------
# ============================================================

def get_user_by_username(username):
    """아이디로 사용자 1명 조회. 없으면 None 반환."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def username_exists(username):
    """회원가입 시 '중복확인' 버튼에서 사용할 아이디 중복 체크 함수."""
    return get_user_by_username(username) is not None


def create_user(role, username, password_hash, name, school=None, grade=None, class_no=None, student_no=None, gender=None):
    """회원가입: 새 사용자를 users 테이블에 추가합니다."""
    conn = get_connection()
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("""
        INSERT INTO users (role, username, password_hash, name, school, grade, class_no, student_no, gender, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (role, username, password_hash, name, school, grade, class_no, student_no, gender, now))
    conn.commit()
    conn.close()


def update_user_password(user_id, new_password_hash):
    """개인정보 수정 화면의 '비밀번호 변경'에서 사용."""
    conn = get_connection()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_password_hash, user_id))
    conn.commit()
    conn.close()


def list_students(school_filter=None, name_query=None):
    """관리자 - 학생관리 화면의 검색/필터 목록 조회."""
    conn = get_connection()
    sql = "SELECT * FROM users WHERE role = 'student'"
    params = []
    if school_filter and school_filter != "전체":
        sql += " AND school = ?"
        params.append(school_filter)
    if name_query:
        sql += " AND name LIKE ?"
        params.append(f"%{name_query}%")
    sql += " ORDER BY id"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_all_schools():
    """학교명 필터 셀렉트박스에 넣을 학교 목록(중복제거)."""
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT school FROM users WHERE role='student' AND school IS NOT NULL").fetchall()
    conn.close()
    return [r["school"] for r in rows]


def delete_student(user_id):
    """학생관리 화면의 '삭제' 버튼."""
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def list_teachers(school_filter=None, name_query=None):
    """관리자 - 회원관리 화면의 교사 현황 목록 조회."""
    conn = get_connection()
    sql = "SELECT * FROM users WHERE role = 'teacher'"
    params = []
    if school_filter and school_filter != "전체":
        sql += " AND school = ?"
        params.append(school_filter)
    if name_query:
        sql += " AND name LIKE ?"
        params.append(f"%{name_query}%")
    sql += " ORDER BY id"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_user(user_id):
    """회원관리 화면에서 학생/교사 공용 '삭제' 버튼."""
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def update_user_fields(user_id, **fields):
    """회원관리 화면의 '수정' 기능: 전달된 필드만 업데이트합니다."""
    if not fields:
        return
    conn = get_connection()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [user_id]
    conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


# ============================================================
# -------------------- assignments 관련 함수 --------------------
# ============================================================

def create_assignment(unit_name, achievement_standard, title, question_text,
                       core_concepts_list, deadline, retest_count, example_answer,
                       criteria_list, created_by):
    """
    과제 생성 (기획안 6~7번 슬라이드).
    criteria_list: [{"element_name":..., "score":..., "criteria_text":...}, ...]
    """
    conn = get_connection()
    now = datetime.now().isoformat(timespec="seconds")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO assignments
            (unit_name, achievement_standard, title, question_text, core_concepts,
             deadline, retest_count, example_answer, status, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, '배포전', ?, ?)
    """, (
        unit_name, achievement_standard, title, question_text,
        json.dumps(core_concepts_list, ensure_ascii=False),
        deadline, retest_count, example_answer, created_by, now
    ))
    assignment_id = cur.lastrowid

    for c in criteria_list:
        cur.execute("""
            INSERT INTO eval_criteria (assignment_id, element_name, score, criteria_text)
            VALUES (?, ?, ?, ?)
        """, (assignment_id, c["element_name"], c["score"], c["criteria_text"]))

    conn.commit()
    conn.close()
    return assignment_id


def list_assignments():
    """
    과제조회 목록 화면용.
    교사가 드래그로 정해둔 sort_order가 있으면 그 순서를, 없으면(=아직 순서를
    바꾼 적 없으면) 먼저 생성된 순서(id 오름차순)를 그대로 사용합니다.
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM assignments ORDER BY (sort_order IS NULL), sort_order ASC, id ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_published_assignments():
    """학생 화면(홈/제출/재검사/결과)에서 사용 — '배포중'인 과제만 보여줍니다."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM assignments WHERE status = '배포중' "
        "ORDER BY (sort_order IS NULL), sort_order ASC, id ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_assignment_status(assignment_id, status):
    """과제 배포 상태를 변경합니다. status: '배포중' | '배포전'"""
    conn = get_connection()
    conn.execute("UPDATE assignments SET status = ? WHERE id = ?", (status, assignment_id))
    conn.commit()
    conn.close()


def set_assignment_order(ordered_ids):
    """
    교사가 드래그로 정렬한 순서를 저장합니다.
    ordered_ids: 화면에 보여준 순서대로 정렬된 assignment id 리스트
    """
    conn = get_connection()
    for idx, assignment_id in enumerate(ordered_ids):
        conn.execute("UPDATE assignments SET sort_order = ? WHERE id = ?", (idx, assignment_id))
    conn.commit()
    conn.close()


def get_assignment(assignment_id):
    """과제 상세 1건 조회 (핵심개념은 JSON 문자열 -> 리스트로 변환해서 반환)."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    data["core_concepts"] = json.loads(data["core_concepts"]) if data["core_concepts"] else []
    return data


def get_eval_criteria(assignment_id):
    """특정 과제의 평가요소/배점/채점기준 목록."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM eval_criteria WHERE assignment_id = ?", (assignment_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_assignment(assignment_id):
    conn = get_connection()
    conn.execute("DELETE FROM assignments WHERE id = ?", (assignment_id,))
    conn.execute("DELETE FROM eval_criteria WHERE assignment_id = ?", (assignment_id,))
    conn.commit()
    conn.close()


def update_assignment_fields(assignment_id, **fields):
    """
    과제 상세보기 화면의 '수정' 기능에서 사용합니다.
    전달한 필드(컬럼)만 업데이트합니다. core_concepts_list를 넘기면 자동으로 JSON 문자열로 변환합니다.
    예: db.update_assignment_fields(1, unit_name="새 단원", question_text="새 문항")
    """
    if "core_concepts_list" in fields:
        fields["core_concepts"] = json.dumps(fields.pop("core_concepts_list"), ensure_ascii=False)
    if not fields:
        return
    conn = get_connection()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [assignment_id]
    conn.execute(f"UPDATE assignments SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


def replace_eval_criteria(assignment_id, criteria_list):
    """
    과제 상세보기 화면에서 평가요소/채점기준을 수정해 저장할 때 사용합니다.
    기존 평가요소를 모두 지우고 새 목록으로 다시 채워 넣습니다.
    """
    conn = get_connection()
    conn.execute("DELETE FROM eval_criteria WHERE assignment_id = ?", (assignment_id,))
    for c in criteria_list:
        conn.execute(
            "INSERT INTO eval_criteria (assignment_id, element_name, score, criteria_text) VALUES (?, ?, ?, ?)",
            (assignment_id, c["element_name"], c["score"], c["criteria_text"]),
        )
    conn.commit()
    conn.close()


# ============================================================
# -------------------- submissions 관련 함수 --------------------
# ============================================================

def create_submission(assignment_id, student_id, pdf_filename, pdf_path):
    """학생의 과제 PDF 제출 기록 저장."""
    conn = get_connection()
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("""
        INSERT INTO submissions (assignment_id, student_id, pdf_filename, pdf_path, submitted_at)
        VALUES (?, ?, ?, ?, ?)
    """, (assignment_id, student_id, pdf_filename, pdf_path, now))
    conn.commit()
    conn.close()


def get_submission(assignment_id, student_id):
    """특정 학생이 특정 과제를 제출했는지 조회 (제출 여부 판단에 사용, 항상 가장 최근 제출본)."""
    conn = get_connection()
    row = conn.execute("""
        SELECT * FROM submissions WHERE assignment_id = ? AND student_id = ?
        ORDER BY id DESC LIMIT 1
    """, (assignment_id, student_id)).fetchone()
    conn.close()
    return dict(row) if row else None


def count_submissions(assignment_id, student_id):
    """이 학생이 이 과제에 지금까지 제출한 횟수(버전 번호 계산용)."""
    conn = get_connection()
    cnt = conn.execute(
        "SELECT COUNT(*) as c FROM submissions WHERE assignment_id = ? AND student_id = ?",
        (assignment_id, student_id),
    ).fetchone()["c"]
    conn.close()
    return cnt


def get_submission_count(assignment_id):
    """진행중인 과제 목록에서 '제출 인원 n/전체' 표시용. 같은 학생이 여러 번(재출) 제출해도 1명으로 셉니다."""
    conn = get_connection()
    cnt = conn.execute(
        "SELECT COUNT(DISTINCT student_id) as c FROM submissions WHERE assignment_id = ?",
        (assignment_id,),
    ).fetchone()["c"]
    conn.close()
    return cnt


def count_extra_submissions(assignment_id, student_id):
    """이 학생이 이 과제에 대해 지금까지 제출한 '추가 과제' 횟수(버전 번호 계산용)."""
    conn = get_connection()
    cnt = conn.execute(
        "SELECT COUNT(*) as c FROM extra_submissions WHERE assignment_id = ? AND student_id = ?",
        (assignment_id, student_id),
    ).fetchone()["c"]
    conn.close()
    return cnt


def create_extra_submission(assignment_id, student_id, pdf_filename, pdf_path):
    """학생이 AI의 보충·심화 과제 제안을 보고 선택적으로 제출하는 '추가 과제' 파일을 저장합니다."""
    conn = get_connection()
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("""
        INSERT INTO extra_submissions (assignment_id, student_id, pdf_filename, pdf_path, submitted_at)
        VALUES (?, ?, ?, ?, ?)
    """, (assignment_id, student_id, pdf_filename, pdf_path, now))
    conn.commit()
    conn.close()


def get_extra_submission(assignment_id, student_id):
    """특정 학생이 이 과제에 대해 제출한 '추가 과제' 파일(있다면 가장 최근 것)을 조회합니다."""
    conn = get_connection()
    row = conn.execute("""
        SELECT * FROM extra_submissions WHERE assignment_id = ? AND student_id = ?
        ORDER BY id DESC LIMIT 1
    """, (assignment_id, student_id)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_submissions_for_assignment(assignment_id):
    """제출현황 화면: 특정 과제에 대한 학생별 제출 여부 표(학생 목록 + 제출여부/시각/파일경로 join)."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT u.*,
               s.id as submission_id,
               s.submitted_at as submitted_at,
               s.pdf_path as pdf_path,
               s.pdf_filename as pdf_filename
        FROM users u
        LEFT JOIN submissions s ON s.id = (
            -- 같은 과제에 여러 번 제출한 경우, 학생당 가장 최근 제출 1건만 사용합니다
            -- (재출은 이후 요청에 따라 허용되므로, 조인 결과가 중복 행으로 늘어나지 않도록 처리).
            SELECT s2.id FROM submissions s2
            WHERE s2.student_id = u.id AND s2.assignment_id = ?
            ORDER BY s2.id DESC LIMIT 1
        )
        WHERE u.role = 'student'
        ORDER BY u.id
    """, (assignment_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ============================================================
# ----------------- retest_questions / results -----------------
# ============================================================

def get_question_bank(assignment_id):
    """문항검토 상세 화면: 과제(단원)의 대표 문항 은행 10문항."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM retest_questions WHERE assignment_id = ?", (assignment_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_question_to_bank(assignment_id, question_text, answer, question_type="short", choices=None):
    conn = get_connection()
    conn.execute("""
        INSERT INTO retest_questions (assignment_id, question_text, question_type, choices, answer)
        VALUES (?, ?, ?, ?, ?)
    """, (assignment_id, question_text, question_type,
          json.dumps(choices, ensure_ascii=False) if choices else None, answer))
    conn.commit()
    conn.close()


def delete_question(question_id):
    conn = get_connection()
    conn.execute("DELETE FROM retest_questions WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()


# ============================================================
# ----------- 학생별 AI 생성 문항 (문항검토 화면 '문항보기'/'근거보기') -----------
# ============================================================

def get_student_generated_questions(assignment_id, student_id):
    """
    특정 학생에게 실제로 생성해준 개인 맞춤 문항 목록을 조회합니다.
    (retest_questions + retest_assignments를 조인해서, 문항 내용과 AI 근거를 함께 반환)
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT ra.id as mapping_id, ra.basis_page, ra.basis_quote, ra.ai_reason,
               rq.id as question_id, rq.question_text, rq.choices, rq.answer
        FROM retest_assignments ra
        JOIN retest_questions rq ON rq.id = ra.question_id
        WHERE ra.assignment_id = ? AND ra.student_id = ?
        ORDER BY ra.id
    """, (assignment_id, student_id)).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["choices"] = json.loads(d["choices"]) if d["choices"] else []
        results.append(d)
    return results


def clear_student_generated_questions(assignment_id, student_id):
    """재생성하기 전, 그 학생에게 이전에 배정했던 개인 맞춤 문항을 모두 지웁니다."""
    conn = get_connection()
    question_ids = [
        row["question_id"] for row in conn.execute(
            "SELECT question_id FROM retest_assignments WHERE assignment_id = ? AND student_id = ?",
            (assignment_id, student_id),
        ).fetchall()
    ]
    conn.execute("DELETE FROM retest_assignments WHERE assignment_id = ? AND student_id = ?",
                 (assignment_id, student_id))
    for qid in question_ids:
        conn.execute("DELETE FROM retest_questions WHERE id = ?", (qid,))
    conn.commit()
    conn.close()


def save_student_generated_questions(assignment_id, student_id, generated_list):
    """AI가 생성한 문항 목록을 저장합니다 (retest_questions에 문항, retest_assignments에 학생 배정+근거)."""
    conn = get_connection()
    for q in generated_list:
        cur = conn.execute("""
            INSERT INTO retest_questions (assignment_id, question_text, question_type, choices, answer)
            VALUES (?, ?, 'mc', ?, ?)
        """, (assignment_id, q["question_text"], json.dumps(q["choices"], ensure_ascii=False), q["answer"]))
        question_id = cur.lastrowid
        conn.execute("""
            INSERT INTO retest_assignments (assignment_id, student_id, question_id, ai_reason, basis_page, basis_quote)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (assignment_id, student_id, question_id,
              f"{q['basis_page']}페이지 답안 내용을 근거로 생성" if q.get("basis_page") else "학생 답안 내용을 근거로 생성",
              q.get("basis_page"), q.get("basis_quote")))
    conn.commit()
    conn.close()


def distribute_student_questions(assignment_id, student_id):
    """교사가 검토를 마친 문항 세트를 학생에게 '배포'합니다 (이때부터 학생이 응시할 수 있습니다)."""
    conn = get_connection()
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "UPDATE retest_assignments SET distributed_at = ? WHERE assignment_id = ? AND student_id = ?",
        (now, assignment_id, student_id),
    )
    conn.commit()
    conn.close()


def is_distributed(assignment_id, student_id):
    """이 학생의 맞춤 문항이 교사에 의해 배포되었는지 확인합니다."""
    conn = get_connection()
    row = conn.execute(
        "SELECT distributed_at FROM retest_assignments WHERE assignment_id = ? AND student_id = ? LIMIT 1",
        (assignment_id, student_id),
    ).fetchone()
    conn.close()
    return bool(row and row["distributed_at"])


def undistribute_student_questions(assignment_id, student_id):
    """배포를 취소합니다 (다시 누르기 전까지 학생은 응시할 수 없습니다)."""
    conn = get_connection()
    conn.execute(
        "UPDATE retest_assignments SET distributed_at = NULL WHERE assignment_id = ? AND student_id = ?",
        (assignment_id, student_id),
    )
    conn.commit()
    conn.close()


def distribute_feedback(result_id):
    """AI 피드백을 학생에게 배포합니다 (배포 전에는 학생 화면에 표시되지 않습니다)."""
    conn = get_connection()
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("UPDATE retest_results SET feedback_distributed_at = ? WHERE id = ?", (now, result_id))
    conn.commit()
    conn.close()


def undistribute_feedback(result_id):
    """AI 피드백 배포를 취소합니다."""
    conn = get_connection()
    conn.execute("UPDATE retest_results SET feedback_distributed_at = NULL WHERE id = ?", (result_id,))
    conn.commit()
    conn.close()


def get_student_retest_status(assignment_id, student_id):
    """
    결과 리포트 화면에서, 아직 이해도 검사를 완료하지 않은 학생의 현재 단계를 판별합니다.
    반환값: "과제미제출" | "문항미생성" | "문항미배포" | "문항미응시" | "완료"
    """
    result = get_retest_result(assignment_id, student_id)
    if result and result.get("score") is not None:
        return "완료"
    if not get_submission(assignment_id, student_id):
        return "과제미제출"
    if not get_student_generated_questions(assignment_id, student_id):
        return "문항미생성"
    if not is_distributed(assignment_id, student_id):
        return "문항미배포"
    return "문항미응시"




def update_student_question(question_id, question_text=None, choices_list=None, answer=None):
    """문항검토 화면에서 교사가 문항/보기/정답 중 하나를 직접 수정할 때 사용합니다."""
    fields = {}
    if question_text is not None:
        fields["question_text"] = question_text
    if choices_list is not None:
        fields["choices"] = json.dumps(choices_list, ensure_ascii=False)
    if answer is not None:
        fields["answer"] = answer
    if not fields:
        return
    conn = get_connection()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [question_id]
    conn.execute(f"UPDATE retest_questions SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


def delete_student_question(mapping_id):
    """특정 학생에게 배정된 문항 1개를 삭제합니다 (retest_assignments + 연결된 retest_questions)."""
    conn = get_connection()
    row = conn.execute("SELECT question_id FROM retest_assignments WHERE id = ?", (mapping_id,)).fetchone()
    conn.execute("DELETE FROM retest_assignments WHERE id = ?", (mapping_id,))
    if row:
        conn.execute("DELETE FROM retest_questions WHERE id = ?", (row["question_id"],))
    conn.commit()
    conn.close()


def get_retest_result(assignment_id, student_id):
    """학생 1명의 특정 과제에 대한 재검사 결과 조회 (항상 가장 최근 응시 회차)."""
    conn = get_connection()
    row = conn.execute("""
        SELECT * FROM retest_results WHERE assignment_id = ? AND student_id = ?
        ORDER BY id DESC LIMIT 1
    """, (assignment_id, student_id)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_retest_result_by_id(result_id):
    """특정 응시 회차(결과 id)를 직접 조회합니다."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM retest_results WHERE id = ?", (result_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_retest_attempts(assignment_id, student_id):
    """학생이 이 과제에 응시한 모든 회차를 오래된 순서(1회차부터)로 반환합니다."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM retest_results WHERE assignment_id = ? AND student_id = ?
        ORDER BY id ASC
    """, (assignment_id, student_id)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_retest_attempts(assignment_id, student_id):
    """이 과제에 대해 학생이 지금까지 응시한 횟수 (최대 응시 횟수 제한에 사용)."""
    conn = get_connection()
    cnt = conn.execute(
        "SELECT COUNT(*) as c FROM retest_results WHERE assignment_id = ? AND student_id = ?",
        (assignment_id, student_id),
    ).fetchone()["c"]
    conn.close()
    return cnt


def list_retest_results(assignment_id):
    """결과리포트/제출현황 화면: 과제에 대한 전체 학생 재검사 결과 목록 (학생별 가장 최근 응시 회차만)."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT u.id as student_id, u.name, u.school, u.grade, u.class_no, u.student_no,
               r.id as result_id, r.score, r.total, r.reliability,
               r.ai_feedback_basis, r.ai_feedback_judgement, r.ai_feedback_suggestion,
               r.teacher_feedback, r.completed_at, r.result_viewed_at, r.feedback_distributed_at
        FROM users u
        JOIN retest_results r ON r.id = (
            SELECT r2.id FROM retest_results r2
            WHERE r2.student_id = u.id AND r2.assignment_id = ?
            ORDER BY r2.id DESC LIMIT 1
        )
        WHERE u.role = 'student' AND r.score IS NOT NULL
        ORDER BY u.id
    """, (assignment_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_result_viewed(assignment_id, student_id):
    """학생이 '결과 확인' 화면에서 완료된 결과를 처음 열람하면 확인 시각을 기록합니다 (가장 최근 응시 회차, 최초 1회만)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id, result_viewed_at FROM retest_results WHERE assignment_id = ? AND student_id = ? ORDER BY id DESC LIMIT 1",
        (assignment_id, student_id),
    ).fetchone()
    if row and not row["result_viewed_at"]:
        now = datetime.now().isoformat(timespec="seconds")
        conn.execute("UPDATE retest_results SET result_viewed_at = ? WHERE id = ?", (now, row["id"]))
        conn.commit()
    conn.close()


def save_retest_result(assignment_id, student_id, score, total, reliability, student_answers):
    """학생이 재검사(이해도 확인 시험) 제출 시 결과를 저장."""
    conn = get_connection()
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("""
        INSERT INTO retest_results
            (assignment_id, student_id, score, total, reliability, student_answers, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (assignment_id, student_id, score, total, reliability, json.dumps(student_answers, ensure_ascii=False), now))
    conn.commit()
    conn.close()


def save_ai_feedback(result_id, basis, judgement, suggestion):
    """AI 피드백 생성하기 버튼 클릭 시 결과 저장 (mock_ai 결과를 DB에 반영)."""
    conn = get_connection()
    conn.execute("""
        UPDATE retest_results
        SET ai_feedback_basis = ?, ai_feedback_judgement = ?, ai_feedback_suggestion = ?
        WHERE id = ?
    """, (basis, judgement, suggestion, result_id))
    conn.commit()
    conn.close()


def save_teacher_feedback(result_id, feedback_text):
    """교사가 학생 결과에 직접 남기는 피드백 저장."""
    conn = get_connection()
    conn.execute("UPDATE retest_results SET teacher_feedback = ? WHERE id = ?", (feedback_text, result_id))
    conn.commit()
    conn.close()
