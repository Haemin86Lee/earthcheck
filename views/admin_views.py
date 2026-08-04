# views/admin_views.py
# ------------------------------------------------------------
# 관리자(교사)용 화면 전체 (기획안 슬라이드 4~15)
#   - 학생관리 / 과제관리(생성·조회·제출현황) / 문항검토 / 결과리포트
# ------------------------------------------------------------

import os
import json
import uuid
import streamlit as st
import database as db
import auth
import mock_ai
import ai_engine
import ui
import config
from views.common_views import go_to

# ------------------------------------------------------------
# 2022 개정 교육과정 지구과학 단원/성취기준/핵심개념(내용요소) 고정 데이터
# 과제 생성 화면에서 교사가 직접 타이핑하지 않고 목록에서 선택하도록 사용합니다.
# ------------------------------------------------------------
CURRICULUM_UNITS = [
    "대기와 해양의 상호작용",
    "지구의 역사와 한반도의 암석",
    "태양계 천체와 별과 우주의 진화",
]

UNIT_ACHIEVEMENT_STANDARDS = {
    "대기와 해양의 상호작용": [
        "[12지과01-01] 해수의 물리적, 화학적 성질을 이해하고, 실측 자료를 활용하여 해수의 온도, 염분, 밀도, 용존 산소량 등의 분포를 분석·해석할 수 있다.",
        "[12지과01-02] 심층 순환의 발생 원리와 분포를 알고, 표층 순환 및 기후 변화의 관련성을 추론할 수 있다.",
        "[12지과01-03] 중위도 저기압과 고기압이 통과할 때 날씨의 변화를 일기도, 위성 영상, 레이더 영상을 종합하여 예측할 수 있다.",
        "[12지과01-04] 태풍의 발생, 이동, 소멸 과정 및 태풍 영향권에서 날씨를 예측하고, 뇌우, 집중호우, 폭설, 강풍, 황사 등 주요 악기상의 생성 메커니즘과 대처 방안을 제시할 수 있다.",
        "[12지과01-05] 대기와 해양의 상호작용의 사례로서 해수의 용승과 침강, 엘니뇨-남방진동(ENSO)의 현상의 진행 과정 및 관련 현상을 설명할 수 있다.",
        "[12지과01-06] 기후 변화의 원인을 자연적 요인과 인위적 요인으로 구분하여 설명하고, 인간 활동에 의한 기후 변화 문제를 과학적으로 해결하는 방법을 탐색할 수 있다.",
    ],
    "지구의 역사와 한반도의 암석": [
        "[12지과02-01] 지층 형성의 선후 관계를 결정짓는 법칙들을 활용하여 상대연령을 비교하고, 방사성 동위원소를 이용한 광물의 절대연령 자료로 암석의 절대연령을 구할 수 있다.",
        "[12지과02-02] 지질 시대를 기(紀) 수준에서 구분하고, 지층과 화석을 통해 지질 시대의 생물과 환경 변화를 해석할 수 있다.",
        "[12지과02-03] 변동대에서 마그마가 생성되고, 그 조성에 따라 다양한 화성암이 생성됨을 설명할 수 있다.",
        "[12지과02-04] 변성 작용의 종류와 지각 변동에 따른 구조를 변동대와 관련지어 설명하고, 지구시스템에서 암석이 순환함을 추론할 수 있다.",
        "[12지과02-05] 우리나라의 대표적인 지질공원의 지질학적 형성 과정을 추론하고, 지역사회와 함께하는 지질공원의 지속가능한 발전방안을 제안할 수 있다.",
    ],
    "태양계 천체와 별과 우주의 진화": [
        "[12지과03-01] 태양-지구-달 시스템에서의 식 현상을 이해하고 모형을 이용하여 태양계 행성의 겉보기 운동을 설명할 수 있다.",
        "[12지과03-02] 별의 분광형 결정 및 별의 분류 과정을 이해하고, 흑체복사 법칙을 이용하여 별의 물리량을 추론할 수 있다.",
        "[12지과03-03] 다양한 질량을 가진 별의 진화 과정을 H-R도에 나타내고 해석할 수 있다.",
        "[12지과03-04] 허블의 은하 분류 체계에 따른 은하의 특징을 비교하고 외부은하의 자료를 이용하여 특이 은하의 관측적 특징을 추론할 수 있다.",
        "[12지과03-05] 허블-르메트르 법칙으로 우주의 팽창을 이해하고 우주의 진화에 대한 다양한 설명 체계의 의의를 현대 우주론의 관점에서 비교할 수 있다.",
    ],
}

CORE_CONCEPTS_ALL = [
    "해수의 성질", "표층 순환", "심층 순환", "수온과 염분",
    "일기 예보", "이동성 고기압과 저기압", "악기상",
    "용승과 침강", "남방진동", "지구 온난화", "기후 변화 요인",
    "퇴적 구조와 퇴적암", "화성암", "변성 작용과 변성암", "변동대",
    "지사 해석 방법", "상대연령과 절대연령",
    "지질 시대의 환경과 생물", "국가지질공원",
    "태양계 모형", "행성의 겉보기 운동", "일식과 월식",
    "별의 물리량", "별의 진화와 H-R도", "은하의 구성과 분류",
    "우주의 팽창",
]


ADMIN_NAV_ITEMS = [
    ("students", "👥 회원 관리", "admin_students"),
    ("assignments", "📋 과제 관리", "admin_assignment_list"),
    ("review", "🔍 문항 검토", "admin_review"),
    ("report", "📊 결과 리포트", "admin_report"),
]

# 교사 화면의 왼쪽 사이드바는 학생 메뉴와 동일한 라벨을 사용하되,
# 실제 학생 개인 데이터가 반영되지 않는 '미리보기' 전용 화면으로 연결합니다.
TEACHER_SIDEBAR_ITEMS = [
    ("home", "📋 과제 확인", "admin_preview_home"),
    ("submit", "📤 과제 제출", "admin_preview_submit"),
    ("retest", "📝 이해도 확인", "admin_preview_retest"),
    ("result", "📊 결과 확인", "admin_preview_result"),
    ("profile", "⚙️ 개인정보", "admin_preview_profile"),
]


def render_admin_nav(active_page):
    """
    관리자(교사) 공통 내비게이션.
    왼쪽 사이드바에는 학생 화면과 동일한 메뉴(과제 확인/과제 제출/이해도 확인/결과 확인/개인정보)를,
    상단 바에는 교사 전용 메뉴(회원관리/과제관리/문항검토/결과리포트)를 함께 보여줘서
    두 메뉴를 동시에 확인할 수 있도록 합니다.
    active_page 인자로 현재 페이지를 넘겨받아, 상단 바에서 해당 메뉴를 강조 표시합니다.
    """
    user = auth.current_user()
    current_page = st.session_state.get("page", "")
    sidebar_active = next((key for key, _, page_name in TEACHER_SIDEBAR_ITEMS if page_name == current_page), None)

    ui.render_role_sidebar(
        role="teacher",
        active=sidebar_active,
        user=user,
        items=TEACHER_SIDEBAR_ITEMS,
        go_to=go_to,
        on_logout=auth.logout,
    )
    ui.render_admin_topbar(active_page, ADMIN_NAV_ITEMS, go_to)


# ============================================================
# 교사 사이드바 전용: 학생 화면 미리보기 (개별 학생 데이터가 반영되지 않는 기본 틀)
# ============================================================
def render_preview_home():
    render_admin_nav(None)
    ui.page_header("과제 확인", "학생 화면의 기본 구성을 보여주는 미리보기입니다.", eyebrow="Preview")

    assignments = db.list_published_assignments()
    if not assignments:
        ui.empty_state("진행 중인 과제가 없습니다.", icon="📭")
        return

    total_students = len(db.list_students())
    col_widths = [0.5, 3, 1, 1.5, 1.5]

    with st.container(key="student_home_table"):
        with st.container(key="student_home_header_row"):
            header = st.columns(col_widths)
            for h, t in zip(header, ["순", "과제명", "배점", "제출 기한", "제출 인원"]):
                h.markdown(f"**{t}**")

        for i, a in enumerate(assignments, start=1):
            with st.container(key=f"trow_preview_home_{a['id']}"):
                c = st.columns(col_widths)
                c[0].markdown(f"<span class='ec-cell-text-center'>{i}</span>", unsafe_allow_html=True)
                c[1].markdown(f"<span class='ec-cell-text-center'>{a['title']}</span>", unsafe_allow_html=True)
                total_score = sum(x["score"] for x in db.get_eval_criteria(a["id"])) or 100
                c[2].markdown(f"<span class='ec-cell-text-center'>{total_score}점</span>", unsafe_allow_html=True)
                c[3].markdown(f"<span class='ec-cell-text-center'>{a['deadline'] or '-'}</span>", unsafe_allow_html=True)
                submitted_count = db.get_submission_count(a["id"])
                c[4].markdown(
                    f"<div style='text-align:center;'>{ui.badge(f'{submitted_count}/{total_students}명', 'info')}</div>",
                    unsafe_allow_html=True,
                )


def render_preview_submit():
    render_admin_nav(None)
    ui.page_header("과제 제출", "학생 화면의 기본 구성을 보여주는 미리보기입니다. 실제 제출은 학생 계정에서 이루어집니다.", eyebrow="Preview")

    assignments = db.list_published_assignments()
    if not assignments:
        ui.empty_state("제출할 수 있는 과제가 없습니다.", icon="📤")
        return

    with st.container(key="assignment_select_box"):
        st.markdown("<div class='ec-select-label'>과제 선택</div>", unsafe_allow_html=True)
        options = {a["title"]: a["id"] for a in assignments}
        selected_title = st.selectbox(
            "과제 선택", list(options.keys()), label_visibility="collapsed", key="preview_submit_select",
        )
        assignment = db.get_assignment(options[selected_title])

    with ui.card():
        st.write(f"**단원명**  \n{assignment['unit_name']}")
        standards = [s for s in (assignment["achievement_standard"] or "").split("\n") if s]
        standards_html = "<br>".join(standards) if standards else "-"
        st.markdown(f"**성취기준**<br>{standards_html}", unsafe_allow_html=True)
        st.write(f"**평가문항**  \n{assignment['question_text']}")
        total_score = sum(x["score"] for x in db.get_eval_criteria(assignment["id"])) or 100
        st.write(f"**배점**  \n{total_score}점")
        st.write(f"**제출 기한**  \n{assignment['deadline'] or '-'}")

    st.info("📌 실제 파일 업로드·제출 기능은 학생 계정으로 로그인했을 때만 동작합니다.")


