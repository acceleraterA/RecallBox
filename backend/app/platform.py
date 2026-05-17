from urllib.parse import urlparse


PLATFORM_HOSTS = {
    "bilibili": ("bilibili.com",),
    "xiaohongshu": ("xiaohongshu.com", "xhslink.com"),
    "douyin": ("douyin.com",),
    "wechat_article": ("mp.weixin.qq.com",),
    "weibo": ("weibo.com", "weibo.cn"),
    "douban": ("douban.com",),
    "instagram": ("instagram.com",),
    "snapchat": ("snapchat.com",),
    "tiktok": ("tiktok.com",),
    "youtube": ("youtube.com", "youtu.be"),
    "x": ("x.com", "twitter.com"),
    "medium": ("medium.com",),
    "reddit": ("reddit.com", "redd.it"),
}


def _matches_host(hostname: str, domains: tuple[str, ...]) -> bool:
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in domains)


def detect_platform(url: str) -> str:
    hostname = (urlparse(url).hostname or "").lower()
    hostname = hostname.removeprefix("www.")

    for platform, domains in PLATFORM_HOSTS.items():
        if _matches_host(hostname, domains):
            return platform

    return "web"
