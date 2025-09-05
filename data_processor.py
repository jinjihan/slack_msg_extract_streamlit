# data_processor.py
# 데이터 처리 및 변환 함수들

import io
import zipfile
from typing import List
import pandas as pd
import requests
from slack_sdk import WebClient

from slack_client import list_history, list_replies, get_permalink, build_user_cache
from config import ts_to_iso


def build_unified_df(token: str, channel_id: str, channel_name: str, start_dt, end_dt) -> pd.DataFrame:
    """메시지와 스레드를 통합한 DataFrame 생성"""
    client = WebClient(token=token)
    oldest = start_dt.timestamp() if start_dt else None
    latest = end_dt.timestamp() if end_dt else None

    messages = list_history(client, channel_id, oldest, latest)
    parents = [m for m in messages if m.get("thread_ts") in (None, m.get("ts"))]

    uname = build_user_cache(token)
    rows: List[dict] = []

    for p in parents:
        root_ts = p.get("thread_ts") or p.get("ts")
        rows.append({
            "row_type": "parent",
            "depth": 0,
            "root_ts": root_ts,
            "parent_ts": None,
            "ts": p.get("ts"),
            "channel_id": channel_id,
            "channel_name": channel_name,
            "user_id": p.get("user"),
            "user_name": uname.get(p.get("user"), p.get("user", "")),
            "text": p.get("text", ""),
            "datetime": ts_to_iso(p.get("ts", "")),
            "files_count": len(p.get("files", []) or []),
            "file_names": ";".join([f.get("name", "") for f in (p.get("files") or [])]),
            "file_urls": ";".join([f.get("url_private", "") for f in (p.get("files") or [])]),
            "permalink": get_permalink(client, channel_id, p.get("ts")),
        })
        
        if p.get("reply_count", 0) > 0:
            for r in list_replies(client, channel_id, root_ts):
                rows.append({
                    "row_type": "reply",
                    "depth": 1,
                    "root_ts": root_ts,
                    "parent_ts": p.get("ts"),
                    "ts": r.get("ts"),
                    "channel_id": channel_id,
                    "channel_name": channel_name,
                    "user_id": r.get("user"),
                    "user_name": uname.get(r.get("user"), r.get("user", "")),
                    "text": r.get("text", ""),
                    "datetime": ts_to_iso(r.get("ts", "")),
                    "files_count": len(r.get("files", []) or []),
                    "file_names": ";".join([f.get("name", "") for f in (r.get("files") or [])]),
                    "file_urls": ";".join([f.get("url_private", "") for f in (r.get("files") or [])]),
                    "permalink": get_permalink(client, channel_id, r.get("ts")),
                })

    df = pd.DataFrame(rows)
    if not df.empty:
        df["_root_ts_f"] = df["root_ts"].astype(float)
        df["_ts_f"] = df["ts"].astype(float)
        df.sort_values(["_root_ts_f", "depth", "_ts_f"], inplace=True)
        df.drop(columns=["_root_ts_f", "_ts_f"], inplace=True)
    
    return df


def download_files_zip(token: str, df: pd.DataFrame) -> bytes:
    """첨부 파일들을 ZIP으로 다운로드"""
    headers = {"Authorization": f"Bearer {token}"}
    buf = io.BytesIO()
    
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for _, row in df.iterrows():
            urls = [u for u in (row.get("file_urls") or "").split(";") if u]
            names = (row.get("file_names") or "").split(";")
            
            for i, u in enumerate(urls):
                try:
                    r = requests.get(u, headers=headers, timeout=60)
                    if r.status_code == 200:
                        name = names[i] if i < len(names) and names[i] else f"{row['ts']}_{i}"
                        arcname = f"{row['channel_name']}/{row['root_ts']}/{name}"
                        zf.writestr(arcname, r.content)
                except Exception:
                    pass
    
    buf.seek(0)
    return buf.getvalue()


def create_excel_buffer(df: pd.DataFrame) -> bytes:
    """DataFrame을 Excel 파일로 변환하여 BytesIO 버퍼 반환"""
    xbuf = io.BytesIO()
    with pd.ExcelWriter(xbuf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="messages_with_threads")
    xbuf.seek(0)
    return xbuf.getvalue()