def render_preview_retest():
    render_admin_nav(None)
    ui.page_header("이해도 확인", "학생 화면의 기본 구성을 보여주는 미리보기입니다.", eyebrow="Preview")

    with ui.card():
        st.markdown(
            f"""
            - 이 시험은 **학생이 제출한 과제 PDF 내용을 바탕으로 AI가 만든** 이해도 확인 문항입니다.
            - 5지선다 객관식으로 총 **N문항**이 출제됩니다 (문항 수는 과제마다 다를 수 있어요).
            - 제한 시간은 **5분**이며, 시간이 종료되면 자동으로 제출됩니다.
            - 시험을 시작하면 다시 처음으로 돌아갈 수 없습니다.
            - 응시 기회는 과제당 총 **{config.RETEST_MAX_ATTEMPTS}회**로 제한됩니다.
            """
        )
        st.button(
            "시험 시작하기", type="primary", use_container_width=True, disabled=True,
            help="실제 응시는 학생 계정으로 로그인했을 때만 가능합니다.",
        )


def render_preview_result():
    render_admin_nav(None)
    ui.page_header("결과 확인", "학생 화면의 기본 구성을 보여주는 미리보기입니다.", eyebrow="Preview")
    ui.empty_state("학생 계정으로 로그인하면 이 자리에 응시 결과와 AI 피드백이 표시됩니다.", icon="📊")


def render_preview_profile():
    """사이드바의 '개인정보' 위치에서, 교사 본인의 개인정보를 확인/수정합니다."""
    render_admin_nav(None)
    user = auth.current_user()
    ui.page_header("개인정보 수정", eyebrow="Profile")

    with ui.card():
        st.selectbox("구분", ["교사"], disabled=True)
        st.text_input("아이디", value=user["username"], disabled=True)

        col_pw1, col_pw2 = st.columns(2)
        with col_pw1:
            new_password = st.text_input("새 비밀번호", type="password", placeholder="••••••••")
        with col_pw2:
            new_password_confirm = st.text_input("새 비밀번호 확인", type="password", placeholder="••••••••")

        if st.button("수정", use_container_width=True):
            if not new_password:
                st.warning("새 비밀번호를 입력해주세요.")
            elif new_password != new_password_confirm:
                st.error("두 비밀번호가 일치하지 않습니다. 다시 확인해주세요.")
            else:
                db.update_user_password(user["id"], auth.hash_password(new_password))
                st.success("비밀번호가 변경되었습니다.")

        st.text_input("학교명", value=user["school"] or "", disabled=True)
        st.text_input("이름", value=user["name"], disabled=True)

        st.caption("비밀번호를 제외한 다른 정보 수정은 관리자에게 문의해 주세요.")


# ============================================================
# 슬라이드 5: 학생 관리
# ============================================================
def _render_member_edit_panel(member, role):
    """회원관리 화면의 '수정' 클릭 시 나타나는, 모든 정보를 고칠 수 있는 패널."""
    with st.container(key=f"member_edit_panel_{role}_{member['id']}"):
        new_name = st.text_input("이름", value=member["name"], key=f"edit_name_{role}_{member['id']}")
        new_school = st.text_input("학교명", value=member["school"] or "", key=f"edit_school_{role}_{member['id']}")
        if role == "student":
            c1, c2, c3 = st.columns(3)
            new_grade = c1.text_input("학년", value=member["grade"] or "", key=f"edit_grade_{member['id']}")
            new_class_no = c2.text_input("반", value=member["class_no"] or "", key=f"edit_class_{member['id']}")
            new_student_no = c3.text_input("번호", value=member["student_no"] or "", key=f"edit_no_{member['id']}")
        if st.button("저장", key=f"edit_save_{role}_{member['id']}", type="primary", use_container_width=True):
            fields = {"name": new_name, "school": new_school or None}
            if role == "student":
                fields.update({"grade": new_grade or None, "class_no": new_class_no or None, "student_no": new_student_no or None})
            db.update_user_fields(member["id"], **fields)
            st.session_state[f"member_edit_open_{role}_{member['id']}"] = False
            st.success("저장되었습니다.")
            st.rerun()


def render_student_management():
    render_admin_nav("students")
    ui.page_header("회원 관리", "학교/이름으로 학생·교사 계정을 검색하고 관리합니다.", eyebrow="Admin")

    with ui.card():
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            schools = ["전체"] + db.list_all_schools()
            school_filter = st.selectbox("학교명", schools)
        with col2:
            name_query = st.text_input("이름 검색", placeholder="이름을 입력하세요")
        with col3:
            st.write("")
            st.write("")
            st.button("검색", use_container_width=True)

    students = db.list_students(
        school_filter=school_filter if school_filter != "전체" else None,
        name_query=name_query if name_query else None,
    )

    st.write(f"총 **{len(students)}명**의 학생이 있습니다.")

    if students:
        header_widths = [0.5, 1.4, 1.1, 0.9, 0.9, 0.9, 1, 1.4, 0.8, 0.8]
        with st.container(key="students_table"):
            with st.container(key="students_header_row"):
                header = st.columns(header_widths)
                for h, t in zip(header, ["순", "이름", "학교명", "학년", "반", "번호", "구분", "가입일", "", ""]):
                    h.markdown(f"**{t}**")

            for i, s in enumerate(students, start=1):
                with st.container(key=f"trow_students_{s['id']}"):
                    c = st.columns(header_widths)
                    c[0].markdown(f"<span class='ec-cell-text-center'>{i}</span>", unsafe_allow_html=True)
                    c[1].markdown(f"<span class='ec-cell-text-center'>{s['name']}</span>", unsafe_allow_html=True)
                    c[2].markdown(f"<span class='ec-cell-text-center'>{s['school'] or '-'}</span>", unsafe_allow_html=True)
                    c[3].markdown(f"<span class='ec-cell-text-center'>{s['grade'] or '-'}</span>", unsafe_allow_html=True)
                    c[4].markdown(f"<span class='ec-cell-text-center'>{s['class_no'] or '-'}</span>", unsafe_allow_html=True)
                    c[5].markdown(f"<span class='ec-cell-text-center'>{s['student_no'] or '-'}</span>", unsafe_allow_html=True)
                    c[6].markdown(f"<div style='text-align:center;'>{ui.badge('학생', 'info')}</div>", unsafe_allow_html=True)
                    c[7].markdown(f"<span class='ec-cell-text-center'>{s['created_at'][:16]}</span>", unsafe_allow_html=True)
                    edit_key = f"member_edit_open_{'student'}_{s['id']}"
                    if c[8].button("수정", key=f"edit_{s['id']}", use_container_width=True):
                        st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                        st.rerun()
                    if c[9].button("삭제", key=f"del_{s['id']}", use_container_width=True):
                        db.delete_student(s["id"])
                        st.rerun()
                    if st.session_state.get(edit_key):
                        _render_member_edit_panel(s, "student")
    else:
        ui.empty_state("검색 조건에 해당하는 학생이 없습니다.", icon="🧑‍🎓")

    st.write("")
    teachers = db.list_teachers(
        school_filter=school_filter if school_filter != "전체" else None,
        name_query=name_query if name_query else None,
    )
    st.write(f"총 **{len(teachers)}명**의 교사가 있습니다.")

    if teachers:
        t_widths = [0.5, 1.8, 1.8, 1, 1.6, 0.8, 0.8]
        with st.container(key="teachers_table"):
            with st.container(key="teachers_header_row"):
                header = st.columns(t_widths)
                for h, t in zip(header, ["순", "이름", "학교명", "구분", "가입일", "", ""]):
                    h.markdown(f"**{t}**")

            for i, t_row in enumerate(teachers, start=1):
                with st.container(key=f"trow_teachers_{t_row['id']}"):
                    c = st.columns(t_widths)
                    c[0].markdown(f"<span class='ec-cell-text-center'>{i}</span>", unsafe_allow_html=True)
                    c[1].markdown(f"<span class='ec-cell-text-center'>{t_row['name']}</span>", unsafe_allow_html=True)
                    c[2].markdown(f"<span class='ec-cell-text-center'>{t_row['school'] or '-'}</span>", unsafe_allow_html=True)
                    c[3].markdown(f"<div style='text-align:center;'>{ui.badge('교사', 'success')}</div>", unsafe_allow_html=True)
                    c[4].markdown(f"<span class='ec-cell-text-center'>{t_row['created_at'][:16]}</span>", unsafe_allow_html=True)
                    edit_key = f"member_edit_open_teacher_{t_row['id']}"
                    if c[5].button("수정", key=f"edit_t_{t_row['id']}", use_container_width=True):
                        st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                        st.rerun()
                    if c[6].button("삭제", key=f"del_t_{t_row['id']}", use_container_width=True):
                        db.delete_user(t_row["id"])
                        st.rerun()
                    if st.session_state.get(edit_key):
                        _render_member_edit_panel(t_row, "teacher")
    else:
        ui.empty_state("검색 조건에 해당하는 교사가 없습니다.", icon="🧑‍🏫")


def _flatten_to_groups(criteria_rows):
    """DB에서 읽은 평가요소 flat 목록을 평가요소별로 묶은 그룹 구조로 변환합니다."""
    groups = []
    by_name = {}
    for c in criteria_rows:
        name = c["element_name"]
        if name not in by_name:
            g = {"gid": uuid.uuid4().hex, "element_name": name, "items": []}
            by_name[name] = g
            groups.append(g)
        by_name[name]["items"].append(
            {"iid": uuid.uuid4().hex, "score": c["score"], "criteria_text": c["criteria_text"]}
        )
    if not groups:
        groups = [{"gid": uuid.uuid4().hex, "element_name": "",
                    "items": [{"iid": uuid.uuid4().hex, "score": 10, "criteria_text": ""}]}]
    return groups


