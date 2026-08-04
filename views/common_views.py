# views/common_views.py
# ------------------------------------------------------------
# 로그인 전(비회원) 상태에서 보여지는 공통 화면 3개를 담당합니다.
#   1) 메인 화면 (슬라이드 1)
#   2) 회원가입 화면 (슬라이드 2)
#   3) 로그인 화면 (슬라이드 3)
# ------------------------------------------------------------

import streamlit as st
import auth
import database as db
import ui
from config import ROLE_STUDENT, ROLE_TEACHER, ROLE_LABELS


def go_to(page_name, **kwargs):
    """
    화면 전환 헬퍼 함수.
    st.session_state["page"] 값을 바꾸고, 필요하면 추가 파라미터도 세션에 저장한 뒤
    st.rerun() 으로 앱을 즉시 다시 그리게 합니다.
    (Streamlit은 위에서 아래로 스크립트를 다시 실행하는 구조이므로,
     "페이지 이동"은 사실 session_state 값을 바꾸고 다시 실행시키는 것으로 구현합니다.)
    """
    st.session_state["page"] = page_name
    for k, v in kwargs.items():
        st.session_state[k] = v
    st.rerun()


def _guest_topnav(active=None):
    ui.render_topnav(role="guest", active=active, items=[], go_to=go_to)


