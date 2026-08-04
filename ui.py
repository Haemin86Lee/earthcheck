# ui.py
# ------------------------------------------------------------
# EarthCheck 전체 화면에서 공통으로 사용하는 "디자인 시스템" 모듈입니다.
#   - inject_css()      : 전역 CSS(폰트/색상/버튼/카드/뱃지 등) 주입
#   - render_topnav()    : 상단 고정 네비게이션 바 (로그인 전/교사/학생 공용)
#   - page_header()      : 화면 상단 타이틀 + 부제목 블록
#   - card() / badge() / empty_state() 등 재사용 UI 조각들
# 화면(views) 코드는 이 모듈의 함수만 불러다 쓰면 되고, CSS는 한 번만 신경 쓰면 됩니다.
# ------------------------------------------------------------

import itertools
import streamlit as st

_card_counter = itertools.count()

PRIMARY = "#2563EB"       # 메인 브랜드 컬러 (인디고 블루)
PRIMARY_DARK = "#1D4ED8"
ACCENT = "#0D9488"        # 포인트 컬러 (틸/지구과학 느낌의 청록)
SUCCESS = "#16A34A"
WARNING = "#D97706"
DANGER = "#DC2626"
INK = "#0F172A"
MUTED = "#64748B"
BORDER = "#E2E8F0"
SURFACE = "#FFFFFF"
BG = "#F5F7FB"