def _render_criteria_groups_editor(groups_key):
    """
    st.session_state[groups_key]에 저장된 평가요소 그룹 목록(헤더행~배점합계행)을 렌더링합니다.
    구조: [{"gid":..., "element_name":..., "items":[{"iid":...,"score":...,"criteria_text":...}]}]
    과제 생성 화면과 과제 상세보기의 수정 화면에서 공통으로 사용합니다.
    반환값: 배점 총합(int)
    """
    col_widths = [2, 1, 3, 0.5]
    groups = st.session_state[groups_key]
    total_score = 0
    group_to_remove = None   # 삭제할 그룹의 gid
    item_to_remove = None    # 삭제할 (gid, iid)

    header_cols = st.columns(col_widths)
    for h, t in zip(header_cols, ["평가요소", "배점", "채점기준", ""]):
        h.markdown(f"**{t}**")

    for group in groups:
        gid = group["gid"]
        # 평가요소 하나 = 카드 한 장. 그 안에서 평가요소칸(왼쪽)이
        # 배점/채점기준 행 전체 높이만큼 늘어나 셀 병합처럼 보이도록 합니다.
        with st.container(key=f"group_card_{groups_key}_{gid}"):
            with st.container(key=f"group_row_{groups_key}_{gid}"):
                name_col, items_col = st.columns([2, 4.5])
                with name_col:
                    with st.container(key=f"elem_cell_{groups_key}_{gid}"):
                        group["element_name"] = st.text_input(
                            "평가요소", value=group["element_name"], key=f"elem_{groups_key}_{gid}",
                            label_visibility="collapsed", placeholder="평가요소",
                        )
                with items_col:
                    for item in group["items"]:
                        iid = item["iid"]
                        c2, c3, c4 = st.columns([1, 3, 0.5])
                        item["score"] = c2.number_input(
                            "배점", value=item["score"], key=f"score_{groups_key}_{iid}",
                            min_value=0, max_value=100, label_visibility="collapsed",
                        )
                        item["criteria_text"] = c3.text_input(
                            "채점기준", value=item["criteria_text"], key=f"crit_{groups_key}_{iid}",
                            label_visibility="collapsed", placeholder="채점기준",
                        )
                        if c4.button("✕", key=f"remove_item_{groups_key}_{iid}"):
                            item_to_remove = (gid, iid)
                        total_score += item["score"]

                    # [이 평가요소 삭제]가 [+ 배점·채점기준 추가]보다 앞에 오도록 배치
                    gc1, gc2 = st.columns([1, 1])
                    with gc1:
                        if len(groups) > 1 and st.button("이 평가요소 삭제", key=f"remove_group_{groups_key}_{gid}"):
                            group_to_remove = gid
                    with gc2:
                        if st.button("+ 배점·채점기준 추가", key=f"add_item_{groups_key}_{gid}"):
                            group["items"].append({"iid": uuid.uuid4().hex, "score": 10, "criteria_text": ""})
                            st.rerun()

    if item_to_remove is not None:
        target_gid, target_iid = item_to_remove
        for g in groups:
            if g["gid"] == target_gid:
                g["items"] = [it for it in g["items"] if it["iid"] != target_iid]
                break
        # 마지막 배점/채점기준까지 삭제되어 빈 평가요소가 되면 그룹째 제거합니다.
        st.session_state[groups_key] = [g for g in groups if g["items"]]
        st.rerun()
    if group_to_remove is not None:
        st.session_state[groups_key] = [g for g in groups if g["gid"] != group_to_remove]
        st.rerun()

    if st.button("+ 평가요소 추가", key=f"add_group_{groups_key}"):
        groups.append({
            "gid": uuid.uuid4().hex, "element_name": "",
            "items": [{"iid": uuid.uuid4().hex, "score": 10, "criteria_text": ""}],
        })
        st.rerun()

    # 마지막 행: 배점 합계
    t1, t2, t3, t4 = st.columns(col_widths)
    t1.markdown("**배점 합계**")
    t2.markdown(f"**{total_score}점**")
    return total_score


# ============================================================
# 슬라이드 6~7: 과제 생성 (2단계 폼)
# ============================================================
def render_assignment_create():
    render_admin_nav("assignments")
    _assignment_sub_nav("create")

    ui.page_header("과제 생성", "단원·성취기준 기반으로 서술형 과제와 평가 기준을 설계합니다.", eyebrow="Assignment")

    # session_state로 평가요소 그룹들을 동적으로 추가/삭제할 수 있게 관리합니다.
    # 구조: [{"element_name": "...", "items": [{"score":10, "criteria_text":"..."}, ...]}, ...]
    # 평가요소 하나에 배점·채점기준 쌍(items)이 여러 개 들어갈 수 있습니다.
    if "new_criteria_groups" not in st.session_state:
        st.session_state["new_criteria_groups"] = [
            {"gid": uuid.uuid4().hex, "element_name": "",
             "items": [{"iid": uuid.uuid4().hex, "score": 10, "criteria_text": ""}]}
        ]
    if "new_assignment_unit" not in st.session_state:
        st.session_state["new_assignment_unit"] = None
    if "new_selected_standards" not in st.session_state:
        st.session_state["new_selected_standards"] = [""]
    if "assignment_form_reset_counter" not in st.session_state:
        st.session_state["assignment_form_reset_counter"] = 0

    def field_label(text):
        st.markdown(f"<div class='ec-field-label'>{text}</div>", unsafe_allow_html=True)

    with ui.card():
        st.markdown("#### 1. 과제")

        # ---- 단원명: 카드 3개 중 클릭해서 선택 (선택된 카드는 색이 바뀝니다) ----
        field_label("단원명 (*)")
        with st.container(key="unit_cards"):
            u_cols = st.columns(3)
            for i, u in enumerate(CURRICULUM_UNITS):
                with u_cols[i]:
                    is_selected = st.session_state["new_assignment_unit"] == u
                    if st.button(u, key=f"unit_card_{i}", use_container_width=True,
                                 type="primary" if is_selected else "secondary"):
                        st.session_state["new_assignment_unit"] = u
                        # 단원이 바뀌면 이전에 골라둔 성취기준은 다른 단원 것일 수 있으므로 초기화합니다.
                        st.session_state["new_selected_standards"] = [""]
                        st.rerun()
        unit_name = st.session_state["new_assignment_unit"]

        # ---- 성취기준: '+ 추가'를 누르면 콤보박스가 하나씩 늘어나고, 각 콤보박스에서
        #      선택한 단원에 해당하는 성취기준 중 하나씩 골라 여러 개를 중복 선택할 수 있습니다. ----
        field_label("성취기준 (*)")
        if not unit_name:
            st.caption("먼저 위에서 단원명을 선택해주세요.")
        else:
            available_standards = UNIT_ACHIEVEMENT_STANDARDS[unit_name]
            for idx, val in enumerate(st.session_state["new_selected_standards"]):
                col_sel, col_rm = st.columns([6, 0.5])
                with col_sel:
                    options = [""] + available_standards
                    default_index = options.index(val) if val in options else 0
                    chosen = st.selectbox(
                        f"성취기준 선택 {idx + 1}", options, index=default_index,
                        key=f"std_select_{unit_name}_{st.session_state['assignment_form_reset_counter']}_{idx}",
                        label_visibility="collapsed",
                    )
                    st.session_state["new_selected_standards"][idx] = chosen
                with col_rm:
                    if len(st.session_state["new_selected_standards"]) > 1 and st.button("✕", key=f"std_remove_{idx}"):
                        st.session_state["new_selected_standards"].pop(idx)
                        st.rerun()
            if st.button("+ 추가", key="add_standard_slot"):
                st.session_state["new_selected_standards"].append("")
                st.rerun()

        selected_standards = [s for s in st.session_state["new_selected_standards"] if s]
        achievement_standard = "\n".join(selected_standards)

        field_label("과제명 (*)")
        title = st.text_input("과제명", label_visibility="collapsed", placeholder="예: 판 경계 지각변동 서술형 과제")

        field_label("평가문항 (*)")
        question_text = st.text_area(
            "평가문항", label_visibility="collapsed",
            placeholder="예: 판 경계에서 발생하는 지각변동 현상을 두 가지 이상 설명하세요.",
        )

        # ---- 핵심 개념(내용 요소): 목록을 모두 나열해두고 여러 개를 중복 선택합니다 ----
        field_label("핵심 개념(내용 요소)")
        selected_concepts = st.multiselect(
            "핵심 개념(내용 요소)", CORE_CONCEPTS_ALL,
            key=f"new_core_concepts_multiselect_{st.session_state['assignment_form_reset_counter']}",
            label_visibility="collapsed",
        )

    with ui.card():
        st.markdown("#### 2. 평가 설계")
        st.write("1) 평가요소와 채점기준 (*)")

        with st.container(key="criteria_table"):
            total_score = _render_criteria_groups_editor("new_criteria_groups")

        st.write("")
        st.write("2) 예시답안 · 작성은 선택")
        example_answer = st.text_area("예시답안", placeholder="예시답안을 입력하세요 (선택)", label_visibility="collapsed")

        # 과제 마감일 · 재검사 문항 수 · 마감 시각을 한 행에 배치합니다.
        col_date, col_retest, col_time = st.columns(3)
        with col_date:
            deadline_date = st.date_input("과제 마감일", key="assign_deadline_date")
        with col_retest:
            retest_count = st.selectbox("재검사 문항 수", [5, 10, 15, 20], index=1, key="assign_retest_count")
        with col_time:
            time_options = _build_deadline_time_options()
            default_idx = time_options.index("18:00") if "18:00" in time_options else 0
            deadline_time = st.selectbox("마감 시각", time_options, index=default_idx, key="assign_deadline_time")

    # key="submit_new_assignment" : 상단 탭의 "과제 생성" 버튼과 라벨이 같아서
    # key를 명시하지 않으면 Streamlit이 두 버튼을 동일한 요소로 착각해 오류가 납니다.
    if st.button("과제 생성", type="primary", use_container_width=True, key="submit_new_assignment"):
        # 그룹 구조(평가요소 + 여러 배점/채점기준)를 DB 저장용 평평한 목록으로 변환
        flat_criteria = [
            {"element_name": g["element_name"], "score": it["score"], "criteria_text": it["criteria_text"]}
            for g in st.session_state["new_criteria_groups"] for it in g["items"]
        ]
        if not unit_name:
            st.error("단원명을 선택해주세요.")
        elif not selected_standards:
            st.error("성취기준을 최소 1개 이상 선택해주세요.")
        elif not title or not question_text:
            st.error("과제명, 평가문항은 필수 입력입니다.")
        elif not any(c["element_name"] for c in flat_criteria):
            st.error("평가요소를 최소 1개 이상 입력해주세요.")
        else:
            deadline_str = f"{deadline_date} {deadline_time}"
            db.create_assignment(
                unit_name=unit_name,
                achievement_standard=achievement_standard,
                title=title,
                question_text=question_text,
                core_concepts_list=selected_concepts,
                deadline=deadline_str,
                retest_count=retest_count,
                example_answer=example_answer,
                criteria_list=flat_criteria,
                created_by=auth.current_user()["id"],
            )
            # 입력폼 상태 초기화
            st.session_state["new_criteria_groups"] = [
                {"gid": uuid.uuid4().hex, "element_name": "",
                 "items": [{"iid": uuid.uuid4().hex, "score": 10, "criteria_text": ""}]}
            ]
            st.session_state["new_assignment_unit"] = None
            st.session_state["new_selected_standards"] = [""]
            st.session_state["assignment_form_reset_counter"] += 1
            st.success("과제가 생성되었습니다.")
            go_to("admin_assignment_list")


