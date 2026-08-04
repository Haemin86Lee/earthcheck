# views/student_views.py
# ------------------------------------------------------------
# 학생용 화면 전체 (기획안 슬라이드 16~22)
#   - 기본 화면 / 과제 제출 / 과제 확인 문항 응시(타이머 시험) / 결과 확인 / 개인정보 수정
# ------------------------------------------------------------

import os
import time
from datetime import datetime, date
import streamlit as st
import database as db
import auth
import mock_ai
import ui
import config
from config import UPLOAD_DIR, MAX_UPLOAD_MB, RETEST_QUESTION_COUNT, RETEST_TIME_LIMIT_SEC
from views.common_views import go_to

# ------------------------------------------------------------
# [데모/화면 확인용 예시 데이터]
# config.DEMO_MODE_STUDENT_USERNAME 계정에서만 사용됩니다.
# 실제 서비스에서는 이 계정도 다른 학생들처럼 실제 AI로 전환해야 합니다.
# (전환 방법은 config.py의 DEMO_MODE_STUDENT_USERNAME 주석을 참고하세요.)
# ------------------------------------------------------------
def _demo_example_questions():
    """'시험 시작하기' 데모용 예시 문항 5개 (실제 AI 호출 없이 화면 확인용)."""
    samples = [
        ("발산형 경계에서 공통적으로 나타나는 현상으로 가장 적절한 것은?",
         ["새로운 지각(암석권)이 생성된다", "기존 지각이 소멸된다", "습곡 산맥이 형성된다", "변성암이 대규모로 생성된다", "지진이 전혀 발생하지 않는다"],
         "새로운 지각(암석권)이 생성된다"),
        ("수렴형 경계 중 해양판과 대륙판이 만나는 경우 주로 형성되는 지형은?",
         ["해구와 호상열도/화산호", "중앙해령", "변환단층", "열곡대", "대륙 분지"],
         "해구와 호상열도/화산호"),
        ("변환형 경계의 대표적인 특징으로 옳은 것은?",
         ["판이 서로 수평으로 어긋나며 이동한다", "새로운 지각이 활발히 생성된다", "마그마가 대량으로 분출한다", "대규모 습곡 산맥이 만들어진다", "해양 지각만 존재한다"],
         "판이 서로 수평으로 어긋나며 이동한다"),
        ("판 경계에서의 지진과 화산 활동에 대한 설명으로 가장 적절한 것은?",
         ["경계 유형에 따라 발생 양상이 다르게 나타난다", "판 경계에서는 지진만 발생하고 화산은 없다", "모든 판 경계에서 동일한 세기로 발생한다", "판 내부에서만 발생한다", "화산 활동은 발산형 경계에서만 일어난다"],
         "경계 유형에 따라 발생 양상이 다르게 나타난다"),
        ("맨틀 대류와 판의 이동 사이의 관계로 옳은 것은?",
         ["맨틀 대류가 판을 움직이는 주요 원동력 중 하나이다", "맨틀 대류와 판 이동은 서로 무관하다", "판은 맨틀 대류와 반대 방향으로만 움직인다", "맨틀 대류는 판의 두께에만 영향을 준다", "맨틀 대류는 해양판에서만 나타난다"],
         "맨틀 대류가 판을 움직이는 주요 원동력 중 하나이다"),
    ]
    return [
        {"id": 900000 + i, "question_text": q, "question_type": "mc", "choices": choices, "answer": answer}
        for i, (q, choices, answer) in enumerate(samples)
    ]


def _demo_example_wrong_answers():
    """'틀린 문항 확인하기' 데모용 예시 오답 1~2개 (화면 확인용)."""
    return [
        {
            "question_text": "변환형 경계의 대표적인 특징으로 옳은 것은?",
            "student_answer": "새로운 지각이 활발히 생성된다",
            "correct_answer": "판이 서로 수평으로 어긋나며 이동한다",
        },
        {
            "question_text": "맨틀 대류와 판의 이동 사이의 관계로 옳은 것은?",
            "student_answer": "맨틀 대류와 판 이동은 서로 무관하다",
            "correct_answer": "맨틀 대류가 판을 움직이는 주요 원동력 중 하나이다",
        },
    ]