def render_main():
    """슬라이드 1: 플랫폼 메인 화면"""
    st.markdown(
        """
        <div class="ec-hero">
            <div class="ec-hero-badge">AI 기반 서술형 과제 이해도 평가 플랫폼</div>
            <h1>🌎 EarthCheck</h1>
            <p>지구과학 서술형 과제, 학생이 진짜 이해했는지 AI로 다시 확인합니다</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, mid, _ = st.columns([2, 1, 2])
    with mid:
        if st.button("로그인", use_container_width=True, type="primary"):
            go_to("login")

        with st.container(key="main_signup_link"):
            if st.button("회원가입", use_container_width=True):
                go_to("signup")

    st.write("")
    st.write("")

    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown(
            """
            <div class="ec-feature">
                <div class="ec-feature-icon">📝</div>
                <h4>서술형 과제 출제</h4>
                <p>단원·성취기준 기반으로 평가요소와 채점기준을
                손쉽게 설계하고 배포할 수 있습니다.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with f2:
        st.markdown(
            """
            <div class="ec-feature">
                <div class="ec-feature-icon">🤖</div>
                <h4>AI 맞춤 재검사</h4>
                <p>제출한 답안을 근거로 AI가 학생 맞춤형
                이해도 확인 문항을 자동으로 선정합니다.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with f3:
        st.markdown(
            """
            <div class="ec-feature">
                <div class="ec-feature-icon">📊</div>
                <h4>이해도 리포트</h4>
                <p>재검사 결과와 AI 피드백을 한눈에 확인하고
                보충·심화 과제를 제안받습니다.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    st.divider()
    st.markdown(
        "<div style='text-align:center; color:#2563EB; font-size:0.85rem;'>"
        "(c) copyright. All rights reserved by Haemin</div>",
        unsafe_allow_html=True,
    )


def render_signup():
    """슬라이드 2: 회원가입 화면"""
    _guest_topnav(active="signup")

    st.markdown('<div class="ec-auth-wrap">', unsafe_allow_html=True)
    ui.page_header("회원가입", "EarthCheck과 함께 지구과학 학습 여정을 시작해보세요.", eyebrow="Welcome")

    with ui.card():
        # ---- "구분(학생/교사)" 선택은 폼 바깥에 둡니다. ----
        # st.form 안에 있으면 사용자가 선택을 바꿔도 "가입하기"를 누르기 전까지
        # 화면이 다시 그려지지 않아서, 학생 전용 입력칸(학년/반/번호)이 즉시
        # 나타나거나 사라지지 않는 문제가 있었습니다. 폼 바깥으로 빼면 선택 즉시
        # 화면이 갱신되어 항상 올바른 입력칸만 보여줍니다.
        role_label = st.selectbox("구분", options=list(ROLE_LABELS.values()), key="signup_role")
        role = ROLE_STUDENT if role_label == "학생" else ROLE_TEACHER

        with st.form("signup_form"):
            username = st.text_input("아이디", placeholder="student2026")
            st.caption("제출 시 자동으로 중복 확인됩니다")

            password = st.text_input("비밀번호", type="password", placeholder="••••••••")
            password_confirm = st.text_input("비밀번호 확인", type="password", placeholder="••••••••")

            school = st.text_input("학교명", placeholder="OO고등학교")

            # 학생일 때만 학년/반/번호 입력 (교사는 불필요)
            grade = class_no = student_no = None
            if role == ROLE_STUDENT:
                col1, col2, col3 = st.columns(3)
                with col1:
                    grade = st.text_input("학년", placeholder="2학년")
                with col2:
                    class_no = st.text_input("반", placeholder="3반")
                with col3:
                    student_no = st.text_input("번호", placeholder="15")

            name = st.text_input("이름", placeholder="홍길동")

            submitted = st.form_submit_button("가입하기", use_container_width=True, type="primary")

            if submitted:
                # ---- 입력값 정리(공백 제거) ----
                username = (username or "").strip()
                password = password or ""
                password_confirm = password_confirm or ""
                name = (name or "").strip()
                school = (school or "").strip()
                grade = grade.strip() if grade else None
                class_no = class_no.strip() if class_no else None
                student_no = student_no.strip() if student_no else None

                # ---- 입력값 검증 ----
                if not username or not password or not name:
                    st.error("아이디, 비밀번호, 이름은 필수 입력입니다.")
                elif len(password) < 4:
                    st.error("비밀번호는 4자 이상 입력해주세요.")
                elif password != password_confirm:
                    st.error("비밀번호가 일치하지 않습니다.")
                elif db.username_exists(username):
                    st.error("이미 사용 중인 아이디입니다. 다른 아이디를 입력해주세요.")
                else:
                    # 통과하면 실제 DB에 저장 (비밀번호는 해시로 변환해서 저장!)
                    try:
                        db.create_user(
                            role=role,
                            username=username,
                            password_hash=auth.hash_password(password),
                            name=name,
                            school=school or None,
                            grade=grade,
                            class_no=class_no,
                            student_no=student_no,
                        )
                    except Exception as e:
                        # DB 저장 중 예기치 못한 오류가 나더라도 화면이 죽지 않고
                        # 원인을 바로 확인할 수 있도록 안내합니다.
                        st.error(f"회원가입 처리 중 오류가 발생했습니다: {e}")
                    else:
                        st.success("회원가입이 완료되었습니다! 로그인 화면으로 이동합니다.")
                        go_to("login")

    if st.button("← 메인으로"):
        go_to("main")
    st.markdown("</div>", unsafe_allow_html=True)


def render_login():
    """슬라이드 3: 로그인 화면"""
    _guest_topnav(active="login")

    st.markdown('<div class="ec-auth-wrap">', unsafe_allow_html=True)
    ui.page_header("로그인", "아이디와 비밀번호를 입력해 EarthCheck에 접속하세요.", eyebrow="Welcome back")

    with ui.card():
        with st.form("login_form"):
            username = st.text_input("아이디", placeholder="student2026", key="login_username")
            password = st.text_input("비밀번호", type="password", placeholder="••••••••", key="login_password")
            submitted = st.form_submit_button("로그인", use_container_width=True, type="primary")

            if submitted:
                ok, message = auth.login(username, password)
                if ok:
                    st.success("로그인 성공! 잠시만 기다려주세요...")
                    # 역할에 따라 관리자 화면 / 학생 화면으로 각각 이동
                    user = auth.current_user()
                    if user["role"] == "teacher":
                        go_to("admin_students")
                    else:
                        go_to("student_home")
                else:
                    st.error(message)

        st.caption("데모 계정  ·  교사: teacher1 / teacher1234  ·  학생: student1 / student1234")

    if st.button("← 메인으로"):
        go_to("main")
    st.markdown("</div>", unsafe_allow_html=True)