def _build_deadline_time_options():
    """
    마감 시각 선택지를 만듭니다: 00:01로 시작해서 정각/30분 단위(00:30, 01:00, 01:30, ...)로
    진행하다가 마지막에 23:59로 끝납니다.
    """
    options = ["00:01"]
    for h in range(24):
        for m in (0, 30):
            if h == 0 and m == 0:
                continue  # 00:00은 제외 (00:01부터 시작)
            options.append(f"{h:02d}:{m:02d}")
    if options[-1] != "23:59":
        options.append("23:59")
    return options


def _assignment_sub_nav(active):
    """과제관리 하위 탭(과제생성/과제조회/제출현황) 네비게이션"""
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("과제 생성", use_container_width=True, type="primary" if active == "create" else "secondary"):
            go_to("admin_assignment_create")
    with c2:
        if st.button("과제 조회", use_container_width=True, type="primary" if active == "list" else "secondary"):
            go_to("admin_assignment_list")
    with c3:
        if st.button("제출 현황", use_container_width=True, type="primary" if active == "status" else "secondary"):
            go_to("admin_submission_status")
    st.write("")


# ============================================================
# 슬라이드 8: 과제 조회 (목록)
# ============================================================
def render_assignment_list():
    render_admin_nav("assignments")
    _assignment_sub_nav("list")

    ui.page_header(
        "과제 조회",
        "생성된 모든 과제를 확인합니다.",
        eyebrow="Assignment",
    )
    assignments = db.list_assignments()  # 저장된 순서(sort_order) 또는 생성순(오래된 순)으로 정렬됨

    if not assignments:
        ui.empty_state("등록된 과제가 없습니다. '과제 생성' 탭에서 새 과제를 만들어보세요.", icon="📋")
        return

    if "assign_reorder_selected_id" not in st.session_state:
        st.session_state["assign_reorder_selected_id"] = None
    selected_id = st.session_state["assign_reorder_selected_id"]

    col_widths = [0.35, 0.35, 1.2, 1.6, 0.8, 1.3, 1.0, 1.15, 1.15]
    with st.container(key="assignments_table"):
        with st.container(key="assign_header_row"):
            header = st.columns(col_widths)
            for h, text in zip(header, ["", "순", "단원명", "과제명", "점수", "제출기한", "성취기준", "배포상태", ""]):
                if text:
                    h.markdown(f"**{text}**")

        for i, a in enumerate(assignments, start=1):
            with st.container(key=f"trow_assign_{a['id']}"):
                c = st.columns(col_widths)

                # ---- 체크박스: 이 과제를 순서 변경 대상으로 선택합니다 (한 번에 하나만 선택) ----
                checked = c[0].checkbox(
                    "선택", key=f"select_{a['id']}", value=(selected_id == a["id"]),
                    label_visibility="collapsed",
                )
                if checked and selected_id != a["id"]:
                    st.session_state["assign_reorder_selected_id"] = a["id"]
                    st.rerun()
                elif not checked and selected_id == a["id"]:
                    st.session_state["assign_reorder_selected_id"] = None
                    st.rerun()

                c[1].markdown(f"<span class='ec-cell-text'>{i}</span>", unsafe_allow_html=True)
                c[2].markdown(f"<span class='ec-cell-text'>{a['unit_name']}</span>", unsafe_allow_html=True)
                with c[3]:
                    # '상세보기' 버튼 대신, 과제명 자체를 링크처럼 만들어 클릭하면 상세보기로 이동합니다.
                    with st.container(key=f"title_link_{a['id']}"):
                        if st.button(a["title"], key=f"open_{a['id']}"):
                            go_to("admin_assignment_detail", selected_assignment_id=a["id"])

                total_score = sum(x["score"] for x in db.get_eval_criteria(a["id"]))
                c[4].markdown(f"<span class='ec-cell-text'>{total_score}점</span>", unsafe_allow_html=True)
                c[5].markdown(f"<span class='ec-cell-text'>{a['deadline'] or '-'}</span>", unsafe_allow_html=True)

                # ---- 성취기준: 버튼을 누르면 팝업으로 내용을 보여줍니다 (배포 버튼들과 크기 통일) ----
                with c[6]:
                    with st.container(key=f"criteria_popover_{a['id']}"):
                        with st.popover("성취기준", use_container_width=True):
                            st.write(a["achievement_standard"])

                # ---- 배포상태 / 빈칸(비고): 배포하기·배포중·배포취소 버튼 크기를 모두 동일하게 맞춥니다 ----
                if a["status"] == "배포중":
                    with c[7]:
                        with st.container(key=f"status_badge_{a['id']}"):
                            st.button("배포중", key=f"status_{a['id']}", use_container_width=True, disabled=True)
                    if c[8].button("배포 취소", key=f"unpublish_{a['id']}", use_container_width=True):
                        db.set_assignment_status(a["id"], "배포전")
                        st.rerun()
                else:
                    if c[7].button("배포하기", key=f"publish_{a['id']}", use_container_width=True, type="primary"):
                        db.set_assignment_status(a["id"], "배포중")
                        st.rerun()
                    # 배포 전 과제는 빈칸을 완전히 비워둡니다 (문자 하나 없이).

    # ---- 순서 변경 아이콘: 표 컨테이너 바깥, 왼쪽 정렬 ----
    # 실제 마우스 드래그는 Streamlit 자체 위젯만으로는 지원되지 않아
    # (검토해 본 드래그 컴포넌트는 이 앱의 여러 페이지를 오가는 구조와 함께 쓰면
    # 이따금 오류가 나서 제외했습니다) 체크박스로 과제를 고른 뒤 ▲▼ 버튼으로 옮기는 방식입니다.
    with st.container(key="reorder_controls"):
        mv_up, mv_down, mv_caption, _spacer = st.columns([0.4, 0.4, 4, 5])
        with mv_up:
            up_clicked = st.button("▲", key="reorder_up", use_container_width=True)
        with mv_down:
            down_clicked = st.button("▼", key="reorder_down", use_container_width=True)
        with mv_caption:
            st.markdown(
                "<div style='padding-top:0.45rem; color:#64748B; font-size:0.85rem;'>"
                "과제를 체크한 뒤 ▲▼ 버튼을 누르면 순서를 바꿀 수 있어요.</div>",
                unsafe_allow_html=True,
            )

    if up_clicked or down_clicked:
        if selected_id is None:
            st.warning("먼저 순서를 바꿀 과제를 체크해주세요.")
        else:
            ids = [x["id"] for x in assignments]
            idx = ids.index(selected_id)
            if up_clicked and idx > 0:
                ids[idx - 1], ids[idx] = ids[idx], ids[idx - 1]
                db.set_assignment_order(ids)
                st.rerun()
            elif down_clicked and idx < len(ids) - 1:
                ids[idx], ids[idx + 1] = ids[idx + 1], ids[idx]
                db.set_assignment_order(ids)
                st.rerun()