def _demo_example_ai_feedback():
    """AI 기반 피드백 데모용 예시 내용 (화면 확인용)."""
    return {
        "basis": "김민준 학생이 제출한 서술형 답안 중 판 경계 유형별 특징을 서술한 부분을 근거로, "
                 "발산형·수렴형·변환형 경계의 개념을 확인하는 문항을 생성했습니다.",
        "judgement": "재검사 5문항 중 3문항 정답으로 신뢰도는 '중' 수준입니다. 발산형·수렴형 경계는 "
                     "정확히 이해했으나, 변환형 경계의 정의와 맨틀 대류가 판 이동의 원동력이라는 점에서 "
                     "혼동이 있는 것으로 보입니다.",
        "suggestion": "변환형 경계(산안드레아스 단층 사례)와 맨틀 대류-판 이동 관계에 대한 보충 자료를 "
                      "먼저 제공하고, 이해 후 판 경계 유형별 지형 비교 심화 과제를 제안합니다.",
    }


STUDENT_NAV_ITEMS = [
    ("home", "📋 과제 확인", "student_home"),
    ("submit", "📤 과제 제출", "student_submit"),
    ("retest", "📝 이해도 확인", "student_retest_intro"),
    ("result", "📊 결과 확인", "student_result"),
    ("profile", "⚙️ 개인정보", "student_profile"),
]


def render_student_nav(active_page):
    """학생 전용 왼쪽 사이드바"""
    user = auth.current_user()
    ui.render_student_sidebar(
        active=active_page,
        user=user,
        items=STUDENT_NAV_ITEMS,
        go_to=go_to,
        on_logout=auth.logout,
    )


def _student_caption(user):
    st.caption(f"{user['school'] or '-'} · {user['grade'] or ''} {user['class_no'] or ''} {user['student_no'] or ''}번 · {user['name']}")


# ============================================================
# 슬라이드 17: 기본 화면 (홈)
# ============================================================
def render_student_home():
    render_student_nav("home")
    ui.page_header("진행 중인 과제", "제출 기한과 참여 현황을 확인하세요.", eyebrow="Home")

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
            with st.container(key=f"trow_home_{a['id']}"):
                c = st.columns(col_widths)
                c[0].markdown(f"<span class='ec-cell-text-center'>{i}</span>", unsafe_allow_html=True)
                with c[1]:
                    # 과제명을 클릭하면 그 과제가 미리 선택된 상태로 '과제 제출' 화면으로 이동합니다.
                    with st.container(key=f"title_link_home_{a['id']}"):
                        if st.button(a["title"], key=f"open_home_{a['id']}"):
                            go_to("student_submit", preselect_assignment_id=a["id"])
                total_score = sum(x["score"] for x in db.get_eval_criteria(a["id"])) or 100
                c[2].markdown(f"<span class='ec-cell-text-center'>{total_score}점</span>", unsafe_allow_html=True)
                c[3].markdown(f"<span class='ec-cell-text-center'>{a['deadline'] or '-'}</span>", unsafe_allow_html=True)
                submitted_count = db.get_submission_count(a["id"])
                c[4].markdown(
                    f"<div style='text-align:center;'>{ui.badge(f'{submitted_count}/{total_students}명', 'info')}</div>",
                    unsafe_allow_html=True,
                )


