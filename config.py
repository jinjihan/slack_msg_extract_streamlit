# config.py
# 설정 및 유틸리티 함수들

import streamlit as st
from datetime import datetime
from typing import Dict


def get_workspaces_from_toml() -> Dict[str, str]:
    """secrets.toml에서 워크스페이스 정보를 자동으로 구성"""
    workspaces: Dict[str, str] = {}
    
    if "slack" not in st.secrets:
        return workspaces
    
    slack_config = dict(st.secrets["slack"])
    
    for key, value in slack_config.items():
        # AttrDict나 dict 타입 모두 지원
        if hasattr(value, 'get') and value.get("name") and value.get("token"):
            workspaces[value["name"]] = value["token"]
    
    return workspaces


def get_workspaces_from_ui() -> Dict[str, str]:
    """UI에서 입력된 워크스페이스 정보를 가져옴"""
    workspaces = st.session_state.get("workspaces", {})
    return workspaces


def get_workspaces() -> Dict[str, str]:
    """워크스페이스 정보를 가져옴 (TOML 우선, 없으면 UI 입력 사용)"""
    # TOML에서 먼저 시도
    toml_workspaces = get_workspaces_from_toml()
    
    # TOML에 워크스페이스가 있으면 사용
    if toml_workspaces:
        return toml_workspaces
    
    # TOML에 없으면 UI 입력 사용
    ui_workspaces = get_workspaces_from_ui()
    
    # 둘 다 없으면 에러
    if not ui_workspaces:
        st.error("워크스페이스 토큰을 입력하거나 .streamlit/secrets.toml에 설정해주세요.")
        st.stop()
    
    return ui_workspaces


def validate_slack_token(token: str) -> bool:
    """Slack 토큰 형식 검증"""
    if not token:
        return False
    
    # Slack Bot Token 형식: xoxb-로 시작하는 24자 이상
    if token.startswith("xoxb-") and len(token) >= 24:
        return True
    
    # Slack User Token 형식: xoxp-로 시작하는 24자 이상  
    if token.startswith("xoxp-") and len(token) >= 24:
        return True
    
    return False


def ts_to_iso(ts: str) -> str:
    """Slack timestamp를 ISO 형식 문자열로 변환"""
    try:
        return datetime.fromtimestamp(float(ts)).astimezone().strftime("%Y-%m-%d %H:%M:%S%z")
    except Exception:
        return ""


def validate_channel_input(channel_id: str) -> bool:
    """채널 ID 입력 검증"""
    if not channel_id:
        st.error("채널을 입력/선택하세요.")
        return False
    return True


def get_date_range(start_date, end_date):
    """날짜 범위를 datetime 객체로 변환"""
    sdt = datetime.combine(start_date, datetime.min.time()).astimezone() if start_date else None
    edt = datetime.combine(end_date, datetime.max.time()).astimezone() if end_date else None
    return sdt, edt
