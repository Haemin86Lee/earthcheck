import streamlit as st

import auth
import database as db
import ui
from views import common_views, admin_views, student_views

# ------------------------------------------------------------
# st.set_page_config(): 브라우저 탭 제목, 아이콘, 레이아웃(wide/centered)을 설정합니다.
# 반드시 다른 st.* 명령보다 "가장 먼저" 한 번만 호출되어야 합니다.
# ------------------------------------------------------------
st.set_page_config(
    page_title="EarthCheck - 지구과학 서술형 과제 평가 시스템",
    page_icon="🌎",
    layout="wide",  # 넓은 화면 레이아웃 (관리자 표 형태 화면이 많으므로 wide가 적합)
)

# ------------------------------------------------------------
# 최초 접속 시 session_state에 기본값을 세팅합니다.
# "page" 키가 없으면(=앱을 처음 켠 상태) "main"(메인 화면)으로 초기화합니다.
# ------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state["page"] = "main"

# 전역 디자인 시스템(폰트/색상/버튼/카드/상단 네비게이션 스타일 등)을 한 번만 주입합니다.
# 학생 화면("student_"로 시작)에서는 왼쪽 사이드바를 보여줍니다.
ui.inject_css(show_sidebar=st.session_state["page"].startswith(("student_", "admin_")))

# 앱이 처음 실행될 때 SQLite DB 테이블을 생성하고(이미 있으면 스킵), 샘플 데이터를 채워 넣습니다.
db.init_db()


def route():
    """
    현재 session_state["page"] 값을 읽어서, 알맞은 화면 렌더링 함수를 호출하는
    핵심 라우팅 함수입니다. 새로운 화면을 추가하고 싶다면:
      1) views/ 폴더에 렌더링 함수를 만들고
      2) 아래 page_map 딕셔너리에 "페이지이름": 함수 형태로 한 줄만 추가하면 됩니다.
    """
    page = st.session_state["page"]
    user = auth.current_user()

    # ---- 인증 가드(Guard): 로그인하지 않은 사용자가 관리자/학생 화면 주소로
    #      직접 접근하려 하면 로그인 화면으로 돌려보냅니다. ----
    protected_pages = {
        "admin_students", "admin_assignment_create", "admin_assignment_list",
        "admin_assignment_detail", "admin_submission_status", "admin_review",
        "admin_review_detail", "admin_review_reason", "admin_report", "admin_ai_feedback",
        "admin_preview_home", "admin_preview_submit", "admin_preview_retest",
        "admin_preview_result", "admin_preview_profile",
        "student_home", "student_submit", "student_retest_intro",
        "student_retest_exam", "student_result", "student_profile",
    }
    if page in protected_pages and user is None:
        st.warning("로그인이 필요합니다.")
        st.session_state["page"] = "login"
        page = "login"

    # ---- 역할 가드: 교사 전용/학생 전용 페이지를 서로 접근하지 못하도록 막습니다. ----
    if page.startswith("admin_") and user is not None and user["role"] != "teacher":
        st.error("관리자(교사) 전용 화면입니다.")
        st.session_state["page"] = "student_home"
        page = "student_home"
    if page.startswith("student_") and user is not None and user["role"] != "student":
        st.error("학생 전용 화면입니다.")
        st.session_state["page"] = "admin_students"
        page = "admin_students"

    # ---- 페이지 이름 -> 렌더링 함수 매핑표 ----
    page_map = {
        # 공통/인증 (슬라이드 1~3)
        "main": common_views.render_main,
        "signup": common_views.render_signup,
        "login": common_views.render_login,

        # 관리자(교사) 화면 (슬라이드 4~15)
        "admin_students": admin_views.render_student_management,
        "admin_assignment_create": admin_views.render_assignment_create,
        "admin_assignment_list": admin_views.render_assignment_list,
        "admin_assignment_detail": admin_views.render_assignment_detail,
        "admin_submission_status": admin_views.render_submission_status,
        "admin_review": admin_views.render_question_review,
        "admin_review_detail": admin_views.render_question_review_detail,
        "admin_review_reason": admin_views.render_review_reason_detail,
        "admin_report": admin_views.render_result_report,
        "admin_ai_feedback": admin_views.render_ai_feedback_detail,
        "admin_preview_home": admin_views.render_preview_home,
        "admin_preview_submit": admin_views.render_preview_submit,
        "admin_preview_retest": admin_views.render_preview_retest,
        "admin_preview_result": admin_views.render_preview_result,
        "admin_preview_profile": admin_views.render_preview_profile,

        # 학생 화면 (슬라이드 16~22)
        "student_home": student_views.render_student_home,
        "student_submit": student_views.render_assignment_submit,
        "student_retest_intro": student_views.render_retest_intro,
        "student_retest_exam": student_views.render_retest_exam,
        "student_result": student_views.render_result_view,
        "student_profile": student_views.render_profile_edit,
    }

    render_func = page_map.get(page, common_views.render_main)
    render_func()


route()