# ============================================================
# 슬라이드 9~10: 과제 상세보기
# ============================================================
def render_assignment_detail():
    render_admin_nav("assignments")
    assignment_id = st.session_state.get("selected_assignment_id")
    assignment = db.get_assignment(assignment_id)

    if not assignment:
        st.error("과제를 찾을 수 없습니다.")
        return

    if st.button("← 과제 조회로"):
        go_to("admin_assignment_list")

    ui.page_header(assignment["title"], assignment["unit_name"], eyebrow="Assignment Detail")

    aid = assignment_id
    # '배포하기' 상태(=아직 배포 전)일 때만 실제로 수정할 수 있습니다.
    # '배포중'일 때는 수정 버튼을 눌러도 편집 모드로 들어가지 않고 안내만 표시합니다.
    is_locked = assignment["status"] == "배포중"

    def edit_toggle(field_key):
        state_key = f"detail_edit_{field_key}_{aid}"
        if state_key not in st.session_state:
            st.session_state[state_key] = False
        if st.button("수정", key=f"btn_edit_{field_key}_{aid}", use_container_width=True):
            if is_locked:
                st.warning("배포중이 아닌 상태에서만 수정할 수 있습니다. 배포 취소를 한 후 다시 시도해주세요.")
            else:
                st.session_state[state_key] = True
                st.rerun()
        return st.session_state[state_key]

    # ---- 단원명/성취기준 편집에 쓸 임시 상태를 미리 준비합니다 ----
    if f"detail_unit_choice_{aid}" not in st.session_state:
        st.session_state[f"detail_unit_choice_{aid}"] = (
            assignment["unit_name"] if assignment["unit_name"] in CURRICULUM_UNITS else None
        )
    if f"detail_standards_{aid}" not in st.session_state:
        existing = [s for s in (assignment["achievement_standard"] or "").split("\n") if s]
        st.session_state[f"detail_standards_{aid}"] = existing or [""]

    with ui.card():
        # ---- 단원명 ----
        c1, c2, c3 = st.columns([1, 4, 1])
        c1.markdown("**단원명**")
        c2.markdown(f"<span class='ec-cell-text'>{assignment['unit_name']}</span>", unsafe_allow_html=True)
        with c3:
            editing_unit = edit_toggle("unit")
        if editing_unit:
            with st.container(key=f"unit_cards_detail_{aid}"):
                u_cols = st.columns(3)
                for i, u in enumerate(CURRICULUM_UNITS):
                    with u_cols[i]:
                        sel = st.session_state[f"detail_unit_choice_{aid}"] == u
                        if st.button(u, key=f"detail_unit_card_{aid}_{i}", use_container_width=True,
                                     type="primary" if sel else "secondary"):
                            st.session_state[f"detail_unit_choice_{aid}"] = u
                            st.session_state[f"detail_standards_{aid}"] = [""]
                            st.rerun()

        effective_unit = st.session_state[f"detail_unit_choice_{aid}"] or assignment["unit_name"]

        # ---- 성취기준 ----
        c1, c2, c3 = st.columns([1, 4, 1])
        c1.markdown("**성취기준**")
        c2.markdown(f"<span class='ec-cell-text'>{assignment['achievement_standard']}</span>", unsafe_allow_html=True)
        with c3:
            editing_standard = edit_toggle("standard")
        if editing_standard:
            available = UNIT_ACHIEVEMENT_STANDARDS.get(effective_unit, [])
            if not available:
                st.caption("이 단원에 해당하는 성취기준 목록이 없습니다. 단원명을 먼저 수정해주세요.")
            else:
                for idx, val in enumerate(st.session_state[f"detail_standards_{aid}"]):
                    col_sel, col_rm = st.columns([6, 0.5])
                    with col_sel:
                        options = [""] + available
                        # 예전 데이터 등으로 목록에 없는 값이면 표시가 깨지지 않도록 임시로 추가합니다.
                        if val and val not in options:
                            options = options + [val]
                        default_index = options.index(val) if val in options else 0
                        chosen = st.selectbox(
                            f"성취기준 선택 {idx + 1}", options, index=default_index,
                            key=f"detail_std_select_{aid}_{idx}", label_visibility="collapsed",
                        )
                        st.session_state[f"detail_standards_{aid}"][idx] = chosen
                    with col_rm:
                        if len(st.session_state[f"detail_standards_{aid}"]) > 1 and st.button(
                            "✕", key=f"detail_std_rm_{aid}_{idx}"
                        ):
                            st.session_state[f"detail_standards_{aid}"].pop(idx)
                            st.rerun()
                if st.button("+ 추가", key=f"detail_std_add_{aid}"):
                    st.session_state[f"detail_standards_{aid}"].append("")
                    st.rerun()

        # ---- 평가문항 ----
        c1, c2, c3 = st.columns([1, 4, 1])
        c1.markdown("**평가문항**")
        c2.markdown(f"<span class='ec-cell-text'>{assignment['question_text']}</span>", unsafe_allow_html=True)
        with c3:
            editing_question = edit_toggle("question")
        if editing_question:
            st.session_state[f"detail_question_{aid}"] = st.text_area(
                "평가문항 수정", value=assignment["question_text"],
                key=f"detail_question_input_{aid}", label_visibility="collapsed",
            )

        # ---- 핵심개념(내용요소) ----
        c1, c2, c3 = st.columns([1, 4, 1])
        c1.markdown("**핵심개념(내용요소)**")
        c2.markdown(
            f"<span class='ec-cell-text'>{' · '.join(assignment['core_concepts']) if assignment['core_concepts'] else '-'}</span>",
            unsafe_allow_html=True,
        )
        with c3:
            editing_concepts = edit_toggle("concepts")
        if editing_concepts:
            legacy_extra = [c for c in assignment["core_concepts"] if c not in CORE_CONCEPTS_ALL]
            options = CORE_CONCEPTS_ALL + legacy_extra
            st.session_state[f"detail_concepts_{aid}"] = st.multiselect(
                "핵심 개념(내용 요소) 수정", options, default=assignment["core_concepts"],
                key=f"detail_concepts_ms_{aid}", label_visibility="collapsed",
            )

    with ui.card():
        st.markdown("#### 평가 설계")

        # ---- 1) 평가요소와 채점기준 (굵게) ----
        c1, c2 = st.columns([5, 1])
        c1.markdown("**1) 평가요소와 채점기준**")
        with c2:
            editing_criteria = edit_toggle("criteria")

        criteria = db.get_eval_criteria(assignment_id)
        groups_key = f"detail_criteria_groups_{aid}"
        if editing_criteria:
            if groups_key not in st.session_state:
                st.session_state[groups_key] = _flatten_to_groups(criteria)
            # 표 컨테이너에 연한 테두리를 넣어 위 타이틀과 구분되도록 합니다.
            with st.container(key="criteria_table"):
                _render_criteria_groups_editor(groups_key)
        else:
            with st.container(key="criteria_table"):
                if criteria:
                    header = st.columns([3, 1, 4])
                    for h, t in zip(header, ["평가요소", "배점", "채점기준"]):
                        h.markdown(f"**{t}**")
                    total = 0
                    for c in criteria:
                        row = st.columns([3, 1, 4])
                        row[0].write(c["element_name"])
                        row[1].write(f"{c['score']}점")
                        row[2].write(c["criteria_text"])
                        total += c["score"]
                    t1, t2, t3 = st.columns([3, 1, 4])
                    t1.markdown("**배점 합계**")
                    t2.markdown(f"**{total}점**")
                else:
                    st.caption("등록된 평가요소가 없습니다.")

        st.write("")
        # ---- 2) 예시답안 (굵게) ----
        c1, c2 = st.columns([5, 1])
        c1.markdown("**2) 예시답안**")
        with c2:
            editing_example = edit_toggle("example")
        if editing_example:
            st.session_state[f"detail_example_{aid}"] = st.text_area(
                "예시답안 수정", value=assignment["example_answer"] or "",
                key=f"detail_example_input_{aid}", label_visibility="collapsed",
            )
        else:
            st.write(assignment["example_answer"] or "-")

    st.write("")
    if st.button("💾 저장", type="primary", use_container_width=True, key=f"detail_save_{aid}"):
        if is_locked:
            st.warning("배포중이 아닌 상태에서만 수정할 수 있습니다. 배포 취소를 한 후 다시 시도해주세요.")
        else:
            final_unit = st.session_state.get(f"detail_unit_choice_{aid}") or assignment["unit_name"]
            final_standards = [s for s in st.session_state.get(f"detail_standards_{aid}", []) if s]
            final_standard_str = "\n".join(final_standards) if final_standards else assignment["achievement_standard"]
            final_question = st.session_state.get(f"detail_question_{aid}", assignment["question_text"])
            final_concepts = st.session_state.get(f"detail_concepts_ms_{aid}", assignment["core_concepts"])
            final_example = st.session_state.get(f"detail_example_{aid}", assignment["example_answer"])

            db.update_assignment_fields(
                aid,
                unit_name=final_unit,
                achievement_standard=final_standard_str,
                question_text=final_question,
                core_concepts_list=final_concepts,
                example_answer=final_example,
            )

            if groups_key in st.session_state:
                flat = [
                    {"element_name": g["element_name"], "score": it["score"], "criteria_text": it["criteria_text"]}
                    for g in st.session_state[groups_key] for it in g["items"] if g["element_name"]
                ]
                if flat:
                    db.replace_eval_criteria(aid, flat)

            # 이 과제에 대한 편집 관련 임시 상태를 모두 정리합니다.
            for f in ["unit", "standard", "question", "concepts", "criteria", "example"]:
                st.session_state.pop(f"detail_edit_{f}_{aid}", None)
            for k in [
                f"detail_unit_choice_{aid}", f"detail_standards_{aid}", f"detail_question_{aid}",
                f"detail_concepts_{aid}", f"detail_example_{aid}", groups_key,
            ]:
                st.session_state.pop(k, None)
            st.success("저장되었습니다.")
            st.rerun()


# ============================================================
# 슬라이드 11: 제출 현황
# ============================================================
def render_submission_status():
    render_admin_nav("assignments")
    _assignment_sub_nav("status")

    ui.page_header("제출 현황", "과제별 학생 제출/재검사/결과확인 진행률을 확인합니다.", eyebrow="Assignment")

    assignments = db.list_assignments()
    if not assignments:
        ui.empty_state("등록된 과제가 없습니다.", icon="📋")
        return

    # ---- 과제 선택: 라벨과 콤보박스를 더 크고 눈에 띄게 ----
    with st.container(key="assignment_select_box"):
        st.markdown("<div class='ec-select-label'>과제 선택</div>", unsafe_allow_html=True)
        options = {a["title"]: a["id"] for a in assignments}
        selected_title = st.selectbox("과제 선택", list(options.keys()), label_visibility="collapsed")
        assignment_id = options[selected_title]
        selected_assignment = db.get_assignment(assignment_id)
        if selected_assignment and selected_assignment.get("status") != "배포중":
            st.markdown(f"<div style='margin-top:0.3rem;'>{ui.badge('미배포', 'muted')}</div>", unsafe_allow_html=True)

    st.write("")

    rows = db.list_submissions_for_assignment(assignment_id)
    results = {r["student_id"]: r for r in db.list_retest_results(assignment_id)}

    # 회원가입한 학생 수 / 실제 배포된 과제 수를 그대로 사용합니다.
    total_registered_students = len(db.list_students())
    published_count = len(db.list_published_assignments())
    submitted = sum(1 for r in rows if r["submission_id"] is not None)
    retest_done = sum(1 for r in rows if r["id"] in results)
    result_checked = sum(1 for r in rows if r["id"] in results and results[r["id"]].get("result_viewed_at"))

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("진행 중인 과제", f"{published_count}건")
    with m2:
        st.metric("전체 학생 수", f"{total_registered_students}명")
    with m3:
        ui.colored_metric("과제 제출", f"{submitted}명", "#DBEAFE", "#1D4ED8")
    with m4:
        ui.colored_metric("재검사 완료", f"{retest_done}명", "#EDE9FE", "#6D28D9")
    with m5:
        ui.colored_metric("결과 확인", f"{result_checked}명", "#FEF3C7", "#B45309")

    st.write("")
    st.write("")

    col_widths = [0.5, 1.2, 1, 0.8, 0.8, 0.8, 1.6, 1.1, 1.1]
    with st.container(key="submission_status_table"):
        with st.container(key="status_header_row"):
            header = st.columns(col_widths)
            for h, t in zip(header, ["순", "학생 이름", "학교명", "학년", "반", "번호", "과제 제출", "재검사완료", "결과확인"]):
                h.markdown(f"**{t}**")

        for i, r in enumerate(rows, start=1):
            with st.container(key=f"trow_status_{r['id']}"):
                c = st.columns(col_widths)
                c[0].markdown(f"<span class='ec-cell-text-center'>{i}</span>", unsafe_allow_html=True)
                c[1].markdown(f"<span class='ec-cell-text-center'>{r['name']}</span>", unsafe_allow_html=True)
                c[2].markdown(f"<span class='ec-cell-text-center'>{r['school'] or '-'}</span>", unsafe_allow_html=True)
                c[3].markdown(f"<span class='ec-cell-text-center'>{r['grade'] or '-'}</span>", unsafe_allow_html=True)
                c[4].markdown(f"<span class='ec-cell-text-center'>{r['class_no'] or '-'}</span>", unsafe_allow_html=True)
                c[5].markdown(f"<span class='ec-cell-text-center'>{r['student_no'] or '-'}</span>", unsafe_allow_html=True)

                # ---- 과제 제출: 제출 시각(초록) + PDF 다운로드 아이콘 / 미완료(빨강) ----
                if r["submission_id"] and r.get("submitted_at"):
                    txt_col, icon_col = c[6].columns([3, 1])
                    txt_col.markdown(f"<span class='ec-status-done'>{r['submitted_at']}</span>", unsafe_allow_html=True)
                    pdf_path = r.get("pdf_path")
                    if pdf_path and os.path.exists(pdf_path):
                        with open(pdf_path, "rb") as f:
                            pdf_bytes = f.read()
                        icon_col.download_button(
                            "📄", data=pdf_bytes,
                            file_name=r.get("pdf_filename") or f"{r['name']}.pdf",
                            key=f"dl_submission_{r['id']}",
                            help="제출한 과제 PDF 다운로드",
                        )
                else:
                    c[6].markdown("<span class='ec-status-pending'>미완료</span>", unsafe_allow_html=True)

                result = results.get(r["id"])

                # ---- 재검사 완료: 완료/미완료 ----
                if result and result.get("completed_at"):
                    c[7].markdown("<span class='ec-status-done'>완료</span>", unsafe_allow_html=True)
                else:
                    c[7].markdown("<span class='ec-status-pending'>미완료</span>", unsafe_allow_html=True)

                # ---- 결과 확인: 완료/미완료 ----
                if result and result.get("result_viewed_at"):
                    c[8].markdown("<span class='ec-status-done'>완료</span>", unsafe_allow_html=True)
                else:
                    c[8].markdown("<span class='ec-status-pending'>미완료</span>", unsafe_allow_html=True)