# ============================================================
# 슬라이드 18: 과제 제출
# ============================================================
def _format_dday(deadline_str):
    """제출 기한 문자열을 근거로 D-day 뱃지 (텍스트, badge종류)를 계산합니다."""
    if not deadline_str:
        return None
    try:
        deadline_dt = datetime.strptime(deadline_str[:16], "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    days_left = (deadline_dt.date() - date.today()).days
    if days_left > 0:
        return f"D-{days_left}", "info"
    elif days_left == 0:
        return "D-DAY", "warning"
    else:
        return f"D+{abs(days_left)} 마감", "danger"


def render_assignment_submit():
    render_student_nav("submit")
    user = auth.current_user()

    ui.page_header("과제 제출", "작성한 답안을 PDF로 저장해 제출하세요.", eyebrow="Submit")

    assignments = db.list_published_assignments()
    if not assignments:
        ui.empty_state("제출할 수 있는 과제가 없습니다.", icon="📤")
        return

    options = {a["title"]: a["id"] for a in assignments}
    option_titles = list(options.keys())
    preselect_id = st.session_state.pop("preselect_assignment_id", None)
    if preselect_id is not None:
        for title, aid in options.items():
            if aid == preselect_id:
                st.session_state["student_submit_assignment_select"] = title
                break

    with st.container(key="assignment_select_box"):
        st.markdown("<div class='ec-select-label'>과제 선택</div>", unsafe_allow_html=True)
        selected_title = st.selectbox(
            "과제 선택", option_titles, key="student_submit_assignment_select", label_visibility="collapsed",
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

        dday = _format_dday(assignment["deadline"])
        if dday:
            dday_text, dday_kind = dday
            st.markdown(
                f"**제출 기한**  \n{assignment['deadline']} &nbsp;&nbsp;{ui.badge(dday_text, dday_kind)}",
                unsafe_allow_html=True,
            )
        else:
            st.write(f"**제출 기한**  \n{assignment['deadline'] or '-'}")

    with ui.card():
        existing = db.get_submission(assignment["id"], user["id"])

        # 제출에 성공하면 업로더를 새 key로 바꿔 선택된 파일을 비웁니다.
        # (그래야 '새로운 파일을 다시 업로드해야' 하는 상태가 자연스럽게 만들어집니다)
        reset_counter = st.session_state.get(f"uploader_reset_{assignment['id']}", 0)
        uploader_key = f"uploader_{assignment['id']}_{reset_counter}"

        # 방금 제출/재제출을 완료한 순간에는 축하 효과를 한 번 보여줍니다.
        just_submitted_key = f"submit_celebrate_{assignment['id']}"
        if st.session_state.pop(just_submitted_key, False):
            st.balloons()

        if existing:
            st.write("다시 제출하려면 새 PDF 파일을 올린 뒤 아래 버튼을 눌러주세요.")
        else:
            st.write("작성한 답안을 PDF로 저장해 제출하세요.")

        # st.file_uploader(): 파일 업로드 위젯. type=["pdf"]로 PDF만 허용, 용량은 서버 설정과 별개로
        # 업로드 후 파일 크기를 직접 검사합니다.
        uploaded_file = st.file_uploader(
            "PDF 파일을 끌어다 놓거나 선택하세요", type=["pdf"], key=uploader_key,
        )

        if uploaded_file is not None:
            size_mb = uploaded_file.size / (1024 * 1024)
            if size_mb > MAX_UPLOAD_MB:
                st.error(f"파일 용량이 {MAX_UPLOAD_MB}MB를 초과합니다. (현재 {size_mb:.1f}MB)")
            else:
                st.success(f"{uploaded_file.name} ({size_mb:.1f}MB) 업로드 준비 완료")

                # 이미 제출한 기록이 있으면 [제출하기](비활성) 옆에 [다시 제출하기]를 나란히 보여줍니다.
                if existing:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.button(
                            "제출하기", use_container_width=True, disabled=True,
                            key=f"submit_disabled_{assignment['id']}",
                            help="이미 제출한 과제가 있습니다. 오른쪽의 '다시 제출하기'를 눌러주세요.",
                        )
                    with col2:
                        clicked = st.button(
                            "다시 제출하기", type="primary", use_container_width=True,
                            key=f"resubmit_btn_{assignment['id']}",
                        )
                else:
                    clicked = st.button(
                        "제출하기", type="primary", use_container_width=True,
                        key=f"submit_btn_{assignment['id']}",
                    )

                if clicked:
                    # 파일명 규칙: {과제ID}_{학년}_{반}_{번호}_{이름}_{제출 순서(버전)}.pdf
                    # 이전에 제출한 파일들을 덮어쓰지 않고, 매 제출마다 새 파일로 순서대로 저장합니다.
                    version = db.count_submissions(assignment["id"], user["id"]) + 1
                    safe_filename = (
                        f"{assignment['id']}_{user['grade'] or ''}_{user['class_no'] or ''}_"
                        f"{user['student_no'] or ''}_{user['name']}_{version}.pdf"
                    )
                    save_path = os.path.join(UPLOAD_DIR, safe_filename)

                    # 업로드된 파일을 실제로 로컬 uploads/ 폴더에 저장합니다.
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    db.create_submission(assignment["id"], user["id"], safe_filename, save_path)

                    st.session_state[f"uploader_reset_{assignment['id']}"] = reset_counter + 1
                    st.session_state[just_submitted_key] = True
                    st.rerun()
        elif existing:
            # '업로드 준비 완료' 메시지가 있던 자리에, 제출 완료 안내를 대신 보여줍니다.
            st.markdown(
                f"""
                <div class="ec-submit-done">
                    ✅ <b>제출이 완료되었습니다!</b> ({existing['pdf_filename']} · {existing['submitted_at']})
                </div>
                """,
                unsafe_allow_html=True,
            )


# ============================================================
# 슬라이드 19: 과제 확인 문항 응시 - 유의사항 안내
# ============================================================
def render_retest_intro():
    render_student_nav("retest")
    user = auth.current_user()

    assignments = db.list_published_assignments()
    if not assignments:
        ui.empty_state("응시할 수 있는 과제가 없습니다.", icon="📝")
        return

    with st.container(key="assignment_select_box"):
        st.markdown("<div class='ec-select-label'>과제 선택</div>", unsafe_allow_html=True)
        options = {a["title"]: a["id"] for a in assignments}
        selected_title = st.selectbox(
            "과제 선택", list(options.keys()), label_visibility="collapsed", key="retest_intro_assignment_select",
        )
        assignment_id = options[selected_title]

    ui.page_header("시험 유의사항", eyebrow="Retest")

    attempt_count = db.count_retest_attempts(assignment_id, user["id"])
    attempts_left = config.RETEST_MAX_ATTEMPTS - attempt_count
    can_start = attempts_left > 0

    with ui.card():
        st.markdown(
            f"""
            - 이 시험은 **내가 제출한 과제 PDF 내용을 바탕으로 AI가 만든** 이해도 확인 문항입니다.
            - 5지선다 객관식으로 총 **N문항**이 출제됩니다 (문항 수는 과제마다 다를 수 있어요).
            - 제한 시간은 **5분**이며, 시간이 종료되면 자동으로 제출됩니다.
            - 시험을 시작하면 다시 처음으로 돌아갈 수 없습니다.
            - 이 과제에 대한 응시 기회는 총 **{config.RETEST_MAX_ATTEMPTS}회**이며, 현재 **{attempts_left}회** 남았습니다.
            """
        )

        if not can_start:
            st.warning(f"이 과제에 대한 응시 기회({config.RETEST_MAX_ATTEMPTS}회)를 모두 사용했습니다.")

        if st.button("시험 시작하기", type="primary", use_container_width=True, disabled=not can_start):
            if not can_start:
                st.error(f"이 과제에 대한 응시 기회({config.RETEST_MAX_ATTEMPTS}회)를 모두 사용했습니다.")
                return
            assignment = db.get_assignment(assignment_id)

            if user["username"] == config.DEMO_MODE_STUDENT_USERNAME:
                # ---- [데모/화면 확인용] ----
                # 이 계정은 실제 AI 호출 없이 예시 문항으로 화면을 바로 확인합니다.
                # 이 학생도 실제 API로 전환하려면 config.DEMO_MODE_STUDENT_USERNAME을
                # None으로 바꾸세요 (그러면 아래 else 분기와 동일하게 동작합니다).
                selected_questions = _demo_example_questions()
            else:
                submission = db.get_submission(assignment_id, user["id"])
                if not submission:
                    st.error("이 과제를 아직 제출하지 않았습니다. 먼저 '과제 제출' 메뉴에서 PDF를 제출해주세요.")
                    return

                # 선생님이 '문항 검토' 화면에서 문항을 검토하고 [배포]를 눌러야만 응시할 수 있습니다.
                if not db.is_distributed(assignment_id, user["id"]):
                    st.error("아직 선생님이 이해도 확인 문항을 배포하지 않았습니다. 배포된 후 다시 시도해주세요.")
                    return

                personalized = db.get_student_generated_questions(assignment_id, user["id"])
                if not personalized:
                    st.error("문항 정보를 찾을 수 없습니다. 선생님께 문의해주세요.")
                    return

                # 시험 화면(render_retest_exam)이 기대하는 문항 형식으로 변환합니다.
                # (문항 생성 근거는 학생 화면에는 노출되지 않고, 문항/보기/정답만 전달됩니다.)
                selected_questions = [
                    {
                        "id": q["question_id"],
                        "question_text": q["question_text"],
                        "question_type": "mc",
                        "choices": q["choices"],
                        "answer": q["answer"],
                    }
                    for q in personalized
                ]

            # 시험 상태를 session_state에 저장 (문항 목록, 시작시각, 답안 등)
            st.session_state["exam_assignment_id"] = assignment_id
            st.session_state["exam_questions"] = selected_questions
            st.session_state["exam_answers"] = {}
            st.session_state["exam_started_at"] = time.time()
            st.session_state["exam_current_idx"] = 0
            go_to("student_retest_exam")

    # ---- 응시 기록 (결과가 아닌, 몇 회차에 언제 응시했는지만) : 카드 바깥, 회색 글씨, 박스 없음 ----
    past_attempts = db.list_retest_attempts(assignment_id, user["id"])
    if past_attempts:
        lines = "<br>".join(
            f"{i + 1}회차 응시 · {att['completed_at']}" for i, att in enumerate(past_attempts)
        )
        st.markdown(
            f"<div style='color:#94A3B8; font-size:0.85rem; margin-top:0.6rem;'>{lines}</div>",
            unsafe_allow_html=True,
        )


# ============================================================
# 슬라이드 20: 과제 확인 문항 응시 - 시험(타이머) 화면
# ============================================================
def render_retest_exam():
    render_student_nav("retest")
    user = auth.current_user()

    questions = st.session_state.get("exam_questions")
    if not questions:
        st.warning("진행 중인 시험이 없습니다. 유의사항 화면에서 시험을 시작해주세요.")
        return

    idx = st.session_state.get("exam_current_idx", 0)
    total = len(questions)

    # ---- 남은 시간 계산 (서버 기준 - 자동 제출 판단에 사용) ----
    elapsed = time.time() - st.session_state["exam_started_at"]
    remaining = max(0, RETEST_TIME_LIMIT_SEC - elapsed)

    with ui.card():
        col_progress, col_timer = st.columns([3, 1])
        with col_progress:
            st.markdown(f"**이해도 확인 문항 · {idx + 1} / {total}**")
            st.progress((idx) / total if total else 0)
        with col_timer:
            # 문항 이동 여부와 상관없이 1초 단위로 실제로 줄어드는 모습을 보여주기 위해
            # 화면에는 JS로 매초 갱신되는 타이머를 표시합니다. (자동 제출 여부는 서버에서 그대로 판단합니다)
            st.iframe(
                f"""
                <div id="ec-exam-timer" style="
                    display:inline-block; float:right; padding:0.22rem 0.65rem;
                    border-radius:999px; font-size:0.78rem; font-weight:700;
                    font-family:'Pretendard Variable','Pretendard',-apple-system,sans-serif;
                    background:#DCFCE7; color:#15803D;">
                    ⏱ 남은 시간 --:--
                </div>
                <script>
                let remaining = {int(remaining)};
                const el = document.getElementById('ec-exam-timer');
                function render() {{
                    const m = String(Math.floor(remaining / 60)).padStart(2, '0');
                    const s = String(remaining % 60).padStart(2, '0');
                    el.innerText = '⏱ 남은 시간 ' + m + ':' + s;
                    if (remaining > 180) {{
                        el.style.background = '#DCFCE7'; el.style.color = '#15803D';
                    }} else if (remaining > 60) {{
                        el.style.background = '#FEF3C7'; el.style.color = '#B45309';
                    }} else {{
                        el.style.background = '#F1F5F9'; el.style.color = '#64748B';
                    }}
                }}
                render();
                const timer = setInterval(function() {{
                    if (remaining > 0) {{ remaining -= 1; render(); }}
                    else {{ clearInterval(timer); }}
                }}, 1000);
                </script>
                """,
                height=36,
            )

    if remaining <= 0:
        st.warning("제한 시간이 종료되어 자동으로 제출되었습니다.")
        _submit_exam(user)
        return

    question = questions[idx]
    is_last = idx == total - 1
    with ui.card():
        st.markdown(f"#### {question['question_text']}")

        answer_key = f"exam_ans_{question['id']}"
        if question["question_type"] == "mc" and question.get("choices"):
            # 객관식 문항: choices가 JSON 문자열이면 리스트로 변환
            import json as _json
            choices = question["choices"] if isinstance(question["choices"], list) else _json.loads(question["choices"])
            answer = st.radio("보기", choices, key=answer_key, label_visibility="collapsed")
        else:
            # 단답형 문항
            answer = st.text_input("답안을 입력하세요", key=answer_key)

        col_prev, col_next = st.columns(2)
        with col_prev:
            if idx > 0 and st.button("이전 문항", use_container_width=True):
                st.session_state["exam_answers"][question["id"]] = answer
                st.session_state["exam_current_idx"] -= 1
                st.rerun()
        with col_next:
            if is_last:
                # 마지막 문항의 [답안 제출]은 [다음 문항]과 구분되도록 다른 색으로 표시합니다.
                with st.container(key="exam_submit_btn"):
                    clicked = st.button("답안 제출", use_container_width=True)
            else:
                clicked = st.button("다음 문항", type="primary", use_container_width=True)

            if clicked:
                st.session_state["exam_answers"][question["id"]] = answer
                if not is_last:
                    st.session_state["exam_current_idx"] += 1
                    st.rerun()
                else:
                    _submit_exam(user)

    if is_last:
        st.caption("💡 답안 제출 버튼을 누르면 결과 확인 페이지로 바로 넘어갑니다.")


def _submit_exam(user):
    """시험 종료 처리: 채점 후 결과 저장하고 결과 화면으로 이동"""
    questions = st.session_state["exam_questions"]
    answers = st.session_state["exam_answers"]
    assignment_id = st.session_state["exam_assignment_id"]

    # 각 문항을 채점 (mock_ai.grade_short_answer 사용)
    correct_count = 0
    for q in questions:
        student_ans = answers.get(q["id"], "")
        if mock_ai.grade_short_answer(student_ans, q["answer"]):
            correct_count += 1

    total = len(questions)
    reliability = round((correct_count / total) * 100) if total else 0

    db.save_retest_result(assignment_id, user["id"], correct_count, total, reliability, answers)

    # 시험 관련 session_state 정리
    for key in ["exam_questions", "exam_answers", "exam_started_at", "exam_current_idx", "exam_assignment_id"]:
        if key in st.session_state:
            del st.session_state[key]

    go_to("student_result")


# ============================================================
# 슬라이드 21: 결과 확인
# ============================================================
def render_result_view():
    render_student_nav("result")
    user = auth.current_user()

    assignments = db.list_published_assignments()
    if not assignments:
        ui.empty_state("결과를 확인할 과제가 없습니다.", icon="📊")
        return

    with st.container(key="assignment_select_box"):
        st.markdown("<div class='ec-select-label'>과제 선택</div>", unsafe_allow_html=True)
        options = {a["title"]: a["id"] for a in assignments}
        selected_title = st.selectbox(
            "과제 선택", list(options.keys()), label_visibility="collapsed", key="result_view_assignment_select",
        )
        assignment_id = options[selected_title]

    attempts = db.list_retest_attempts(assignment_id, user["id"])

    ui.page_header("과제 이해도 검사 점수", eyebrow="Result")
    if not attempts:
        ui.empty_state("아직 재검사를 완료하지 않았습니다. '이해도 확인' 메뉴에서 시험을 진행해주세요.", icon="🧪")
        return

    # 학생이 실제로 결과를 열람한 시각을 기록합니다 (교사의 '제출 현황' 화면에서 사용, 최신 회차 기준).
    db.mark_result_viewed(assignment_id, user["id"])

    latest_result = attempts[-1]  # AI 피드백은 항상 가장 최근 응시를 기준으로 합니다.

    # ---- 회차별 점수 카드 (클릭하면 아래 '틀린 문항'이 그 회차 기준으로 바뀝니다) ----
    select_key = f"selected_attempt_{assignment_id}"
    if select_key not in st.session_state:
        st.session_state[select_key] = latest_result["id"]

    with ui.card():
        st.markdown("**응시 회차별 점수**")
        cols = st.columns(len(attempts))
        for i, (col, att) in enumerate(zip(cols, attempts)):
            with col:
                is_selected = st.session_state[select_key] == att["id"]
                with st.container(key=f"attempt_card_{att['id']}"):
                    st.markdown(
                        f"<div class='ec-attempt-round'>{i + 1}회차</div>"
                        f"<div class='ec-attempt-score'>{att['score']}/{att['total']}</div>"
                        f"<div class='ec-attempt-date'>{att['completed_at']}</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "✓ 선택됨" if is_selected else "보기",
                        key=f"attempt_select_{att['id']}", use_container_width=True,
                        type="primary" if is_selected else "secondary",
                    ):
                        st.session_state[select_key] = att["id"]
                        st.rerun()

        selected_result = next((a for a in attempts if a["id"] == st.session_state[select_key]), latest_result)

        with st.expander("틀린 문항 확인하기"):
            if user["username"] == config.DEMO_MODE_STUDENT_USERNAME:
                # ---- [데모/화면 확인용] ----
                # 이 계정은 예시 오답 데이터를 보여줍니다. 실제 전환 방법은
                # config.py의 DEMO_MODE_STUDENT_USERNAME 주석을 참고하세요.
                for ex in _demo_example_wrong_answers():
                    st.write(f"❌ **{ex['question_text']}**")
                    st.markdown(f"<span class='ec-wrong-my-answer'>내 답: {ex['student_answer']}</span>", unsafe_allow_html=True)
                    st.markdown(f"<span class='ec-wrong-correct-answer'>정답: {ex['correct_answer']}</span>", unsafe_allow_html=True)
            else:
                import json as _json
                student_answers = _json.loads(selected_result["student_answers"]) if selected_result["student_answers"] else {}
                # 이 학생에게 실제로 생성/배정된 맞춤 문항을 기준으로, 선택한 회차의 오답을 판별합니다.
                personalized = db.get_student_generated_questions(assignment_id, user["id"])
                bank = {q["question_id"]: q for q in personalized}
                for qid_str, ans in student_answers.items():
                    qid = int(qid_str) if isinstance(qid_str, str) else qid_str
                    q = bank.get(qid)
                    if not q:
                        continue
                    is_correct = mock_ai.grade_short_answer(ans, q["answer"])
                    if not is_correct:
                        st.write(f"❌ **{q['question_text']}**")
                        st.markdown(f"<span class='ec-wrong-my-answer'>내 답: {ans or '(미응답)'}</span>", unsafe_allow_html=True)
                        st.markdown(f"<span class='ec-wrong-correct-answer'>정답: {q['answer']}</span>", unsafe_allow_html=True)

    with st.container(key="ai_feedback_card"):
        st.markdown("#### 🤖 AI 기반 피드백")
        st.caption("가장 최근 응시 결과를 기준으로, 이 학생이 제출한 과제 분석과 이해도 재검사 응시 결과를 바탕으로 AI가 작성했습니다.")

        if user["username"] == config.DEMO_MODE_STUDENT_USERNAME:
            # ---- [데모/화면 확인용] ----
            feedback = _demo_example_ai_feedback()
            st.write(f"1) 문항 생성 근거 — {feedback['basis']}")
            st.write(f"2) 이해도 판단 — {feedback['judgement']}")
            st.write(f"3) 보충·심화 제안 — {feedback['suggestion']}")
            has_feedback = True
        else:
            # 선생님이 '결과 리포트'에서 [배포]를 눌러야만 학생 화면에 AI 피드백이 표시됩니다.
            has_feedback = bool(latest_result.get("ai_feedback_basis")) and bool(latest_result.get("feedback_distributed_at"))
            if has_feedback:
                st.write(f"1) 문항 생성 근거 — {latest_result['ai_feedback_basis']}")
                st.write(f"2) 이해도 판단 — {latest_result['ai_feedback_judgement']}")
                st.write(f"3) 보충·심화 제안 — {latest_result['ai_feedback_suggestion']}")

        if has_feedback:
            st.write("")
            st.markdown("**추가 과제 제출 (선택)**")
            st.caption("위 보충·심화 제안에 따라 작성한 과제가 있다면 PDF로 제출할 수 있습니다.")
            existing_extra = db.get_extra_submission(assignment_id, user["id"])
            if existing_extra:
                st.info(f"이미 제출한 추가 과제가 있습니다: {existing_extra['pdf_filename']} ({existing_extra['submitted_at']})")
            extra_reset = st.session_state.get(f"extra_uploader_reset_{assignment_id}", 0)
            extra_file = st.file_uploader(
                "추가 과제 PDF", type=["pdf"], key=f"extra_upload_{assignment_id}_{extra_reset}",
            )
            if st.button(
                "추가 과제 제출하기", key=f"extra_submit_{assignment_id}",
                type="primary", use_container_width=True, disabled=extra_file is None,
            ):
                # 파일명 규칙: {과제ID}_{학년}_{반}_{번호}_{이름}_{추가과제 제출 순서}.pdf
                extra_version = db.count_extra_submissions(assignment_id, user["id"]) + 1
                safe_filename = (
                    f"{assignment_id}_{user['grade'] or ''}_{user['class_no'] or ''}_"
                    f"{user['student_no'] or ''}_{user['name']}_{extra_version}.pdf"
                )
                save_path = os.path.join(UPLOAD_DIR, safe_filename)
                with open(save_path, "wb") as f:
                    f.write(extra_file.getbuffer())
                db.create_extra_submission(assignment_id, user["id"], safe_filename, save_path)
                st.session_state[f"extra_uploader_reset_{assignment_id}"] = extra_reset + 1
                st.success("추가 과제가 제출되었습니다!")
                st.rerun()
        else:
            if latest_result.get("ai_feedback_basis"):
                st.caption("AI 피드백이 생성되었지만, 아직 선생님이 배포하지 않았습니다.")
            else:
                st.caption("아직 선생님이 AI 피드백을 생성하지 않았습니다.")

    with ui.card():
        st.markdown("#### 교사 피드백")
        st.write(latest_result.get("teacher_feedback") or "아직 등록된 교사 피드백이 없습니다.")


# ============================================================
# 슬라이드 22: 개인정보 수정
# ============================================================
def render_profile_edit():
    render_student_nav("profile")
    user = auth.current_user()

    ui.page_header("개인정보 수정", eyebrow="Profile")

    with ui.card():
        st.selectbox("구분", ["학생"], disabled=True)
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
                import auth as auth_module
                db.update_user_password(user["id"], auth_module.hash_password(new_password))
                st.success("비밀번호가 변경되었습니다.")

        st.text_input("학교명", value=user["school"] or "", disabled=True)
        c1, c2, c3 = st.columns(3)
        c1.text_input("학년", value=user["grade"] or "", disabled=True)
        c2.text_input("반", value=user["class_no"] or "", disabled=True)
        c3.text_input("번호", value=user["student_no"] or "", disabled=True)
        st.text_input("학생명", value=user["name"], disabled=True)

        st.caption("비밀번호를 제외한 다른 정보 수정은 담임 교사에게 문의해 주세요.")
