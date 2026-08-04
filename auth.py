# auth.py
# ------------------------------------------------------------
# 로그인 / 회원가입 / 세션(로그인 유지) 관련 로직을 모아둔 파일입니다.
# 사용자가 요청한 "간단한 자체 구현(ID/PW를 DB에 저장, 해시 처리)" 방식입니다.
# ------------------------------------------------------------

import hashlib  # 비밀번호를 안전하게 저장하기 위한 해시(암호화) 표준 라이브러리
import streamlit as st
import database as db


def hash_password(plain_password: str) -> str:
    """
    비밀번호를 SHA-256 방식으로 해시(암호화)합니다.
    ⚠️ 실무/운영 환경에서는 bcrypt, argon2 등 "느린 해시" 알고리즘 사용을 권장합니다.
       (SHA-256은 속도가 빨라 무작위 대입 공격에 상대적으로 취약할 수 있음)
       지금은 로컬 학습/뼈대용 프로젝트이므로 표준 라이브러리만으로 구현했습니다.
    """
    return hashlib.sha256(plain_password.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, password_hash: str) -> bool:
    """입력한 평문 비밀번호를 해시로 변환해서 DB에 저장된 해시와 비교합니다."""
    return hash_password(plain_password) == password_hash


def login(username: str, password: str):
    """
    로그인 시도.
    성공하면 st.session_state["user"] 에 사용자 정보(dict)를 저장하고 True 반환.
    실패하면 False 반환.
    """
    user = db.get_user_by_username(username)
    if user is None:
        return False, "존재하지 않는 아이디입니다."
    if not verify_password(password, user["password_hash"]):
        return False, "비밀번호가 일치하지 않습니다."

    # st.session_state : Streamlit에서 "새로고침(rerun)해도 유지되어야 하는 값"을 저장하는 공간입니다.
    # 로그인한 사용자 정보를 여기에 담아두면, 다른 화면(함수)에서도 계속 꺼내 쓸 수 있습니다.
    st.session_state["user"] = dict(user)
    return True, "로그인 성공"


def logout():
    """로그아웃: 세션에서 사용자 정보와 관련 상태를 모두 지웁니다."""
    for key in ["user", "page", "selected_assignment_id", "selected_student_id",
                "exam_started_at", "exam_answers", "exam_questions"]:
        if key in st.session_state:
            del st.session_state[key]


def current_user():
    """현재 로그인된 사용자 정보(dict)를 반환. 로그인 안 되어 있으면 None."""
    return st.session_state.get("user")


def is_logged_in() -> bool:
    return current_user() is not None


def is_teacher() -> bool:
    user = current_user()
    return user is not None and user["role"] == "teacher"


def is_student() -> bool:
    user = current_user()
    return user is not None and user["role"] == "student"