# ============================================================
# 슬라이드 12: 문항 검토 (목록)
# ============================================================
def _demo_teacher_review_questions():
    """'과제 이해도 문항 생성' 데모용 예시 문항 5개 (실제 AI 호출 없이 화면 확인용, 근거 문구 포함)."""
    samples = [
        ("발산형 경계에서 공통적으로 나타나는 현상으로 가장 적절한 것은?",
         ["새로운 지각(암석권)이 생성된다", "기존 지각이 소멸된다", "습곡 산맥이 형성된다", "변성암이 대규모로 생성된다", "지진이 전혀 발생하지 않는다"],
         "새로운 지각(암석권)이 생성된다", 1,
         "발산형 경계에서는 맨틀 물질이 상승하면서 새로운 지각이 계속 생성된다고 서술하였다."),
        ("수렴형 경계 중 해양판과 대륙판이 만나는 경우 주로 형성되는 지형은?",
         ["해구와 호상열도/화산호", "중앙해령", "변환단층", "열곡대", "대륙 분지"],
         "해구와 호상열도/화산호", 1,
         "해양판이 대륙판 아래로 섭입하면서 해구가 만들어지고 화산 활동이 일어난다고 답하였다."),
        ("변환형 경계의 대표적인 특징으로 옳은 것은?",
         ["판이 서로 수평으로 어긋나며 이동한다", "새로운 지각이 활발히 생성된다", "마그마가 대량으로 분출한다", "대규모 습곡 산맥이 만들어진다", "해양 지각만 존재한다"],
         "판이 서로 수평으로 어긋나며 이동한다", 2,
         "산안드레아스 단층을 예로 들며, 두 판이 나란히 미끄러지듯 이동한다고 서술하였다."),
        ("판 경계에서의 지진과 화산 활동에 대한 설명으로 가장 적절한 것은?",
         ["경계 유형에 따라 발생 양상이 다르게 나타난다", "판 경계에서는 지진만 발생하고 화산은 없다", "모든 판 경계에서 동일한 세기로 발생한다", "판 내부에서만 발생한다", "화산 활동은 발산형 경계에서만 일어난다"],
         "경계 유형에 따라 발생 양상이 다르게 나타난다", 2,
         "발산형·수렴형·변환형 경계마다 지진과 화산 활동의 양상이 다르게 나타난다고 비교하여 서술하였다."),
        ("맨틀 대류와 판의 이동 사이의 관계로 옳은 것은?",
         ["맨틀 대류가 판을 움직이는 주요 원동력 중 하나이다", "맨틀 대류와 판 이동은 서로 무관하다", "판은 맨틀 대류와 반대 방향으로만 움직인다", "맨틀 대류는 판의 두께에만 영향을 준다", "맨틀 대류는 해양판에서만 나타난다"],
         "맨틀 대류가 판을 움직이는 주요 원동력 중 하나이다", 3,
         "맨틀 대류가 판을 이동시키는 힘으로 작용한다고 결론 부분에 서술하였다."),
    ]
    return [
        {"question_text": q, "choices": choices, "answer": answer, "basis_page": page, "basis_quote": quote}
        for q, choices, answer, page, quote in samples
    ]


def _ensure_student_questions(assignment, student):
    """
    이 학생에게 이미 생성된 개인 맞춤 문항이 있으면 그대로 두고,
    없으면 실제로 제출한 PDF 답안을 근거로 AI에게 문항 생성을 요청해 저장합니다.
    성공하면 True, 실패(제출물 없음/AI 오류)하면 False를 반환합니다.
    """
    existing = db.get_student_generated_questions(assignment["id"], student["id"])
    if existing:
        return True

    if student.get("username") == config.DEMO_MODE_STUDENT_USERNAME:
        # ---- [데모/화면 확인용] ----
        # 이 학생은 실제 AI 호출 없이 예시 문항(근거 문구 포함)으로 화면 구성을 바로 확인합니다.
        # 실제 AI로 전환하려면 config.DEMO_MODE_STUDENT_USERNAME을 None으로 바꾸세요.
        db.save_student_generated_questions(assignment["id"], student["id"], _demo_teacher_review_questions())
        return True

    submission = db.get_submission(assignment["id"], student["id"])
    if not submission:
        st.error(f"{student['name']} 학생은 아직 이 과제를 제출하지 않아 문항을 생성할 수 없습니다.")
        return False

    with st.spinner("AI가 학생 답안을 분석해 맞춤 문항을 생성하고 있습니다..."):
        try:
            generated = ai_engine.generate_personalized_questions(
                submission["pdf_path"],
                count=assignment.get("retest_count") or 10,
                unit_name=assignment["unit_name"],
                achievement_standard=assignment["achievement_standard"],
                question_text=assignment["question_text"],
            )
        except ai_engine.AIEngineError as e:
            st.error(str(e))
            return False

    db.save_student_generated_questions(assignment["id"], student["id"], generated)
    return True


def render_question_review():
    render_admin_nav("review")
    ui.page_header("문항 검토", "AI가 선정한 재검사 문항과 선정 근거를 검토합니다.", eyebrow="Review")

    assignments = db.list_assignments()
    if not assignments:
        ui.empty_state("등록된 과제가 없습니다.", icon="🔍")
        return

    with st.container(key="assignment_select_box"):
        st.markdown("<div class='ec-select-label'>과제 선택</div>", unsafe_allow_html=True)
        options = {a["title"]: a["id"] for a in assignments}
        selected_title = st.selectbox("과제 선택", list(options.keys()), label_visibility="collapsed")
        assignment_id = options[selected_title]
        assignment = db.get_assignment(assignment_id)
        if assignment and assignment.get("status") != "배포중":
            st.markdown(f"<div style='margin-top:0.3rem;'>{ui.badge('미배포', 'muted')}</div>", unsafe_allow_html=True)
    st.write("")

    students = db.list_students()  # 실제로는 해당 과제를 제출한 학생만 필터링하는 것이 이상적
    col_widths = [0.4, 0.4, 0.9, 0.8, 0.5, 0.5, 0.5, 1.7, 0.9]

    # 체크박스 위젯 자신의 session_state 값을 그대로 읽습니다 (이전 렌더에서 저장된 값이라
    # 화면이 다시 그려지는 이번 렌더의 맨 위에서부터 곧바로 정확한 선택 상태를 알 수 있습니다).
    selected_students = [s for s in students if st.session_state.get(f"bulk_chk_{s['id']}", False)]

    with st.container(key="bulk_distribute_wrap"):
        if st.button("📤 선택한 학생 일괄 배포", type="primary", disabled=not selected_students):
            distributed_names = []
            for s in selected_students:
                if _ensure_student_questions(assignment, s):
                    db.distribute_student_questions(assignment_id, s["id"])
                    distributed_names.append(s["name"])
            if distributed_names:
                st.success(f"{', '.join(distributed_names)} 학생에게 문항이 일괄 배포되었습니다.")
            st.rerun()

    with st.container(key="review_table"):
        with st.container(key="review_header_row"):
            header = st.columns(col_widths)
            for h, t in zip(header, ["☐", "순", "학생명", "학교", "학년", "반", "번호", "과제 이해도 문항 생성", "배포"]):
                h.markdown(f"**{t}**")

        for i, s in enumerate(students, start=1):
            with st.container(key=f"trow_review_{s['id']}"):
                c = st.columns(col_widths)

                # 데모 계정(예: student1)은 실제 제출 여부와 상관없이 화면 구성을 미리 확인할 수 있습니다.
                is_demo = s.get("username") == config.DEMO_MODE_STUDENT_USERNAME
                has_submission = is_demo or db.get_submission(assignment_id, s["id"]) is not None

                c[0].checkbox(
                    "선택", value=s["id"] in [x["id"] for x in selected_students],
                    key=f"bulk_chk_{s['id']}", label_visibility="collapsed",
                    disabled=not has_submission,
                )

                c[1].markdown(f"<span class='ec-cell-text-center'>{i}</span>", unsafe_allow_html=True)
                c[2].markdown(f"<span class='ec-cell-text-center'>{s['name']}</span>", unsafe_allow_html=True)
                c[3].markdown(f"<span class='ec-cell-text-center'>{s['school'] or '-'}</span>", unsafe_allow_html=True)
                c[4].markdown(f"<span class='ec-cell-text-center'>{s['grade'] or '-'}</span>", unsafe_allow_html=True)
                c[5].markdown(f"<span class='ec-cell-text-center'>{s['class_no'] or '-'}</span>", unsafe_allow_html=True)
                c[6].markdown(f"<span class='ec-cell-text-center'>{s['student_no'] or '-'}</span>", unsafe_allow_html=True)

                if not has_submission:
                    c[7].markdown("<span class='ec-status-stage'>과제 미제출</span>", unsafe_allow_html=True)
                    c[8].markdown("<span class='ec-status-stage'>과제 미제출</span>", unsafe_allow_html=True)
                else:
                    if c[7].button("과제 이해도 문항 생성", key=f"qview_{s['id']}", use_container_width=True):
                        if _ensure_student_questions(assignment, s):
                            go_to("admin_review_detail", selected_assignment_id=assignment_id, selected_student_id=s["id"])
                    already_distributed = db.is_distributed(assignment_id, s["id"])
                    if c[8].button(
                        "✓ 배포됨" if already_distributed else "배포",
                        key=f"distribute_{s['id']}", use_container_width=True,
                        type="secondary" if already_distributed else "primary",
                    ):
                        if already_distributed:
                            db.undistribute_student_questions(assignment_id, s["id"])
                            st.info(f"{s['name']} 학생에 대한 배포가 취소되었습니다.")
                            st.rerun()
                        elif _ensure_student_questions(assignment, s):
                            db.distribute_student_questions(assignment_id, s["id"])
                            st.success(f"{s['name']} 학생에게 문항이 배포되었습니다.")
                            st.rerun()


