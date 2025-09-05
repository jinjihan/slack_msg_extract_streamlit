# app.py
# Streamlit app: Slack 메시지 및 스레드를 Excel로 내보내기
# 워크스페이스 자동 감지 및 단일 시트 통합

import streamlit as st

from config import get_workspaces, validate_channel_input, get_date_range
from slack_client import list_channels
from data_processor import build_unified_df, download_files_zip, create_excel_buffer

# ------ UI ------
st.set_page_config(page_title="슬랙 채널 메세지 추출", layout="wide")
st.title("슬랙 채널 메세지 추출")

# 워크스페이스 설정
WORKSPACES = get_workspaces()
workspace_name = st.selectbox("워크스페이스 선택", list(WORKSPACES.keys()))
TOKEN = WORKSPACES[workspace_name]

ch_mode = st.radio("채널 선택 방법", ["목록에서 선택", "채널 ID 직접 입력"], index=0)

channel_id, channel_name = "", ""
if ch_mode == "목록에서 선택":
    if st.button("채널 목록 불러오기"):
        st.session_state["channels_cache"] = list_channels(TOKEN)
    chans = st.session_state.get("channels_cache", [])
    if chans:
        label_map = {f"#{c.get('name')} ({c.get('id')})": c.get("id") for c in chans}
        label = st.selectbox("채널", list(label_map.keys()))
        channel_id = label_map[label]
        channel_name = label.split(" ")[0].lstrip("#")
    else:
        st.info("채널 목록을 불러오세요.")
else:
    channel_id = st.text_input("채널 ID (예: C0123ABCD)")
    channel_name = st.text_input("채널명(엑셀 파일명용)", value="channel")

col_a, col_b = st.columns(2)
with col_a:
    start_date = st.date_input("시작일", value=None)
with col_b:
    end_date = st.date_input("종료일", value=None)

run = st.button("수집 실행")

if run:
    if not validate_channel_input(channel_id):
        st.stop()
    
    with st.spinner("수집 중…"):
        sdt, edt = get_date_range(start_date, end_date)
        df = build_unified_df(TOKEN, channel_id, channel_name or channel_id, sdt, edt)

    st.subheader("미리보기")
    if df.empty:
        st.warning("해당 조건에서 조회된 메시지가 없습니다.")
    else:
        st.dataframe(df.head(300), use_container_width=True)
        
        # Excel 다운로드
        excel_data = create_excel_buffer(df)
        st.download_button(
            "엑셀 다운로드 (.xlsx)",
            data=excel_data,
            file_name=f"slack_{channel_name or channel_id}_threads.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        
        # 첨부 파일 ZIP 다운로드
        with st.expander("첨부 파일 ZIP (선택)"):
            if st.button("ZIP 생성"):
                with st.spinner("파일 다운로드 및 압축 중…"):
                    zbytes = download_files_zip(TOKEN, df[df["files_count"] > 0])
                st.download_button(
                    "파일 ZIP 다운로드",
                    data=zbytes,
                    file_name=f"slack_{channel_name or channel_id}_files.zip",
                    mime="application/zip",
                )