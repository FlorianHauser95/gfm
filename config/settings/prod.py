from .base import *

DEBUG = False

ALLOWED_HOSTS = ["grubhebtab.de","www.grubhebtab.de"]

# Django läuft unter /app/
FORCE_SCRIPT_NAME = "/gfm"
STATIC_URL = "/gfm/static/"

# Reverse Proxy / SSL
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

CSRF_TRUSTED_ORIGINS = ["https://grubhebtab.de","https://www.grubhebtab.de"]

# Security Headers (nach Testphase ggf. hochdrehen)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False