# ============================================================
# 슬라이드 13: 문항 검토 - 상세보기 (문항은행)
# ============================================================
def render_question_review_detail():
    render_admin_nav("review")

    assignment_id = st.session_state.get("selected_assignment_id")
    student_id = st.session_state.get("selected_student_id")
    assignment = db.get_assignment(assignment_id)

    student = None
    for s in db.list_students():
        if s["id"] == student_id:
            student = s
            break

    if st.button("← 문항 검토로"):
        go_to("admin_review")

    if student and assignment:
        st.caption(f"{student['name']} · {student['school']} · {student['grade']} {student['class_no']} {student['student_no']}번 · {assignment['title']}")

    questions = db.get_student_generated_questions(assignment_id, student_id)
    ui.page_header(
        "과제 이해도 문항 생성",
        f"{student['name'] if student else ''} 학생의 과제를 근거로 생성된 맞춤 문항 {len(questions)}개를 검토·수정할 수 있습니다.",
        eyebrow="Question Bank",
    )

    if not questions:
        ui.empty_state("아직 생성된 문항이 없습니다.", icon="🤖")
        return

    col_widths = [0.5, 2, 1.8, 0.9, 1.6, 0.7, 0.7]
    with st.container(key="review_detail_table"):
        with st.container(key="review_detail_header_row"):
            header = st.columns(col_widths)
            for h, t in zip(header, ["문항번호", "문항", "보기", "정답", "문항 생성 근거", "", ""]):
                h.markdown(f"**{t}**")

        for i, q in enumerate(questions, start=1):
            mapping_id = q["mapping_id"]
            with st.container(key=f"trow_qbank_{mapping_id}"):
                c = st.columns(col_widths)
                c[0].markdown(f"<span class='ec-cell-text-center'>{i}</span>", unsafe_allow_html=True)
                c[1].markdown(f"<span class='ec-cell-text'>{q['question_text']}</span>", unsafe_allow_html=True)
                choices_html = "<br>".join(f"{j + 1}. {ch}" for j, ch in enumerate(q["choices"]))
                c[2].markdown(f"<span class='ec-cell-text-sm'>{choices_html}</span>", unsafe_allow_html=True)
                # 정답은 보기 번호(1~5)로 표시합니다.
                answer_no = q["choices"].index(q["answer"]) + 1 if q["answer"] in q["choices"] else "-"
                c[3].markdown(f"<span class='ec-cell-text-center'>{answer_no}</span>", unsafe_allow_html=True)

                # ---- 문항 생성 근거: 학생 과제의 페이지 + 문단 요약, 🔍 아이콘 클릭 시 상세 팝업 ----
                with c[4]:
                    quote = q.get("basis_quote") or ""
                    preview = quote if len(quote) <= 22 else quote[:22] + "…"
                    page_label = f"{q['basis_page']}페이지" if q.get("basis_page") else "근거"
                    pc1, pc2 = st.columns([4, 1])
                    pc1.markdown(
                        f"<span class='ec-cell-text-sm'><b>{page_label}</b><br>{preview}</span>",
                        unsafe_allow_html=True,
                    )
                    with pc2.popover("🔍"):
                        st.markdown("**학생 과제 페이지 및 단락**")
                        st.write(page_label)
                        st.divider()
                        st.markdown("**학생 과제물 원문 및 문항 생성 근거**")
                        st.write(f"원문: {quote or '근거 문구가 저장되어 있지 않습니다.'}")
                        st.write(f"생성 근거: {q.get('ai_reason') or '-'}")

                if c[5].button("수정", key=f"editbtn_{mapping_id}", use_container_width=True):
                    st.session_state[f"review_edit_open_{mapping_id}"] = not st.session_state.get(
                        f"review_edit_open_{mapping_id}", False
                    )
                    st.rerun()
                if c[6].button("삭제", key=f"delbtn_{mapping_id}", use_container_width=True):
                    db.delete_student_question(mapping_id)
                    st.rerun()

                # ---- 수정 패널: 문항 / 보기 / 정답 중 무엇을 고칠지 선택 후 직접 수정 ----
                if st.session_state.get(f"review_edit_open_{mapping_id}"):
                    with st.container(key=f"review_edit_panel_{mapping_id}"):
                        target = st.radio(
                            "무엇을 수정하시겠습니까?", ["문항", "보기(선지)", "정답"],
                            key=f"review_edit_target_{mapping_id}", horizontal=True,
                        )
                        if target == "문항":
                            new_q = st.text_area(
                                "문항 수정", value=q["question_text"],
                                key=f"editq_input_{mapping_id}", label_visibility="collapsed",
                            )
                            if st.button("저장", key=f"save_q_{mapping_id}", type="primary"):
                                db.update_student_question(q["question_id"], question_text=new_q)
                                st.session_state[f"review_edit_open_{mapping_id}"] = False
                                st.rerun()
                        elif target == "보기(선지)":
                            new_choices = []
                            for j, ch in enumerate(q["choices"]):
                                new_choices.append(
                                    st.text_input(f"보기 {j + 1}", value=ch, key=f"editc_{mapping_id}_{j}")
                                )
                            if st.button("저장", key=f"save_c_{mapping_id}", type="primary"):
                                db.update_student_question(q["question_id"], choices_list=new_choices)
                                st.session_state[f"review_edit_open_{mapping_id}"] = False
                                st.rerun()
                        else:  # 정답
                            default_idx = q["choices"].index(q["answer"]) if q["answer"] in q["choices"] else 0
                            new_answer = st.selectbox(
                                "정답 선택", q["choices"], index=default_idx,
                                key=f"edita_{mapping_id}", label_visibility="collapsed",
                            )
                            if st.button("저장", key=f"save_a_{mapping_id}", type="primary"):
                                db.update_student_question(q["question_id"], answer=new_answer)
                                st.session_state[f"review_edit_open_{mapping_id}"] = False
                                st.rerun()

    col_add, col_save = st.columns(2)
    with col_add:
        if st.button("➕ 문항 추가", use_container_width=True):
            db.save_student_generated_questions(assignment_id, student_id, [{
                "question_text": "새 문항을 입력하세요.",
                "choices": ["보기 1", "보기 2", "보기 3", "보기 4", "보기 5"],
                "answer": "보기 1",
                "basis_page": None,
                "basis_quote": "",
            }])
            st.rerun()
    with col_save:
        if st.button("💾 저장", type="primary", use_container_width=True):
            st.success("문항 검토 내용이 저장되었습니다. '문항 검토' 목록에서 [배포]를 누르면 학생에게 전달됩니다.")


def render_review_reason_detail():
    """근거보기: AI가 학생의 실제 답안 중 어느 페이지의 어떤 문장을 근거로 문항을 만들었는지 보여줍니다."""
    render_admin_nav("review")

    assignment_id = st.session_state.get("selected_assignment_id")
    student_id = st.session_state.get("selected_student_id")
    assignment = db.get_assignment(assignment_id)

    student = None
    for s in db.list_students():
        if s["id"] == student_id:
            student = s
            break

    if st.button("← 문항 검토로"):
        go_to("admin_review")

    ui.page_header("AI 문항 선정 근거", "학생의 실제 답안 내용 중 어떤 부분을 근거로 문항을 만들었는지 보여줍니다.", eyebrow="Review")

    if student and assignment:
        with ui.card():
            info_col, dl_col = st.columns([5, 1])
            with info_col:
                st.write(
                    f"**{student['name']}** · {student['school'] or '-'} · "
                    f"{student['grade'] or '-'} {student['class_no'] or '-'} {student['student_no'] or '-'}번 · "
                    f"{assignment['title']}"
                )
            with dl_col:
                submission = db.get_submission(assignment_id, student_id)
                if submission and submission.get("pdf_path") and os.path.exists(submission["pdf_path"]):
                    with open(submission["pdf_path"], "rb") as f:
                        pdf_bytes = f.read()
                    st.download_button(
                        "📄 과제물 열기", data=pdf_bytes,
                        file_name=submission.get("pdf_filename") or f"{student['name']}.pdf",
                        key=f"dl_reason_{student_id}", use_container_width=True,
                    )

    questions = db.get_student_generated_questions(assignment_id, student_id)
    if not questions:
        ui.empty_state("아직 생성된 문항이 없습니다.", icon="🤖")
        return

    col_widths = [0.6, 2.4, 2.2, 3, 0.8]
    with st.container(key="review_reason_table"):
        with st.container(key="review_reason_header_row"):
            header = st.columns(col_widths)
            for h, t in zip(header, ["문항번호", "문항", "보기", "근거", ""]):
                h.markdown(f"**{t}**")

        for i, q in enumerate(questions, start=1):
            with st.container(key=f"trow_reason_{q['mapping_id']}"):
                c = st.columns(col_widths)
                c[0].markdown(f"<span class='ec-cell-text-center'>{i}</span>", unsafe_allow_html=True)
                c[1].markdown(f"<span class='ec-cell-text'>{q['question_text']}</span>", unsafe_allow_html=True)
                choices_html = "<br>".join(f"{j + 1}. {ch}" for j, ch in enumerate(q["choices"]))
                c[2].markdown(f"<span class='ec-cell-text-sm'>{choices_html}</span>", unsafe_allow_html=True)

                if q.get("basis_page"):
                    basis_html = f"<b>{q['basis_page']}페이지</b> · \u201c{q.get('basis_quote') or ''}\u201d"
                else:
                    basis_html = q.get("ai_reason") or "-"
                c[3].markdown(f"<span class='ec-cell-text-sm'>{basis_html}</span>", unsafe_allow_html=True)
                c[4].markdown("", unsafe_allow_html=True)


