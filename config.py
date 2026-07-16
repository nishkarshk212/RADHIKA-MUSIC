from os import getenv
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        self.API_ID = int(getenv("API_ID", 0))
        self.API_HASH = getenv("API_HASH")

        self.BOT_TOKEN = getenv("BOT_TOKEN")
        self.MONGO_URL = getenv("MONGO_URL")

        self.LOGGER_ID = int(getenv("LOGGER_ID", 0))
        self.OWNER_ID = int(getenv("OWNER_ID", 0))

        self.DURATION_LIMIT = int(getenv("DURATION_LIMIT", 120)) * 60
        self.QUEUE_LIMIT = int(getenv("QUEUE_LIMIT", 20))
        self.PLAYLIST_LIMIT = int(getenv("PLAYLIST_LIMIT", 20))

        self.SESSION1 = getenv("SESSION", None)
        self.SESSION2 = getenv("SESSION2", None)
        self.SESSION3 = getenv("SESSION3", None)

        self.SUPPORT_CHANNEL = getenv("SUPPORT_CHANNEL", "https://t.me/titanic_network")
        self.SUPPORT_CHAT = getenv("SUPPORT_CHAT", "https://t.me/+WAOT47P-70QwOTBl")

        self.YTPROXY_URL = getenv("YTPROXY_URL", "https://tgapi.xbitcode.com")  # xBit Music Endpoint
        self.YT_API_KEY = getenv("YT_API_KEY", "")  # Get from https://t.me/tgmusic_apibot

        # Railway self-hosted YouTube API
        self.RAILWAY_YT_API_URL = getenv("RAILWAY_YT_API_URL", "https://youtube-api-music-production-824b.up.railway.app")
        self.RAILWAY_YT_API_KEY = getenv("RAILWAY_YT_API_KEY", "SLtWox3TFKKHuMySdvz_4y2Ju3NlSHYk")

        # Shruti API — Primary download source (get key from @SHRUTIAPIBOT)
        self.SHRUTI_API_URL = getenv("SHRUTI_API_URL", "http://api01.shrutibots.site")
        self.SHRUTI_API_KEY = getenv("SHRUTI_API_KEY", "")

        # Forward proxy used to fetch googlevideo media so YouTube doesn't
        # 403 the bot's (flagged) deployment egress IP. Use socks5h:// so DNS
        # is resolved through the proxy (the proxy host has no IPv6 route).
        # Defaults to the project VPS SOCKS5 proxy so the bot works on deploy
        # without manual config; set STREAM_PROXY_URL="" to disable.
        self.STREAM_PROXY_URL = getenv(
            "STREAM_PROXY_URL", "socks5h://lily:lilypass@165.245.190.41:1080"
        )
        
        self.AUTO_LEAVE: bool = getenv("AUTO_LEAVE", "False").lower() == "true"
        self.AUTO_END: bool = getenv("AUTO_END", "False").lower() == "true"
    
        self.THUMB_GEN: bool = getenv("THUMB_GEN", "True").lower() == "true"
        self.VIDEO_PLAY: bool = getenv("VIDEO_PLAY", "True").lower() == "true"

        self.LANG_CODE = getenv("LANG_CODE", "en")

        self.COOKIES_URL = [
            url for url in getenv("COOKIES_URL", "").split(" ")
            if url and "batbin.me" in url
        ]
        self.COOKIES_DATA = getenv("COOKIES_DATA", "")
        self.DEFAULT_THUMB = getenv("DEFAULT_THUMB", "https://te.legra.ph/file/3e40a408286d4eda24191.jpg")
        self.PING_IMG = getenv("PING_IMG", "https://files.catbox.moe/haagg2.png")
        self.START_IMG = getenv("START_IMG", "https://files.catbox.moe/zvziwk.jpg")

    def check(self):
        missing = [
            var
            for var in ["API_ID", "API_HASH", "BOT_TOKEN", "MONGO_URL", "LOGGER_ID", "OWNER_ID", "SESSION1"]
            if not getattr(self, var)
        ]
        if missing:
            raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")
