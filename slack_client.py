# slack_client.py
# Slack API 관련 함수들

from typing import Dict, List
from tenacity import retry, stop_after_attempt, wait_exponential_jitter
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


@retry(stop=stop_after_attempt(5), wait=wait_exponential_jitter(2, 8))
def call_with_retry(func, **kwargs):
    """API 호출 재시도 로직"""
    return func(**kwargs)


def list_channels(token: str) -> List[dict]:
    """채널 목록 조회"""
    client = WebClient(token=token)
    chans: List[dict] = []
    cursor = None
    
    while True:
        resp = call_with_retry(
            client.conversations_list,
            cursor=cursor,
            limit=200,
            types="public_channel,private_channel",
        )
        chans += resp.get("channels", [])
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    
    return chans


def build_user_cache(token: str) -> Dict[str, str]:
    """사용자 ID → 이름 매핑 캐시 구축"""
    client = WebClient(token=token)
    name_map: Dict[str, str] = {}
    cursor = None
    
    while True:
        resp = call_with_retry(client.users_list, cursor=cursor, limit=200)
        for u in resp.get("members", []):
            uid = u.get("id")
            if uid:
                name_map[uid] = u.get("profile", {}).get("real_name") or u.get("name") or uid
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    
    return name_map


def list_history(client: WebClient, channel: str, oldest: float | None, latest: float | None) -> List[dict]:
    """채널 메시지 히스토리 조회"""
    messages: List[dict] = []
    cursor = None
    
    while True:
        resp = client.conversations_history(
            channel=channel,
            cursor=cursor,
            limit=200,
            oldest=str(oldest) if oldest else None,
            latest=str(latest) if latest else None,
            inclusive=True,
        )
        messages += resp.get("messages", [])
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    
    return messages


def list_replies(client: WebClient, channel: str, parent_ts: str) -> List[dict]:
    """스레드 답글 조회"""
    replies: List[dict] = []
    cursor = None
    
    while True:
        resp = client.conversations_replies(
            channel=channel,
            ts=parent_ts,
            cursor=cursor,
            limit=200,
            inclusive=True,
        )
        msgs = resp.get("messages", [])
        replies += [m for m in msgs if m.get("ts") != parent_ts]
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    
    return replies


def get_permalink(client: WebClient, channel: str, ts: str) -> str:
    """메시지 permalink 조회"""
    try:
        pr = client.chat_getPermalink(channel=channel, message_ts=ts)
        return pr.get("permalink") or ""
    except SlackApiError:
        return ""