# ============================================================
# 슬라이드 14: 결과 리포트
# ============================================================
def render_result_report():
    render_admin_nav("report")
    ui.page_header("결과 리포트", "학생별 재검사 결과", eyebrow="Report")

    assignments = db.list_assignments()
    if not assignments:
        ui.empty_state("등록된 과제가 없습니다.", icon="📊")
        return

    with st.container(key="assignment_select_box"):
        st.markdown("<div class='ec-select-label'>과제 선택</div>", unsafe_allow_html=True)
        options = {a["title"]: a["id"] for a in assignments}
        selected_title = st.selectbox("과제 선택", list(options.keys()), label_visibility="collapsed")
        assignment_id = options[selected_title]
        assignment = db.get_assignment(assignment_id)
        if assignment and assignment.get("status") != "배포중":
            st.markdown(f"<div style='margin-top:0.3rem;'>{ui.badge('미배포', 'muted')}</div>", unsafe_allow_html=True)

    st.write("")

    total_questions = assignment.get("retest_count") or 10

    # 과제 이해도 검사를 완료한 학생 결과 (student_id -> result dict)
    completed_results = {r["student_id"]: r for r in db.list_retest_results(assignment_id)}
    # 전체 학생을 대상으로 표시합니다 (응시하지 않은 학생도 현재 단계와 함께 보여줍니다).
    all_students = db.list_students()
    if not all_students:
        ui.empty_state("등록된 학생이 없습니다.", icon="📊")
        return

    reliability_style = {
        "상": ("#DCFCE7", "#15803D"),
        "중": ("#FEF3C7", "#B45309"),
        "하": ("#FEE2E2", "#B91C1C"),
    }
    status_labels = {
        "과제미제출": "#DB2777",
        "문항미생성": "#DB2777",
        "문항미배포": "#DB2777",
        "문항미응시": "#DB2777",
    }

    # ---- 상단: 선택한 학생 일괄 배포 (AI 피드백을 학생에게 공개) ----
    selected_students = [
        s for s in all_students
        if st.session_state.get(f"report_bulk_chk_{s['id']}", False) and s["id"] in completed_results
    ]
    with st.container(key="report_bulk_distribute_wrap"):
        if st.button("📤 선택한 학생에게 AI 피드백 일괄 배포", type="primary", disabled=not selected_students):
            distributed_names = []
            for s in selected_students:
                r = completed_results[s["id"]]
                if r.get("ai_feedback_basis"):
                    db.distribute_feedback(r["result_id"])
                    distributed_names.append(s["name"])
            if distributed_names:
                st.success(f"{', '.join(distributed_names)} 학생에게 AI 피드백이 배포되었습니다.")
            st.rerun()

    col_widths = [0.4, 0.5, 1, 1, 0.8, 0.8, 0.8, 1, 1, 1, 0.9]
    with st.container(key="report_table"):
        with st.container(key="report_header_row"):
            header = st.columns(col_widths)
            for h, t in zip(header, ["☐", "순", "학생명", "학교", "학년", "반", "번호", "과제 이해도 점수", "과제 신뢰도", "AI 피드백", "배포"]):
                h.markdown(f"**{t}**")

        for i, s in enumerate(all_students, start=1):
            r = completed_results.get(s["id"])
            row_key = r["result_id"] if r else f"nr_{s['id']}"
            with st.container(key=f"trow_report_{row_key}"):
                c = st.columns(col_widths)

                has_feedback = bool(r and r.get("ai_feedback_basis"))
                c[0].checkbox(
                    "선택", value=False, key=f"report_bulk_chk_{s['id']}", label_visibility="collapsed",
                    disabled=not has_feedback,
                )
                c[1].markdown(f"<span class='ec-cell-text-center'>{i}</span>", unsafe_allow_html=True)
                c[2].markdown(f"<span class='ec-cell-text-center'>{s['name']}</span>", unsafe_allow_html=True)
                c[3].markdown(f"<span class='ec-cell-text-center'>{s['school'] or '-'}</span>", unsafe_allow_html=True)
                c[4].markdown(f"<span class='ec-cell-text-center'>{s['grade'] or '-'}</span>", unsafe_allow_html=True)
                c[5].markdown(f"<span class='ec-cell-text-center'>{s['class_no'] or '-'}</span>", unsafe_allow_html=True)
                c[6].markdown(f"<span class='ec-cell-text-center'>{s['student_no'] or '-'}</span>", unsafe_allow_html=True)

                if not r:
                    status = db.get_student_retest_status(assignment_id, s["id"])
                    color = status_labels.get(status, "#94A3B8")
                    c[7].markdown(f"<span class='ec-cell-text-center' style='color:{color};'>{status}</span>", unsafe_allow_html=True)
                    c[8].markdown("<span class='ec-cell-text-center' style='color:#94A3B8;'>-</span>", unsafe_allow_html=True)
                    c[9].markdown("<span class='ec-cell-text-center' style='color:#94A3B8;'>-</span>", unsafe_allow_html=True)
                    c[10].markdown("<span class='ec-cell-text-center' style='color:#94A3B8;'>-</span>", unsafe_allow_html=True)
                    continue

                # 과제 이해도 점수 = 정답 개수 / 과제 생성 시 설정한 총 문항수
                c[7].markdown(f"<span class='ec-cell-text-center'>{r['score']}/{total_questions}</span>", unsafe_allow_html=True)

                # 과제 신뢰도 = 정답 비율에 따른 상/중/하 카드
                label = _reliability_label(r["score"], total_questions)
                bg, fg = reliability_style[label]
                c[8].markdown(
                    f"<div style='text-align:center;'><span class='ec-reliability-card' "
                    f"style='background:{bg}; color:{fg};'>{label}</span></div>",
                    unsafe_allow_html=True,
                )

                if c[9].button("확인하기", key=f"aifb_{r['result_id']}", use_container_width=True):
                    go_to("admin_ai_feedback", selected_assignment_id=assignment_id, selected_student_id=r["student_id"])

                # 배포: AI 피드백을 학생에게 공개합니다 (피드백이 아직 없으면 비활성화).
                already_distributed = bool(r.get("feedback_distributed_at"))
                if c[10].button(
                    "✓ 배포됨" if already_distributed else "배포",
                    key=f"report_distribute_{r['result_id']}", use_container_width=True,
                    type="secondary" if already_distributed else "primary",
                    disabled=not has_feedback,
                    help=None if has_feedback else "먼저 [확인하기]에서 AI 피드백을 생성해주세요.",
                ):
                    if already_distributed:
                        db.undistribute_feedback(r["result_id"])
                        st.info(f"{s['name']} 학생에 대한 AI 피드백 배포가 취소되었습니다.")
                    else:
                        db.distribute_feedback(r["result_id"])
                        st.success(f"{s['name']} 학생에게 AI 피드백이 배포되었습니다.")
                    st.rerun()


# ============================================================
# 슬라이드 15: AI 피드백 생성 결과
# ============================================================
def _reliability_label(score, total):
    """정답 비율에 따라 과제 신뢰도를 상/중/하로 분류합니다."""
    if not total:
        return "하"
    ratio = score / total
    if ratio >= 0.67:
        return "상"
    elif ratio >= 0.34:
        return "중"
    return "하"


def _get_wrong_answers(assignment_id, result):
    """AI 피드백 생성을 위해, 학생이 실제로 틀린 문항들을 모읍니다."""
    if not result.get("student_answers"):
        return []
    student_answers = json.loads(result["student_answers"])
    bank = {q["id"]: q for q in db.get_question_bank(assignment_id)}
    wrong = []
    for qid_str, ans in student_answers.items():
        qid = int(qid_str) if isinstance(qid_str, str) else qid_str
        q = bank.get(qid)
        if not q:
            continue
        if not mock_ai.grade_short_answer(ans, q["answer"]):
            wrong.append({"question_text": q["question_text"], "student_answer": ans, "correct_answer": q["answer"]})
    return wrong


def render_ai_feedback_detail():
    render_admin_nav("report")

    assignment_id = st.session_state.get("selected_assignment_id")
    student_id = st.session_state.get("selected_student_id")
    assignment = db.get_assignment(assignment_id)
    result = db.get_retest_result(assignment_id, student_id)

    student = None
    for s in db.list_students():
        if s["id"] == student_id:
            student = s
            break

    if st.button("← 결과 리포트로"):
        go_to("admin_report")

    if student and assignment:
        st.caption(f"{student['name']} · {student['school']} · {student['grade']} {student['class_no']} {student['student_no']}번 · {assignment['title']}")

    ui.page_header("AI 피드백 확인", "AI가 생성한 피드백을 교사가 검토·수정하고, 필요하면 별도 피드백을 남길 수 있습니다.", eyebrow="AI Feedback")

    if not result:
        st.warning("재검사 결과가 없습니다.")
        return

    # AI 피드백이 아직 생성되지 않았다면 실제 AI 호출로 생성
    if not result.get("ai_feedback_basis"):
        reliability_label = _reliability_label(result["score"], result["total"])
        wrong_answers = _get_wrong_answers(assignment_id, result)
        with st.spinner("AI가 재검사 결과를 분석해 피드백을 생성하고 있습니다..."):
            try:
                feedback = ai_engine.generate_ai_feedback(
                    student["name"], assignment["title"], assignment["achievement_standard"],
                    result["score"], result["total"], reliability_label, wrong_answers,
                )
            except ai_engine.AIEngineError as e:
                st.error(str(e))
                return
        db.save_ai_feedback(result["id"], feedback["basis"], feedback["judgement"], feedback["suggestion"])
        result = db.get_retest_result(assignment_id, student_id)  # 갱신된 값 다시 조회
        st.success("AI 피드백이 생성되었습니다. 학생의 '결과 확인' 화면에서도 확인할 수 있습니다.")

    with ui.card():
        st.markdown("**AI가 생성한 피드백**")
        new_basis = st.text_area("1) 문항 생성 근거", value=result["ai_feedback_basis"] or "", height=100)
        new_judgement = st.text_area("2) 이해도 판단 내용 및 근거", value=result["ai_feedback_judgement"] or "", height=100)
        new_suggestion = st.text_area("3) 보충 및 심화 과제 제안", value=result["ai_feedback_suggestion"] or "", height=100)
        if st.button("AI 피드백 저장", use_container_width=True, key="save_ai_feedback_edit"):
            db.save_ai_feedback(result["id"], new_basis, new_judgement, new_suggestion)
            st.success("저장되었습니다.")
            st.rerun()

    with ui.card():
        st.markdown("**교사 추가 피드백**")
        st.caption("AI 피드백과 별도로, 학생에게 직접 남기고 싶은 코멘트를 적어주세요. 학생 화면 하단 '교사 피드백'에 표시됩니다.")
        new_teacher_feedback = st.text_area(
            "교사 피드백", value=result.get("teacher_feedback") or "", height=100, label_visibility="collapsed",
        )
        if st.button("교사 피드백 저장", use_container_width=True, key="save_teacher_feedback_edit"):
            db.save_teacher_feedback(result["id"], new_teacher_feedback)
            st.success("교사 피드백이 저장되었습니다.")
            st.rerun()
