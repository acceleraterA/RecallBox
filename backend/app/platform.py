from urllib.parse import urlparse


def detect_platform(url: str) -> str:
    hostname = (urlparse(url).hostname or "").lower()
    hostname = hostname.removeprefix("www.")

    if hostname == "bilibili.com" or hostname.endswith(".bilibili.com"):
        return "bilibili"
    if hostname == "xiaohongshu.com" or hostname.endswith(".xiaohongshu.com"):
        return "xiaohongshu"
    if hostname == "douyin.com" or hostname.endswith(".douyin.com"):
        return "douyin"
    if hostname == "mp.weixin.qq.com":
        return "wechat_article"
    if hostname == "youtube.com" or hostname.endswith(".youtube.com") or hostname == "youtu.be":
        return "youtube"
    return "web"
