# auth.py
# 인증 및 사용자 관리 시스템

import streamlit as st
import hashlib
from typing import Dict, Optional


def hash_password(password: str) -> str:
    """비밀번호를 SHA-256으로 해시화"""
    return hashlib.sha256(password.encode()).hexdigest()


def get_users() -> Dict[str, str]:
    """사용자 정보를 가져옴 (secrets.toml에서)"""
    if "users" not in st.secrets:
        return {}
    
    users = {}
    for username, password_hash in st.secrets["users"].items():
        users[username] = password_hash
    return users


def authenticate_user(username: str, password: str) -> bool:
    """사용자 인증"""
    users = get_users()
    
    if username not in users:
        return False
    
    password_hash = hash_password(password)
    return users[username] == password_hash


def is_authenticated() -> bool:
    """현재 사용자가 인증되었는지 확인"""
    return st.session_state.get("authenticated", False)


def login_user(username: str):
    """사용자 로그인"""
    st.session_state["authenticated"] = True
    st.session_state["username"] = username


def logout_user():
    """사용자 로그아웃"""
    st.session_state["authenticated"] = False
    st.session_state["username"] = None


def show_login_form():
    """로그인 폼 표시"""
    st.title("🔐 로그인")
    st.markdown("Slack 메시지 추출 도구에 접근하려면 로그인이 필요합니다.")
    
    with st.form("login_form"):
        username = st.text_input("사용자명", placeholder="사용자명을 입력하세요")
        password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
        submit_button = st.form_submit_button("로그인")
        
        if submit_button:
            if not username or not password:
                st.error("사용자명과 비밀번호를 모두 입력해주세요.")
                return
            
            if authenticate_user(username, password):
                login_user(username)
                st.success(f"환영합니다, {username}님!")
                st.rerun()
            else:
                st.error("잘못된 사용자명 또는 비밀번호입니다.")


def show_logout_button():
    """로그아웃 버튼 표시"""
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🚪 로그아웃"):
            logout_user()
            st.rerun()
    with col2:
        st.write(f"👤 {st.session_state.get('username', 'Unknown')}님으로 로그인됨")


def require_auth(func):
    """인증이 필요한 함수에 적용할 데코레이터"""
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            show_login_form()
            return
        return func(*args, **kwargs)
    return wrapper