def inject_css(show_sidebar=False):
    """
    앱 전체에 한 번만 호출하는 전역 스타일 주입 함수.
    show_sidebar=True 이면(학생 화면) 왼쪽 사이드바를 보여주고,
    그 외(비회원/교사 화면)에는 기존처럼 사이드바를 숨깁니다.
    """
    sidebar_display = "block" if show_sidebar else "none"
    st.markdown(
        f"""
        <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.css');

        html, body, [class*="css"] {{
            font-family: 'Pretendard Variable', 'Pretendard', -apple-system, BlinkMacSystemFont,
                         'Segoe UI', system-ui, sans-serif !important;
        }}

        /* ---------- 배경 & 기본 레이아웃 ---------- */
        .stApp {{
            background: {BG};
        }}
        .block-container {{
            padding-top: 1.6rem !important;
            padding-bottom: 3rem !important;
            max-width: 1440px;
        }}

        /* ---------- Streamlit 기본 크롬 숨기기 ---------- */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header[data-testid="stHeader"] {{
            background: transparent;
            height: 0;
            /* 클릭 이벤트를 절대 가로채지 않도록 완전히 무시시킴
               (fixed 방식 대신 sticky를 쓰더라도, 혹시 남아있는 헤더 레이어가
               우리 네비게이션 바 버튼 클릭을 가로채는 것을 원천 차단합니다) */
            pointer-events: none;
        }}
        div[data-testid="stToolbar"] {{visibility: hidden;}}
        div[data-testid="stDecoration"] {{visibility: hidden;}}
        section[data-testid="stSidebar"] {{display: {sidebar_display};}}

        /* ---------- 학생 전용 왼쪽 사이드바 ---------- */
        section[data-testid="stSidebar"] {{
            background: {SURFACE};
            border-right: 1px solid {BORDER};
            width: 260px;
            overflow-x: hidden;
        }}
        /* 사이드바 폭을 260px로 맞추고, 안쪽 콘텐츠를 화면 맨 위까지 바짝 당깁니다 (타이틀이 최상단에 오도록) */
        section[data-testid="stSidebar"] > div:first-child {{
            width: 260px;
            padding-top: 0;
            overflow-x: hidden;
            box-sizing: border-box;
        }}
        section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {{
            padding-top: 0;
            overflow-x: hidden;
            box-sizing: border-box;
        }}
        section[data-testid="stSidebar"] * {{
            max-width: 100%;
            box-sizing: border-box;
        }}
        section[data-testid="stSidebar"] .stButton > button {{
            border: none;
            background: transparent;
            color: {INK};
            font-weight: 600;
            font-size: 0.95rem;
            text-align: left;
            justify-content: flex-start;
            padding: 0.55rem 0.8rem;
            border-radius: 10px;
            box-shadow: none;
        }}
        section[data-testid="stSidebar"] .stButton > button:hover {{
            background: #EEF2FF;
            color: {PRIMARY_DARK};
        }}
        section[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
            background: #EEF2FF;
            color: {PRIMARY_DARK};
            box-shadow: none;
        }}
        .ec-sidebar-badge {{
            display: inline-block;
            background: linear-gradient(90deg, {PRIMARY}, {ACCENT});
            color: white;
            font-weight: 700;
            font-size: 0.52rem;
            letter-spacing: -0.01em;
            padding: 0.18rem 0.4rem;
            border-radius: 999px;
            margin-bottom: 0.5rem;
            white-space: nowrap;
            max-width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
            box-sizing: border-box;
        }}
        .ec-sidebar-title {{
            font-size: 1.4rem;
            font-weight: 800;
            color: {INK};
            padding: 0 0.2rem 0.6rem 0.2rem;
            user-select: none;
        }}
        .ec-sidebar-userinfo {{
            background: #F8FAFC;
            border: 1px solid {BORDER};
            border-radius: 12px;
            padding: 0.8rem 0.9rem;
            margin-bottom: 1rem;
            font-size: 0.9rem;
            line-height: 1.75;
            color: {INK};
        }}
        .ec-sidebar-userinfo .ec-welcome {{
            margin-top: 0.4rem;
            color: {ACCENT};
            font-weight: 700;
        }}
        .ec-sidebar-divider {{
            height: 1px;
            background: {BORDER};
            margin: 0.7rem 0.2rem 0.7rem 0.2rem;
        }}


        /* 이전에는 position:fixed로 화면에 완전히 띄웠으나, Streamlit 내부 레이아웃
           구조와 좌표계가 어긋나 버튼이 "보이지만 클릭되지 않는" 문제가 있었습니다.
           position:sticky는 문서 흐름 안에 정상적으로 자리 잡으면서 스크롤 시에만
           상단에 붙기 때문에 클릭 좌표가 어긋나지 않고 항상 정상적으로 클릭됩니다. */
        div.st-key-topnav {{
            position: sticky;
            top: 0;
            z-index: 100;
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 14px;
            box-shadow: 0 2px 12px rgba(15, 23, 42, 0.04);
            padding: 0.55rem 1.4rem;
            margin-bottom: 1.4rem;
        }}
        div.st-key-topnav div[data-testid="stHorizontalBlock"] {{
            align-items: center;
            gap: 0.15rem;
        }}
        div.st-key-topnav .stButton > button {{
            border: none;
            background: transparent;
            color: {MUTED};
            font-weight: 600;
            font-size: 0.88rem;
            padding: 0.45rem 0.6rem;
            border-radius: 8px;
            box-shadow: none;
            white-space: nowrap;
        }}
        div.st-key-topnav .stButton > button p {{
            white-space: nowrap;
        }}
        div.st-key-topnav .stButton > button:hover {{
            background: #EEF2FF;
            color: {PRIMARY_DARK};
        }}
        div.st-key-topnav .stButton > button[kind="primary"] {{
            background: #EEF2FF;
            color: {PRIMARY_DARK};
            box-shadow: none;
        }}

        /* ---------- 버튼 공통 ---------- */
        .stButton > button {{
            border-radius: 10px;
            font-weight: 600;
            border: 1px solid {BORDER};
            transition: all 0.15s ease;
        }}
        .stButton > button[kind="primary"] {{
            background: {PRIMARY};
            border: none;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.28);
        }}
        .stButton > button[kind="primary"]:hover {{
            background: {PRIMARY_DARK};
            box-shadow: 0 6px 18px rgba(37, 99, 235, 0.36);
        }}
        .stButton > button[kind="secondary"]:hover {{
            border-color: {PRIMARY};
            color: {PRIMARY_DARK};
        }}
        .stDownloadButton > button, .stFormSubmitButton > button {{
            border-radius: 10px;
            font-weight: 600;
        }}

        /* ---------- 입력 위젯 ---------- */
        .stTextInput input, .stTextArea textarea, .stNumberInput input,
        .stDateInput input, .stTimeInput input, div[data-baseweb="select"] {{
            border-radius: 10px !important;
        }}
        .stTextInput input:focus, .stTextArea textarea:focus {{
            border-color: {PRIMARY} !important;
            box-shadow: 0 0 0 1px {PRIMARY} !important;
        }}

        /* ---------- 카드 ---------- */
        div[class*="st-key-card_"], .ec-card {{
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 16px;
            padding: 1.4rem 1.6rem;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
            margin-bottom: 1rem;
        }}
        div[class*="st-key-row_"] {{
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 12px;
            padding: 0.75rem 1.1rem;
            margin-bottom: 0.55rem;
            transition: box-shadow 0.15s ease, border-color 0.15s ease;
        }}
        div[class*="st-key-row_"]:hover {{
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.07);
            border-color: #C7D2FE;
        }}

        /* ---------- 단일 테이블(하나의 칼럼)로 보이는 목록 ---------- */
        div[class*="st-key-students_table"] {{
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 16px;
            padding: 0.4rem 1.2rem;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
            margin-bottom: 1rem;
        }}
        div[class*="st-key-trow_"] {{
            padding: 0.7rem 0;
            border-bottom: 1px solid {BORDER};
        }}
        div[class*="st-key-trow_"]:last-child {{
            border-bottom: none;
        }}
        div[class*="st-key-trow_"]:hover {{
            background: #F8FAFC;
        }}

        /* ---------- 평가요소/채점기준 테이블 (과제 생성 화면), 과제 조회 표 ---------- */
        div[class*="st-key-students_table"], div[class*="st-key-criteria_table"], div[class*="st-key-assignments_table"], div[class*="st-key-submission_status_table"], div[class*="st-key-review_table"], div[class*="st-key-report_table"], div[class*="st-key-review_detail_table"], div[class*="st-key-review_reason_table"], div[class*="st-key-student_home_table"], div[class*="st-key-teachers_table"] {{
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 16px;
            padding: 0.4rem 1.2rem 1rem 1.2rem;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
            margin-bottom: 1rem;
        }}

        /* '과제 선택' 라벨/콤보박스를 더 크고 눈에 띄게 (라벨과 동일한 글자 크기, 굵게는 X) */
        .ec-select-label {{
            font-size: 1.15rem;
            font-weight: 700;
            color: {INK};
            margin: 0.2rem 0 0.5rem 0;
        }}
        div[class*="st-key-assignment_select_box"] div[data-baseweb="select"] {{
            background: {SURFACE};
            border-radius: 10px;
        }}
        div[class*="st-key-assignment_select_box"] div[data-baseweb="select"] div {{
            background: {SURFACE} !important;
        }}
        div[class*="st-key-assignment_select_box"] div[data-baseweb="select"] {{
            border: 1px solid {BORDER};
        }}
        div[class*="st-key-assignment_select_box"] div[data-baseweb="select"] * {{
            font-size: 1.15rem !important;
            font-weight: 400 !important;
        }}
        /* 제출현황 표: 완료(시각)는 초록, 미완료는 빨강 계열 (가운데 정렬, 굵게 아님, 다른 셀과 동일한 크기) */
        .ec-status-done {{
            color: #15803D;
            font-weight: 400;
            font-size: 0.92rem;
            text-align: center;
            display: block;
        }}
        .ec-status-pending {{
            color: #DC2626;
            font-weight: 400;
            font-size: 0.92rem;
            text-align: center;
            display: block;
        }}
        /* 제출현황 표의 내용행 공통 셀 스타일: 크기 통일, 굵게 아님, 가운데 정렬 */
        .ec-cell-text-center {{
            font-size: 0.92rem;
            font-weight: 400;
            color: {INK};
            text-align: center;
            display: block;
        }}

        /* 과제 조회: 과제명을 '상세보기' 버튼 대신 링크처럼 보이게 */
        div[class*="st-key-title_link_"] .stButton > button {{
            border: none;
            background: transparent;
            box-shadow: none;
            color: {INK};
            font-weight: 700;
            padding: 0.1rem 0;
            text-align: left;
            justify-content: flex-start;
        }}
        div[class*="st-key-title_link_"] .stButton > button p {{
            font-weight: 700;
        }}
        div[class*="st-key-title_link_"] .stButton > button:hover {{
            text-decoration: underline;
            color: {PRIMARY_DARK};
        }}

        /* 과제 조회 표 / 제출 현황 표 / 학생 관리 표: 헤더행과 내용행을 밑줄로 구분 */
        div[class*="st-key-assign_header_row"], div[class*="st-key-status_header_row"], div[class*="st-key-students_header_row"], div[class*="st-key-review_header_row"], div[class*="st-key-report_header_row"], div[class*="st-key-review_detail_header_row"], div[class*="st-key-review_reason_header_row"], div[class*="st-key-student_home_header_row"], div[class*="st-key-teachers_header_row"] {{
            border-bottom: 2px solid {BORDER};
            padding-bottom: 0.5rem;
            margin-bottom: 0.2rem;
        }}
        div[class*="st-key-status_header_row"] p, div[class*="st-key-students_header_row"] p, div[class*="st-key-review_header_row"] p, div[class*="st-key-report_header_row"] p, div[class*="st-key-review_detail_header_row"] p, div[class*="st-key-review_reason_header_row"] p, div[class*="st-key-student_home_header_row"] p, div[class*="st-key-teachers_header_row"] p {{
            text-align: center;
        }}
        /* 문항보기/근거보기 수정 패널 살짝 구분 */
        div[class*="st-key-review_edit_panel_"] {{
            background: #F8FAFC;
            border: 1px dashed {BORDER};
            border-radius: 10px;
            padding: 0.8rem;
            margin: 0.4rem 0 0.8rem 0;
        }}
        /* 내용 행 글자 크기를 통일 (성취기준만 조금 더 작게) */
        .ec-cell-text {{
            font-size: 0.92rem;
            color: {INK};
        }}
        .ec-cell-text-sm {{
            font-size: 0.8rem;
            color: {MUTED};
            line-height: 1.4;
        }}
        /* 성취기준 팝오버 버튼: 배포하기/배포중/배포취소 버튼과 크기·모양을 통일 */
        div[class*="st-key-criteria_popover_"] div[data-testid="stPopover"] button {{
            width: 100%;
            border-radius: 10px;
            font-weight: 600;
            border: 1px solid {BORDER};
        }}

        div[class*="st-key-status_badge_"] .stButton > button:disabled {{
            background: #DCFCE7;
            color: #15803D;
            border: none;
            opacity: 1;
            cursor: default;
        }}
        /* 순서 변경 ▲▼ 버튼 영역: 표 아래 왼쪽에 붙여서 배치 */
        div[class*="st-key-reorder_controls"] {{
            margin-top: 0.6rem;
        }}
        div[class*="st-key-reorder_controls"] .stButton > button {{
            padding: 0.3rem 0;
        }}
        /* 평가요소 하나 = 카드 한 장 */
        div[class*="st-key-group_card_"] {{
            background: #FAFBFC;
            border: 1px solid {BORDER};
            border-radius: 12px;
            padding: 0.8rem 0.9rem 0.5rem 0.9rem;
            margin: 0.7rem 0;
        }}
        /* 평가요소칸이 오른쪽 배점/채점기준 행 전체 높이만큼 늘어나
           셀 병합처럼 보이도록, 이 행의 두 컬럼을 서로 높이를 맞춥니다. */
        div[class*="st-key-group_row_"] > div[data-testid="stHorizontalBlock"] {{
            align-items: stretch;
        }}
        div[class*="st-key-group_row_"] div[data-testid="column"] {{
            height: 100%;
        }}
        div[class*="st-key-group_row_"] div[data-testid="column"] > div {{
            height: 100%;
        }}
        div[class*="st-key-elem_cell_"] {{
            height: 100%;
            min-height: 2.6rem;
            display: flex;
            align-items: stretch;
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 10px;
            padding: 0.2rem;
        }}
        div[class*="st-key-elem_cell_"] .stTextInput {{
            width: 100%;
            display: flex;
        }}
        div[class*="st-key-elem_cell_"] .stTextInput > div {{
            width: 100%;
            height: 100%;
        }}
        div[class*="st-key-elem_cell_"] input {{
            height: 100%;
        }}

        /* 과제 생성 화면: 단원명/성취기준/과제명/평가문항/핵심개념 라벨 글자 크기를 통일 */
        .ec-field-label {{
            font-size: 0.95rem;
            font-weight: 600;
            color: {INK};
            margin: 0.3rem 0 0.35rem 0;
        }}
        /* 단원명 카드형 선택 버튼 */
        div[class*="st-key-unit_cards"] .stButton > button {{
            padding: 0.9rem 0.6rem;
            font-weight: 700;
            white-space: normal;
        }}

        /* ---------- 페이지 헤더 ---------- */
        .ec-eyebrow {{
            color: {ACCENT};
            font-weight: 700;
            font-size: 0.82rem;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-bottom: 0.2rem;
        }}
        .ec-title {{
            font-size: 1.9rem;
            font-weight: 800;
            color: {INK};
            margin: 0 0 0.15rem 0;
        }}
        .ec-subtitle {{
            color: {MUTED};
            font-size: 0.98rem;
            margin-bottom: 1.1rem;
        }}

        /* ---------- 뱃지 ---------- */
        .ec-badge {{
            display: inline-block;
            padding: 0.22rem 0.65rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
        }}
        .ec-badge-success {{ background: #DCFCE7; color: #15803D; }}
        .ec-badge-warning {{ background: #FEF3C7; color: #B45309; }}
        .ec-badge-danger  {{ background: #FEE2E2; color: #B91C1C; }}
        .ec-badge-muted   {{ background: #F1F5F9; color: {MUTED}; }}
        .ec-badge-info    {{ background: #E0E7FF; color: {PRIMARY_DARK}; }}
        .ec-reliability-card {{
            display: inline-block;
            padding: 0.35rem 1rem;
            border-radius: 10px;
            font-size: 0.95rem;
            font-weight: 700;
        }}

        /* 과제 제출: '업로드 준비 완료' 자리에 나타나는 제출 완료 안내 */
        .ec-submit-done {{
            background: #DCFCE7;
            border: 1px solid #86EFAC;
            color: #15803D;
            border-radius: 10px;
            padding: 0.75rem 1rem;
            font-size: 0.92rem;
            line-height: 1.6;
        }}

        /* AI 기반 피드백 카드: 눈이 편안한 연하늘색 계열 */
        div[class*="st-key-ai_feedback_card"] {{
            background: #EFF6FF;
            border: 1px solid #BFDBFE;
            border-radius: 16px;
            padding: 1.4rem 1.6rem;
            margin-bottom: 1rem;
        }}

        /* 시험 응시: 마지막 문항의 [답안 제출] 버튼을 [다음 문항]과 다른 색으로 */
        div[class*="st-key-exam_submit_btn"] .stButton > button {{
            background: #7C3AED;
            color: white;
            border: none;
            box-shadow: 0 4px 14px rgba(124, 58, 237, 0.28);
        }}
        div[class*="st-key-exam_submit_btn"] .stButton > button:hover {{
            background: #6D28D9;
            color: white;
            box-shadow: 0 6px 18px rgba(124, 58, 237, 0.36);
        }}

        /* 응시 회차 카드 (결과 확인 화면) */
        div[class*="st-key-attempt_card_"] {{
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 12px;
            padding: 0.7rem 0.5rem 0.4rem 0.5rem;
            text-align: center;
            margin-bottom: 0.4rem;
        }}
        .ec-attempt-round {{
            font-size: 0.8rem;
            color: {MUTED};
            font-weight: 700;
        }}
        .ec-attempt-score {{
            font-size: 1.3rem;
            font-weight: 800;
            color: {INK};
            margin: 0.15rem 0;
        }}
        .ec-attempt-date {{
            font-size: 0.7rem;
            color: {MUTED};
        }}

        /* 회원관리: 수정 패널 */
        div[class*="st-key-member_edit_panel_"] {{
            background: #F8FAFC;
            border: 1px dashed {BORDER};
            border-radius: 10px;
            padding: 0.9rem;
            margin: 0.4rem 0 0.9rem 0;
        }}

        /* 문항검토 / 결과리포트: 일괄 배포 버튼 글자·아이콘을 항상 흰색으로 (비활성 상태 포함),
           배경색은 다른 버튼들과 동일한 기본 파란색을 그대로 사용합니다. */
        div[class*="st-key-bulk_distribute_wrap"] .stButton > button,
        div[class*="st-key-report_bulk_distribute_wrap"] .stButton > button {{
            color: #FFFFFF !important;
        }}
        div[class*="st-key-bulk_distribute_wrap"] .stButton > button p,
        div[class*="st-key-report_bulk_distribute_wrap"] .stButton > button p,
        div[class*="st-key-bulk_distribute_wrap"] .stButton > button span,
        div[class*="st-key-report_bulk_distribute_wrap"] .stButton > button span {{
            color: #FFFFFF !important;
        }}

        /* 문항검토 / 결과리포트: [배포] → [✓ 배포됨](연두색, 다시 누르면 배포 취소) */
        div[class*="st-key-distribute_"] .stButton > button:not([kind="primary"]),
        div[class*="st-key-report_distribute_"] .stButton > button:not([kind="primary"]) {{
            background: #DCFCE7;
            color: #15803D;
            border: 1px solid #86EFAC;
        }}
        div[class*="st-key-distribute_"] .stButton > button:not([kind="primary"]):hover,
        div[class*="st-key-report_distribute_"] .stButton > button:not([kind="primary"]):hover {{
            background: #BBF7D0;
            color: #15803D;
        }}

        /* 문항검토 / 결과리포트: 미완료 단계 표시(과제미제출·문항미생성 등)는 분홍색으로 */
        .ec-status-stage {{
            color: #DB2777;
            font-size: 0.92rem;
            text-align: center;
            display: block;
        }}

        /* 문항검토: [과제 이해도 문항 생성] 버튼 글자가 한 줄로 보이도록 */
        div[class*="st-key-qview_"] .stButton > button,
        div[class*="st-key-qview_"] .stButton > button p {{
            white-space: nowrap;
        }}

        /* 틀린 문항 확인: 내 답(분홍) / 정답(연두)을 서로 다른 행으로 구분 */
        .ec-wrong-my-answer {{
            display: block;
            background: #FCE7F3;
            color: #BE185D;
            border-radius: 8px;
            padding: 0.4rem 0.7rem;
            margin: 0.3rem 0;
            font-size: 0.9rem;
        }}
        .ec-wrong-correct-answer {{
            display: block;
            background: #DCFCE7;
            color: #15803D;
            border-radius: 8px;
            padding: 0.4rem 0.7rem;
            margin: 0.3rem 0 0.8rem 0;
            font-size: 0.9rem;
        }}

        /* ---------- 메트릭 카드 ---------- */
        div[data-testid="stMetric"] {{
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 14px;
            padding: 0.9rem 1.1rem;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
        }}

        /* ---------- 구분선 ---------- */
        hr {{ border-color: {BORDER}; }}

        /* ---------- expander ---------- */
        div[data-testid="stExpander"] {{
            border-radius: 12px !important;
            border: 1px solid {BORDER} !important;
            background: {SURFACE};
        }}

        /* ---------- 히어로 섹션 (메인 화면) ---------- */
        .ec-hero {{
            text-align: center;
            padding: 5rem 1rem 4rem 1rem;
        }}
        .ec-hero h1 {{
            font-size: 3.1rem;
            font-weight: 800;
            color: {INK};
            margin-bottom: 0.6rem;
            letter-spacing: -0.02em;
        }}
        .ec-hero p {{
            font-size: 1.15rem;
            color: {MUTED};
            margin-bottom: 0;
        }}
        .ec-hero .ec-hero-badge {{
            display: inline-block;
            background: linear-gradient(90deg, {PRIMARY}, {ACCENT});
            color: white;
            font-weight: 700;
            font-size: 0.8rem;
            letter-spacing: 0.04em;
            padding: 0.35rem 0.9rem;
            border-radius: 999px;
            margin-bottom: 1.4rem;
        }}

        /* 메인 화면 '로그인' 버튼 아래의 '회원가입' 텍스트 링크 */
        div[class*="st-key-main_signup_link"] {{
            text-align: center;
            margin-top: 0.6rem;
        }}
        div[class*="st-key-main_signup_link"] .stButton > button {{
            border: none;
            background: transparent;
            box-shadow: none;
            color: {MUTED};
            font-weight: 600;
            font-size: 0.9rem;
            text-decoration: underline;
            text-underline-offset: 3px;
            padding: 0.2rem 0.4rem;
        }}
        div[class*="st-key-main_signup_link"] .stButton > button:hover {{
            color: {PRIMARY_DARK};
        }}

        .ec-feature {{
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 16px;
            padding: 1.6rem 1.4rem;
            height: 100%;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
        }}
        .ec-feature .ec-feature-icon {{
            font-size: 1.7rem;
            margin-bottom: 0.6rem;
        }}
        .ec-feature h4 {{
            margin: 0 0 0.35rem 0;
            color: {INK};
            font-weight: 700;
        }}
        .ec-feature p {{
            color: {MUTED};
            font-size: 0.92rem;
            margin: 0;
        }}

        .ec-auth-wrap {{
            max-width: 460px;
            margin: 2.2rem auto 0 auto;
        }}
        .ec-user-chip {{
            color: {MUTED};
            font-size: 0.85rem;
            font-weight: 600;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .ec-user-chip b {{ color: {INK}; }}

        /* 관리자(교사) 네비게이션 바 전용: 비활성 로고 + 좌측 정렬 교사정보 + 구분선 */
        .ec-nav-logo-disabled {{
            font-weight: 700;
            font-size: 0.95rem;
            color: {MUTED};
            white-space: nowrap;
            padding: 0.45rem 0.6rem;
        }}
        .ec-user-chip-inline {{
            text-align: left;
            padding: 0.45rem 0.6rem;
        }}
        .ec-nav-divider {{
            width: 1px;
            height: 1.6rem;
            background: {BORDER};
            margin: 0.45rem auto 0 auto;
        }}

        .ec-table-header {{
            padding: 0 1.1rem;
            color: {MUTED};
            font-size: 0.82rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.02em;
            margin-bottom: 0.35rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def card():
    """
    카드 스타일 컨테이너를 반환합니다. 매 호출마다 고유한 key를 자동 발급하므로
    한 화면에서 여러 번 `with ui.card():` 를 사용해도 key 중복 에러가 나지 않습니다.
    사용법: with ui.card(): ... 위젯들 ...
    """
    return st.container(key=f"card_{next(_card_counter)}")


def page_header(title, subtitle=None, eyebrow=None):
    """화면 최상단 제목 블록 (eyebrow: 작은 라벨, subtitle: 설명문)"""
    html = ""
    if eyebrow:
        html += f'<div class="ec-eyebrow">{eyebrow}</div>'
    html += f'<div class="ec-title">{title}</div>'
    if subtitle:
        html += f'<div class="ec-subtitle">{subtitle}</div>'
    st.markdown(html, unsafe_allow_html=True)


def badge(text, kind="muted"):
    """뱃지 HTML 문자열을 반환합니다. kind: success/warning/muted/info"""
    return f'<span class="ec-badge ec-badge-{kind}">{text}</span>'


def empty_state(message, icon="🌤️"):
    st.markdown(
        f"""
        <div class="ec-card" style="text-align:center; padding: 3rem 1.5rem; color:{MUTED};">
            <div style="font-size:2.2rem; margin-bottom:0.6rem;">{icon}</div>
            <div style="font-size:1rem;">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def colored_metric(label, value, bg, fg):
    """색이 입혀진 요약 카드 (제출현황 화면의 과제제출/재검사완료/결과확인 등에 사용)."""
    st.markdown(
        f"""
        <div style="background:{bg}; border-radius:14px; padding:0.95rem 1.1rem; height:100%;">
            <div style="color:{fg}; font-size:0.85rem; font-weight:700; opacity:0.85;">{label}</div>
            <div style="color:{fg}; font-size:1.9rem; font-weight:800; margin-top:0.25rem;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_topnav(role, active, user=None, items=None, go_to=None, on_logout=None):
    """
    상단 네비게이션 바.
    role  : "guest" | "teacher" | "student"
    active: 현재 활성화된 메뉴 key
    items : [(key, label, page_name), ...] 형태의 메뉴 목록
    go_to : views.common_views.go_to 함수 (페이지 전환용)
    on_logout: 로그아웃 처리 함수 (auth.logout)

    role == "teacher" 인 경우는 관리자 화면 전용 레이아웃을 사용합니다:
      [EarthCheck(비활성)] [교사정보] | [메뉴들...] | [로그아웃]
    """
    if role == "teacher":
        _render_admin_topnav(active, user, items, go_to, on_logout)
        return

    with st.container(key="topnav"):
        widths = [1.7, 0.2] + [1.3] * len(items) + [2.6]
        cols = st.columns(widths)

        with cols[0]:
            if st.button("🌎  EarthCheck", key="nav_logo", use_container_width=True):
                if go_to:
                    home = "main" if role == "guest" else "student_home"
                    go_to(home)

        for i, (key, label, page_name) in enumerate(items):
            with cols[2 + i]:
                clicked = st.button(
                    label,
                    key=f"nav_{key}",
                    use_container_width=True,
                    type="primary" if active == key else "secondary",
                )
                if clicked and go_to:
                    go_to(page_name)

        with cols[-1]:
            if role == "guest":
                g1, g2 = st.columns(2)
                with g1:
                    if st.button(
                        "로그인", key="nav_login", use_container_width=True,
                        type="primary" if active == "login" else "secondary",
                    ) and go_to:
                        go_to("login")
                with g2:
                    if st.button(
                        "회원가입", key="nav_signup", use_container_width=True,
                        type="secondary" if active == "login" else "primary",
                    ) and go_to:
                        go_to("signup")
            else:
                u1, u2 = st.columns([2.4, 1])
                with u1:
                    chip = (
                        f"<div class='ec-user-chip'>🎓 <b>{user['name']}</b> · "
                        f"{user['school'] or '-'} {user['grade'] or ''}{user['class_no'] or ''}"
                        f"{('/' + str(user['student_no'])) if user['student_no'] else ''}</div>"
                    )
                    st.markdown(f"<div style='padding-top:0.55rem; text-align:right;'>{chip}</div>", unsafe_allow_html=True)
                with u2:
                    if st.button("로그아웃", key="nav_logout", use_container_width=True) and go_to and on_logout:
                        on_logout()
                        go_to("main")


def render_admin_topbar(active, items, go_to):
    """
    교사 화면 전용 상단 바. 이제 로고/교사정보/로그아웃은 왼쪽 사이드바로 옮겨졌으므로,
    여기서는 {회원관리·과제관리·문항검토·결과리포트} 메뉴 버튼만 가로로 보여줍니다.
    사이드바 오른쪽 본문 영역 안에서만 펼쳐지므로 사이드바와 겹치지 않습니다.
    """
    items = items or []
    with st.container(key="topnav"):
        cols = st.columns(len(items))
        for i, (key, label, page_name) in enumerate(items):
            with cols[i]:
                clicked = st.button(
                    label,
                    key=f"nav_{key}",
                    use_container_width=True,
                    type="primary" if active == key else "secondary",
                )
                if clicked and go_to:
                    go_to(page_name)


def render_role_sidebar(role, active, user, items, go_to, on_logout):
    """
    왼쪽 사이드바 (학생/교사 공용).
    - 상단 'EarthCheck' 타이틀은 클릭/호버 반응이 없는 순수 텍스트입니다.
    - role == "student": 학교/학년-반-번호/이름 정보를 보여줍니다.
    - role == "teacher": 학교명과 교사명을 보여줍니다.
    - items: [(key, label, page_name), ...] 형태의 메뉴 목록
    """
    with st.sidebar:
        st.markdown(
            "<div class='ec-sidebar-badge'>AI 기반 서술형 과제 이해도 평가 플랫폼</div>"
            "<div class='ec-sidebar-title'>🌎 EarthCheck</div>",
            unsafe_allow_html=True,
        )

        if role == "teacher":
            info_html = f"""
            <div class='ec-sidebar-userinfo'>
                {user['school'] or '-'}<br>
                {user['name']} 선생님
                <div class='ec-welcome'>환영합니다!  :)</div>
            </div>
            """
        else:
            info_html = f"""
            <div class='ec-sidebar-userinfo'>
                {user['school'] or '-'}<br>
                {user['grade'] or ''}-{user['class_no'] or ''}-{user['student_no'] or ''}<br>
                {user['name']}
                <div class='ec-welcome'>환영합니다!  :)</div>
            </div>
            """
        st.markdown(info_html, unsafe_allow_html=True)

        for key, label, page_name in items:
            if st.button(
                label, key=f"sidebar_{key}", use_container_width=True,
                type="primary" if active == key else "secondary",
            ):
                go_to(page_name)

        st.markdown("<div class='ec-sidebar-divider'></div>", unsafe_allow_html=True)
        if st.button("로그아웃", key="sidebar_logout", use_container_width=True):
            on_logout()
            go_to("main")


def render_student_sidebar(active, user, items, go_to, on_logout):
    """(하위 호환용) render_role_sidebar(role='student', ...)의 얇은 래퍼입니다."""
    render_role_sidebar("student", active, user, items, go_to, on_logout)
