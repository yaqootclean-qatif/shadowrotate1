# ============ PART 1 ============
"""
server.py — ShadowRotate Backend v3.0
نظام إدارة الحسابات الاحترافي
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import platform
import re
import secrets
import string
import subprocess
import sys
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ============================================================
# التثبيت التلقائي للمكتبات
# ============================================================
REQUIRED = ["fastapi", "uvicorn", "playwright", "pyotp", "openpyxl", "python-multipart"]

def ensure_dependencies():
    missing = []
    for pkg in REQUIRED:
        mod = pkg.replace("-", "_")
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[setup] Installing: {missing}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
        print("[setup] Done. Relaunching...")
        os.execv(sys.executable, [sys.executable] + sys.argv)

ensure_dependencies()

import pyotp
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from playwright.async_api import async_playwright, TimeoutError as PWTimeout


# ============================================================
# الإعدادات
# ============================================================
BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = BASE_DIR / "output"
SHOTS_DIR = BASE_DIR / "shots"
ACTIVATED_FILE = BASE_DIR / "activated.json"

OUTPUT_DIR.mkdir(exist_ok=True)
SHOTS_DIR.mkdir(exist_ok=True)

HEADLESS = os.getenv("HEADLESS", "0") == "1"
SLOW_MO = int(os.getenv("SLOW_MO", "80"))
NAV_TIMEOUT = 60_000
ACTION_TIMEOUT = 25_000
TRIAL_MAX_ACCOUNTS = 5
TRIAL_MAX_PARALLEL = 1
PRO_MAX_PARALLEL = 15
SUBSCRIPTION_DAYS = 30


# ============================================================
# قائمة المستخدمين — المجموعة 1 (100 مستخدم)
# ============================================================
USERS_BUILTIN = {
    "vk8mq2px7n4lfz8t3hj@gmail.com": "K9#mP2$xL@vN4wR6tY8uQ!zA5&bC7*dE3fG",
    "qw3er5ty9ui2op4as6d@gmail.com": "W5@rYt9$Um2#Bv7&Nz4dP!cX8*eS6%fG",
    "zx4cv2bn5m8k1j4h6gf@gmail.com": "A7!sEd3%Fg6#Hj9&Kl2mN@bV4$cX8*dZ",
    "we6rt3ty7ui1op2as8d@gmail.com": "Z4@wQx7$Cv1#Bn8&Mr5tP!dF6*gH9%jK",
    "sd2fg8h1j4k7l9z6xc@gmail.com": "E6!rTy4%Ui8#Op2&As9dF@vB3$nM7*cX",
    "cv4bn5m8k1j6h9g3f2@gmail.com": "H3@jKl6$Pm9#Vb2&Nc7xZ!dF4*gH8%jK",
    "rt6yu9i4o8p1a3s5d2@gmail.com": "R5!fGh7%Tk1#Yz3&Wq8eS@cV2$nM6*bX",
    "fg8h1j5k9l7z2x4c6v@gmail.com": "T7@sDf2$Gh5#Jk8&Lm3nB!vC4*xZ9%qW",
    "bn4m8k6j1h3g5f7d9s@gmail.com": "U9!wEr4%Ty6#Ui2&Op7aD@zX3$cV8*bN",
    "yu3i6o9p2a5s8d1f4g@gmail.com": "I2@oPa5$Sd8#Fg3&Hj6kL!zX4*cV9%bN",
    "hj5k9l1z3x7c5v9b2n@gmail.com": "O4!pAs7%Df9#Gh2&Jk5lZ@qW6*eR8%tY",
    "mk4j8h6g1f5d7s9a2p@gmail.com": "P6@qAz1$Sx3#Dc7&Fv9bN!wE4*rT8%yU",
    "nb7v9c2x4z6l1k3j5h@gmail.com": "L8!mNb4%Vc6#Xz1&Aq3wE@tY7*uI9%oP",
    "vc9x2z6l4k1j3h5g7f@gmail.com": "M1@nBv5$Cx7#Za2&Sd4fR!uI8*oP3%eW",
    "ty2u6i8o4p1a3s5d7f@gmail.com": "N3!bVc6%Zx8#As1&Df5gT@yU9*iO4%pW",
    "gf4d6s8a1p3o5i7u9y@gmail.com": "B5@vCx7$Za9#Sd2&Fg6hU!iP4*oY8%eI",
    "lk6j8h1g3f5d7s9a4p@gmail.com": "V7!cXz8%As1#Df3&Gh7jI@oU9*pY5%eT",
    "po5i7u9y2t4r6e8w3q@gmail.com": "C9@xZa9$Sd2#Fg4&Hj8kO!pI6*uY3%eR",
    "ds3a5p7o9i2u4y6t8r@gmail.com": "X1!zAs1%Df3#Gh5&Jk9lP@qW4*eR8%tY",
    "nb1v3c5x7z9l4k6j8h@gmail.com": "Z3@aS2$Fg4#Hj6&Kl1mQ!wE5*rT9%yU",
    "kj8h4g2f1d5s3a7p9o@gmail.com": "S5!dF3%Gh5#Jk7&Lm2nR@tY8*uI4%oP",
    "mk9j7h3g1f2d4s6a8p@gmail.com": "D7@fG4$Hj6#Kl8&Mm3oQ!wE9*rT5%yU",
    "nb2v4c6x8z1l3k5j7h@gmail.com": "F9!gH5%Jk7#Lm9&Nn4pS@qW3*eR7%tY",
    "po5i7u9y1t3r5e7w2q@gmail.com": "G2@hJ6$Kl8#Mn1&Oo5qT!vC7*xZ4%bN",
    "qw8e1r3t5y7u9i2o4p@gmail.com": "H4!jK7%Lm9#No2&Pp6rU@cV8*nM3*bX",
    "rt1y3u5i7o9p2a4s6d@gmail.com": "J6@kL8$Mn1#Op3&Qq7sV!zX5*cV9%bN",
    "sd4f6g8h1j3k5l7z9x@gmail.com": "K8!lM9%No2#Pq4&Rr8tW@qY4*uI6%oP",
    "ty7u9i2o4p6a8s1d3f@gmail.com": "L1@mN1$Op3#Qr5&Ss9uX!wE6*rT3%yU",
    "ui1o3p5a7s9d2f4g6h@gmail.com": "M3!nO2%Pq4#Rs6&Tt1vY@zX7*cV5%bN",
    "vc4x6z8l1k3j5h7g9f@gmail.com": "N5@oP3$Qr5#St7&Uu2wZ!qY8*uI4%oP",
    "we7r9t2y4u6i8o1p3a@gmail.com": "O7!pQ4%Rs6#Tu8&Vv3aB@cV9*nM2*bX",
    "xz1l3k5j7h9g2f4d6s@gmail.com": "P9@qR5$St7#Uv9&Ww4bC!wE3*rT6%yU",
    "yu4i6o8p1a3s5d7f9g@gmail.com": "Q2!rS6%Tu8#Vw1&Xx5cD@zX4*cV7%bN",
    "zx7c9v2b4n6m8k1j3h@gmail.com": "R4@sT7$Uv9#Wx2&Yy6dE!qY5*uI8%oP",
    "as1d3f5g7h9j2k4l6z@gmail.com": "S6!tU8%Vw1#Xy3&Zz7eF@wE2*rT9%yU",
    "bn4m6k8j1h3g5f7d9s@gmail.com": "T8@uV9$Wx2#Yz4&Aa8fG!vC3*xZ6%bN",
    "cv7b9n2m4k6j8h1g3f@gmail.com": "U1!vW1%Xy3#Za5&Bb9gH@qY7*uI2%oP",
    "df1g3h5j7k9l2z4x6c@gmail.com": "V3@wX2$Yz4#Ab6&Cc1hI!zX8*cV5%bN",
    "er4t6y8u1i3o5p7a9s@gmail.com": "W5!xY3%Za5#Bc7&Dd2iJ@wE9*rT4%yU",
    "fg7h9j2k4l6z8x1c3v@gmail.com": "X7@yZ4$Ab6#Cd8&Ee3jK!vC2*xZ9%bN",
    "gh1j3k5l7z9x2c4v6b@gmail.com": "Y9!zA5%Bc7#De9&Ff4kL@qY3*uI6%oP",
    "hj4k6l8z1x3c5v7b9n@gmail.com": "Z2@aB6$Cd8#Ef1&Gg5lM!wE7*rT2%yU",
    "io7p9a2s4d6f8g1h3j@gmail.com": "A4!bC7%De9#Fg2&Hh6mN@zX9*cV3%bN",
    "jk1l3z5x7c9v2b4n6m@gmail.com": "B6@cD8$Ef1#Gh3&Ii7nO!qY5*uI9%oP",
    "kl4z6x8c1v3b5n7m9k@gmail.com": "C8!dE9%Fg2#Hi4&Jj8pP@wE4*rT7%yU",
    "lz7x9c2v4b6n8m1k3j@gmail.com": "D1@eF1$Gh3#Ij5&Kk9qQ!vC6*xZ8%bN",
    "mk1j3h5g7f9d2s4a6p@gmail.com": "E3!fG2%Hi4#Jk6&Ll1rR@qY7*uI3%oP",
    "nm4k6j8h1g3f5d7s9a@gmail.com": "F5@gH3$Ij5#Kl7&Mm2sS!wE8*rT5%yU",
    "op7a9s2d4f6g8h1j3k@gmail.com": "G7!hI4%Jk6#Lm8&Nn3tT@zX2*cV5%bN",
    "pa1s3d5f7g9h2j4k6l@gmail.com": "H9@iJ5$Kl7#Mn9&Oo4uU!qY6*uI8%oP",
    "qw4e6r8t1y3u5i7o9p@gmail.com": "I2!jK6%Lm8#No1&Pp5vV@wE3*rT9%yU",
    "rt7y9u2i4o6p8a1s3d@gmail.com": "J4@kL7$Mn9#Op2&Qq6wW!vC7*xZ4%bN",
    "sd1f3g5h7j9k2l4z6x@gmail.com": "K6!lM8%No1#Pq3&Rr7xX@qY9*uI5%oP",
    "ty4u6i8o1p3a5s7d9f@gmail.com": "L8@mN9$Op2#Qr4&Ss8yY!wE5*rT8%yU",
    "ui7o9p2a4s6d8f1g3h@gmail.com": "M1!nO1%Pq3#Rs5&Tt9zZ@zX6*cV2%bN",
    "vc1x3z5l7k9j2h4g6f@gmail.com": "N3@oP2$Qr4#St6&Uu1aA!qY8*uI4%oP",
    "we4r6t8y1u3i5o7p9a@gmail.com": "O5!pQ3%Rs5#Tu7&Vv2bB@wE6*rT3%yU",
    "xz7l9k2j4h6g8f1d3s@gmail.com": "P7@qR4$St6#Uv8&Ww3cC!vC9*xZ7%bN",
    "yu1i3o5p7a9s2d4f6g@gmail.com": "Q9!rS5%Tu7#Vw9&Xx4dD@qY2*uI9%oP",
    "zx4c6v8b1n3m5k7j9h@gmail.com": "R2@sT6$Uv8#Wx1&Yy5eE!wE7*rT4%yU",
    "as7d2f4g6h8j1k3l5z@gmail.com": "S4!tU7%Vw9#Xy2&Zz6fF@zX3*cV8%bN",
    "bn1m3k5j7h9g2f4d6s@gmail.com": "T6@uV8$Wx1#Yz3&Aa7gG!qY5*uI2%oP",
    "cv4b6n1m3k5j7h9g2f@gmail.com": "U8!vW9%Xy2#Za4&Bb8hH@wE9*rT6%yU",
    "df7g2h4j6k8l1z3x5c@gmail.com": "V1@wX1$Yz3#Ab5&Cc9iI!vC4*xZ6%bN",
    "er1t3y5u7i9o2p4a6s@gmail.com": "W3!xY2%Za4#Bc6&Dd1jJ@qY8*uI5%oP",
    "fg4h6j8k1l3z5x7c9v@gmail.com": "X5@yZ3$Ab5#Cd7&Ee2kK!wE3*rT7%yU",
    "gh7j9k2l4z6x8c1v3b@gmail.com": "Y7!zA4%Bc6#De8&Ff3lL@zX5*cV2%bN",
    "hj1k3l5z7x9c2v4b6n@gmail.com": "Z9@aB5$Cd7#Ef9&Gg4mM!qY7*uI3%oP",
    "io4p6a8s1d3f5g7h9j@gmail.com": "A2!bC6%De8#Fg1&Hh5nN@wE8*rT4%yU",
    "jk7k9l2z4x6c8v1b3n@gmail.com": "B4@cD7$Ef9#Gh2&Ii6oO!vC7*xZ3%bN",
    "kl1l3z5x7c9v2b4n6m@gmail.com": "C6!dE8%Fg1#Hi3&Jj7pP@qY9*uI6%oP",
    "lz4x6c8v1b3n5m7k9j@gmail.com": "D8@eF9$Gh2#Ij4&Kk8qQ!wE4*rT8%yU",
    "mk7j9h2g4f6d8s1a3p@gmail.com": "E1!fG1%Hi3#Jk5&Ll9rR@zX8*cV4%bN",
    "nm1m3k5j7h9g2f4d6s@gmail.com": "F3@gH2$Ij4#Kl6&Mm1sS!qY3*uI7%oP",
    "op4p6a8s1d3f5g7h9j@gmail.com": "G5!hI3%Jk5#Lm7&Nn2tT@wE9*rT3%yU",
    "pa7a9s2d4f6g8h1j3k@gmail.com": "H7@iJ4$Kl6#Mn8&Oo3uU!vC4*xZ9%bN",
    "qw1w3e5r7t9y2u4i6o@gmail.com": "I9!jK5%Lm7#No9&Pp4vV@qY6*uI2%oP",
    "rt4t6y8u1i3o5p7a9s@gmail.com": "J2@kL6$Mn8#Op1&Qq5wW!wE7*rT5%yU",
    "sd7d9f2g4h6j8k1l3z@gmail.com": "K4!lM7%No9#Pq2&Rr6xX@zX5*cV3%bN",
    "ty1y3u5i7o9p2a4s6d@gmail.com": "L6@mN8$Op1#Qr3&Ss7yY!qY8*uI4%oP",
    "ui4i6o8p1a3s5d7f9g@gmail.com": "M8!nO9%Pq2#Rs4&Tt8zZ@wE2*rT9%yU",
    "vc7c9x2z4l6k8j1h3g@gmail.com": "N1@oP1$Qr3#St5&Uu9aA!vC8*xZ2%bN",
    "we1e3r5t7y9u2i4o6p@gmail.com": "O3!pQ2%Rs4#Tu6&Vv1bB@qY5*uI9%oP",
    "xz4z6l8k1j3h5g7f9d@gmail.com": "P5@qR3$St5#Uv7&Ww2cC!wE4*rT6%yU",
    "yu7u9i2o4p6a8s1d3f@gmail.com": "Q7!rS4%Tu6#Vw8&Xx3dD@zX9*cV7%bN",
    "zx1x3c5v7b9n2m4k6j@gmail.com": "R9@sT5$Uv7#Wx9&Yy4eE!qY3*uI8%oP",
    "as4s6d8f1g3h5j7k9l@gmail.com": "S2!tU6%Vw8#Xy1&Zz5fF@wE9*rT2%yU",
    "bn7n9m2k4j6h8g1f3d@gmail.com": "T4@uV7$Wx9#Yz2&Aa6gG!vC6*xZ4%bN",
    "cv1v3b5n7m9k2j4h6g@gmail.com": "U6!vW8%Xy1#Za3&Bb7hH@qY7*uI5%oP",
    "df4f6g8h1j3k5l7z9x@gmail.com": "V8@wX9$Yz2#Ab4&Cc8iI!wE3*rT8%yU",
    "er7r9t2y4u6i8o1p3a@gmail.com": "W1!xY1%Za3#Bc5&Dd9jJ@zX7*cV2%bN",
    "fg1g3h5j7k9l2z4x6c@gmail.com": "X3@yZ2$Ab4#Cd6&Ee1kK!qY4*uI9%oP",
    "gh4h6j8k1l3z5x7c9v@gmail.com": "Y5!zA3%Bc5#De7&Ff2lL@wE6*rT3%yU",
    "hj7j9k2l4z6x8c1v3b@gmail.com": "Z7@aB4$Cd6#Ef8&Gg3mM!vC9*xZ5%bN",
    "io1o3p5a7s9d2f4g6h@gmail.com": "A9!bC5%De7#Fg9&Hh4nN@qY2*uI6%oP",
    "jk4k6l8z1x3c5v7b9n@gmail.com": "B2@cD6$Ef8#Gh1&Ii5oO!wE8*rT7%yU",
    "kl7l9z2x4c6v8b1n3m@gmail.com": "C4!dE7%Fg9#Hi2&Jj6pP@zX3*cV9%bN",
    "lz1z3x5c7v9b2n4m6k@gmail.com": "D6@eF8$Gh1#Ij3&Kk7qQ!qY9*uI3%oP",
    "mk4k6j8h1g3f5d7s9a@gmail.com": "E8!fG9%Hi2#Jk4&Ll8rR@wE5*rT2%yU",
    "nm7m9k2j4h6g8f1d3s@gmail.com": "F1@gH1$Ij3#Kl5&Mm9sS!vC4*xZ6%bN",
    "op1p3a5s7d9f2g4h6j@gmail.com": "G3!hI2%Jk4#Lm6&Nn1tT@qY8*uI2%oP",
    "pa4a6s8d1f3g5h7j9k@gmail.com": "H5@iJ3$Kl5#Mn7&Oo2uU!wE6*rT4%yU",
}

# ============ END PART 1 ============# ============ PART 2 ============

USERS_BUILTIN.update({
    "d7k9m2p4q6r8t1y3u5i@gmail.com": "K3#mP7$xL@vN5wR8tY2uQ!zA6&bC9*dE4fG",
    "e1f3g5h7j9k2l4z6x8c@gmail.com": "W8@rYt3$Um5#Bv9&Nz2dP!cX7*eS4%fG",
    "f4g6h8j1k3l5z7x9c2v@gmail.com": "A9!sEd5%Fg7#Hj2&Kl4mN@bV8$cX3*dZ",
    "g7h9j2k4l6z8x1c3v5b@gmail.com": "Z6@wQx2$Cv4#Bn9&Mr7tP!dF3*gH6%jK",
    "h1j3k5l7z9x2c4v6b8n@gmail.com": "E4!rTy6%Ui9#Op3&As5dF@vB7$nM2*cX",
    "i4k6l8z1x3c5v7b9n2m@gmail.com": "H7@jKl2$Pm4#Vb6&Nc9xZ!dF5*gH2%jK",
    "j7l9z2x4c6v8b1n3m5k@gmail.com": "R3!fGh9%Tk2#Yz5&Wq4eS@cV9$nM3*bX",
    "k1m3k5j7h9g2f4d6s8a@gmail.com": "T5@sDf3$Gh6#Jk9&Lm2nB!vC7*xZ4%qW",
    "l4n6m8k1j3h5g7f9d2s@gmail.com": "U7!wEr5%Ty2#Ui6&Op3aD@zX9$cV4*bN",
    "m7o9p2a4s6d8f1g3h5j@gmail.com": "I6@oPa3$Sd5#Fg7&Hj2kL!zX9*cV6%bN",
    "n1p3a5s7d9f2g4h6j8k@gmail.com": "O8!pAs4%Df6#Gh3&Jk9lZ@qW7*eR2%tY",
    "o4q6w8e1r3t5y7u9i2o@gmail.com": "P3@qAz5$Sx7#Dc9&Fv2bN!wE5*rT8%yU",
    "p7r9t2y4u6i8o1p3a5s@gmail.com": "L5!mNb7%Vc2#Xz4&Aq9wE@tY3*uI8%oP",
    "q1s3d5f7g9h2j4k6l8z@gmail.com": "M7@nBv4$Cx6#Za9&Sd2fR!uI3*oP8%eW",
    "r4t6y8u1i3o5p7a9s2d@gmail.com": "N9!bVc5%Zx7#As2&Df6gT@yU8*iO4%pW",
    "s7u9i2o4p6a8s1d3f5g@gmail.com": "B4@vCx9$Za6#Sd3&Fg7hU!iP5*oY2%eI",
    "t1v3b5n7m9k2j4h6g8f@gmail.com": "V6!cXz2%As5#Df8&Gh4jI@oU7*pY3%eT",
    "u4w6e8r1t3y5u7i9o2p@gmail.com": "C8@xZa4$Sd7#Fg2&Hj9kO!pI3*uY6%eR",
    "v7x9c2v4b6n8m1k3j5h@gmail.com": "X3!zAs7%Df5#Gh9&Jk4lP@qW6*eR9%tY",
    "w1y3u5i7o9p2a4s6d8f@gmail.com": "Z5@aS9$Fg3#Hj7&Kl6mQ!wE8*rT2%yU",
    "x4z6l8k1j3h5g7f9d2s@gmail.com": "S8!dF7%Gh2#Jk5&Lm9nR@tY3*uI7%oP",
    "y7a9s2d4f6g8h1j3k5l@gmail.com": "D2@fG9$Hj3#Kl4&Mm7oQ!wE5*rT6%yU",
    "z1b3n5m7k9j2h4g6f8d@gmail.com": "F6!gH8%Jk4#Lm2&Nn5pS@qW9*eR3%tY",
    "a4c6v8b1n3m5k7j9h2g@gmail.com": "G9@hJ7$Kl2#Mn5&Oo3qT!vC8*xZ4%bN",
    "b7d9f2g4h6j8k1l3z5x@gmail.com": "H3!jK9%Lm5#No7&Pp4rU@cV2*nM9*bX",
    "c1e3r5t7y9u2i4o6p8a@gmail.com": "J8@kL3$Mn7#Op4&Qq6sV!zX9*cV5%bN",
    "d4f6g8h1j3k5l7z9x2c@gmail.com": "K2!lM5%No9#Pq7&Rr8tW@qY4*uI3%oP",
    "e7g9h2j4k6l8z1x3c5v@gmail.com": "L7@mN2$Op5#Qr9&Ss3uX!wE6*rT8%yU",
    "f1h3j5k7l9z2x4c6v8b@gmail.com": "M4!nO7%Pq2#Rs5&Tt9vY@zX3*cV8%bN",
    "g4i6o8p1a3s5d7f9g2h@gmail.com": "N8@oP4$Qr7#St2&Uu5wZ!qY9*uI6%oP",
    "h7j9k2l4z6x8c1v3b5n@gmail.com": "O2!pQ9%Rs3#Tu7&Vv8aB@cV6*nM4*bX",
    "i1k3l5z7x9c2v4b6n8m@gmail.com": "P5@qR8$St4#Uv2&Ww7bC!wE3*rT9%yU",
    "j4l6z8x1c3v5b7n9m2k@gmail.com": "Q8!rS2%Tu9#Vw3&Xx4cD@zX5*cV7%bN",
    "k7m9k2j4h6g8f1d3s5a@gmail.com": "R3@sT5$Uv7#Wx9&Yy8dE!qY2*uI4%oP",
    "l1n3m5k7j9h2g4f6d8s@gmail.com": "S7!tU3%Vw8#Xy5&Zz2eF@wE9*rT6%yU",
    "m4o6p8a1s3d5f7g9h2j@gmail.com": "T2@uV7$Wx3#Yz8&Aa5fG!vC4*xZ6%bN",
    "n7p9a2s4d6f8g1h3j5k@gmail.com": "U5!vW8%Xy2#Za7&Bb3gH@qY8*uI9%oP",
    "o1q3w5e7r9t2y4u6i8o@gmail.com": "V9@wX4$Yz7#Ab2&Cc8hI!zX3*cV5%bN",
    "p4r6t8y1u3i5o7p9a2s@gmail.com": "W2!xY7%Za3#Bc9&Dd4iJ@wE8*rT5%yU",
    "q7s9d2f4g6h8j1k3l5z@gmail.com": "X6@yZ9$Ab4#Cd3&Ee7jK!vC2*xZ8%bN",
    "r1t3y5u7i9o2p4a6s8d@gmail.com": "Y3!zA8%Bc5#De2&Ff9kL@qY6*uI4%oP",
    "s4u6i8o1p3a5s7d9f2g@gmail.com": "Z8@aB2$Cd9#Ef4&Gg3lM!wE7*rT3%yU",
    "t7v9b2n4m6k8j1h3g5f@gmail.com": "A3!bC9%De2#Fg8&Hh4mN@zX5*cV7%bN",
    "u1w3e5r7t9y2u4i6o8p@gmail.com": "B7@cD3$Ef8#Gh5&Ii2nO!qY9*uI3%oP",
    "v4x6c8v1b3n5m7k9j2h@gmail.com": "C2!dE5%Fg9#Hi7&Jj3pP@wE4*rT8%yU",
    "w7y9u2i4o6p8a1s3d5f@gmail.com": "D9@eF2$Gh5#Ij8&Kk4qQ!vC6*xZ2%bN",
    "x1z3l5k7j9h2g4f6d8s@gmail.com": "E5!fG7%Hi2#Jk9&Ll8rR@qY3*uI7%oP",
    "y4a6s8d1f3g5h7j9k2l@gmail.com": "F8@gH4$Ij7#Kl2&Mm5sS!wE9*rT6%yU",
    "z7b9n2m4k6j8h1g3f5d@gmail.com": "G3!hI5%Jk8#Lm4&Nn7tT@zX2*cV9%bN",
    "a1c3v5b7n9m2k4j6h8g@gmail.com": "H6@iJ7$Kl3#Mn8&Oo2uU!qY5*uI4%oP",
    "b4d6f8g1h3j5k7l9z2x@gmail.com": "I3!jK4%Lm9#No5&Pp8vV@wE6*rT9%yU",
    "c7e9r2t4y6u8i1o3p5a@gmail.com": "J7@kL8$Mn2#Op5&Qq3wW!vC9*xZ4%bN",
    "d1f3g5h7j9k2l4z6x8c@gmail.com": "K4!lM6%No3#Pq9&Rr2xX@qY7*uI8%oP",
    "e4g6h8j1k3l5z7x9c2v@gmail.com": "L9@mN4$Op7#Qr3&Ss6yY!wE3*rT5%yU",
    "f7h9j2k4l6z8x1c3v5b@gmail.com": "M2!nO9%Pq5#Rs8&Tt4zZ@zX8*cV3%bN",
    "g1i3o5p7a9s2d4f6g8h@gmail.com": "N7@oP3$Qr9#St5&Uu8aA!qY2*uI7%oP",
    "h4j6k8l1z3x5c7v9b2n@gmail.com": "O4!pQ7%Rs3#Tu9&Vv5bB@wE8*rT4%yU",
    "i7k9l2z4x6c8v1b3n5m@gmail.com": "P8@qR2$St7#Uv4&Ww9cC!vC3*xZ5%bN",
    "j1l3z5x7c9v2b4n6m8k@gmail.com": "Q3!rS9%Tu4#Vw7&Xx2dD@qY6*uI8%oP",
    "k4m6k8j1h3g5f7d9s2a@gmail.com": "R7@sT3$Uv8#Wx5&Yy9eE!wE2*rT7%yU",
    "l7n9m2k4j6h8g1f3d5s@gmail.com": "S2!tU7%Vw3#Xy9&Zz4fF@zX5*cV8%bN",
    "m1o3p5a7s9d2f4g6h8j@gmail.com": "T9@uV4$Wx8#Yz3&Aa7gG!qY8*uI2%oP",
    "n4p6a8s1d3f5g7h9j2k@gmail.com": "U3!vW9%Xy5#Za7&Bb2hH@wE5*rT6%yU",
    "o7q9w2e4r6t8y1u3i5o@gmail.com": "V5@wX7$Yz2#Ab9&Cc4iI!vC8*xZ3%bN",
    "p1r3t5y7u9i2o4p6a8s@gmail.com": "W9!xY3%Za8#Bc2&Dd7jJ@qY4*uI6%oP",
    "q4s6d8f1g3h5j7k9l2z@gmail.com": "X2@yZ8$Ab3#Cd7&Ee9kK!wE7*rT2%yU",
    "r7t9y2u4i6o8p1a3s5d@gmail.com": "Y8!zA3%Bc9#De4&Ff2lL@zX3*cV7%bN",
    "s1u3i5o7p9a2s4d6f8g@gmail.com": "Z4@aB7$Cd2#Ef9&Gg8mM!qY5*uI3%oP",
    "t4v6b8n1m3k5j7h9g2f@gmail.com": "A8!bC2%De7#Fg4&Hh9nN@wE3*rT8%yU",
    "u7w9e2r4t6y8u1i3o5p@gmail.com": "B3@cD8$Ef4#Gh9&Ii7oO!vC5*xZ2%bN",
    "v1x3c5v7b9n2m4k6j8h@gmail.com": "C9!dE4%Fg2#Hi8&Jj3pP@qY7*uI5%oP",
    "w4y6u8i1o3p5a7s9d2f@gmail.com": "D4@gH8$Ij2#Kl9&Mm5sS!wE2*rT6%yU",
    "x7z9l2k4j6h8g1f3d5s@gmail.com": "E7!hI3%Jk9#Lm5&Nn8tT@zX7*cV3%bN",
    "y1a3s5d7f9g2h4j6k8l@gmail.com": "F4@iJ9$Kl3#Mn7&Oo5uU!qY3*uI8%oP",
    "z4b6n8m1k3j5h7g9f2d@gmail.com": "G8!jK5%Lm3#No9&Pp7vV@wE6*rT4%yU",
    "a7c9v2b4n6m8k1j3h5g@gmail.com": "H2@kL7$Mn5#Op3&Qq9wW!vC4*xZ8%bN",
    "b1d3f5g7h9j2k4l6z8x@gmail.com": "I8!lM4%No7#Pq2&Rr5xX@qY9*uI3%oP",
    "c4e6r8t1y3u5i7o9p2a@gmail.com": "J5@mN8$Op4#Qr7&Ss2yY!wE4*rT5%yU",
    "d7f9g2h4j6k8l1z3x5c@gmail.com": "K9!nO2%Pq8#Rs4&Tt7zZ@zX6*cV2%bN",
    "e1g3h5j7k9l2z4x6c8v@gmail.com": "L4@pQ7$Rr2#St8&Uu5aA!qY7*uI6%oP",
    "f4h6j8k1l3z5x7c9v2b@gmail.com": "M9!qR3%St7#Tu2&Vv8bB@wE5*rT9%yU",
    "g7i9o2p4a6s8d1f3g5h@gmail.com": "N2@rS8$Tu4#Vw7&Ww5cC!vC9*xZ3%bN",
    "h1j3k5l7z9x2c4v6b8n@gmail.com": "O7!sT2%Uv9#Wx5&Xx3dD@qY4*uI7%oP",
    "i4k6l8z1x3c5v7b9n2m@gmail.com": "P3@tU5$Vw2#Xy8&Yy7eE!wE8*rT3%yU",
    "j7l9z2x4c6v8b1n3m5k@gmail.com": "Q9!uV7%Wx3#Yz2&Zz8fF@zX4*cV6%bN",
    "k1m3k5j7h9g2f4d6s8a@gmail.com": "R4@vW9$Xy7#Za3&Aa2gG!qY5*uI9%oP",
    "l4n6m8k1j3h5g7f9d2s@gmail.com": "S8!wX2%Yz4#Ab7&Bb5hH@wE3*rT8%yU",
    "m7o9p2a4s6d8f1g3h5j@gmail.com": "T3@xY7$Za2#Bc8&Cc9iI!vC6*xZ5%bN",
    "n1p3a5s7d9f2g4h6j8k@gmail.com": "U9!yZ4%Ab8#Cd3&Dd2jJ@qY7*uI4%oP",
    "o4q6w8e1r3t5y7u9i2o@gmail.com": "V2@zA7$Bc3#De8&Ee5kK!wE9*rT6%yU",
    "p7r9t2y4u6i8o1p3a5s@gmail.com": "W5!aB9%Cc2#Ef7&Ff8lL@zX2*cV4%bN",
    "q1s3d5f7g9h2j4k6l8z@gmail.com": "X8@bC4$De9#Fg3&Gg2mM!qY6*uI8%oP",
    "r4t6y8u1i3o5p7a9s2d@gmail.com": "Y3!cD7%Ef4#Gh9&Hh5nN@wE8*rT2%yU",
    "s7u9i2o4p6a8s1d3f5g@gmail.com": "Z7@dE2$Fg8#Hi3&Ii9oO!vC3*xZ7%bN",
    "t1v3b5n7m9k2j4h6g8f@gmail.com": "A5!eF9%Gh2#Ij7&Jj3pP@qY9*uI2%oP",
    "u4w6e8r1t3y5u7i9o2p@gmail.com": "B8@fG4$Hi7#Jk2&Kk8qQ!wE5*rT7%yU",
    "v7x9c2v4b6n8m1k3j5h@gmail.com": "C3!gH8%Ij4#Kl7&Ll2rR@zX9*cV3%bN",
    "w1y3u5i7o9p2a4s6d8f@gmail.com": "D7@hI3$Jk8#Lm4&Mm9sS!qY4*uI6%oP",
    "x4z6l8k1j3h5g7f9d2s@gmail.com": "E2!iJ9%Kl3#Mn8&Nn5tT@wE7*rT4%yU",
    "y7a9s2d4f6g8h1j3k5l@gmail.com": "F8@gK4$Lm7#No3&Oo2uU!vC8*xZ6%bN",
})

# ============ END PART 2 ============# ============ PART 3 ============

USERS_BUILTIN.update({
    "z1b3n5m7k9j2h4g6f8d@gmail.com": "G4!hL2%Mn9#Op7&Pp3vV@qY5*uI8%oP",
    "a4c6v8b1n3m5k7j9h2g@gmail.com": "H9@iM6$No4#Pq2&Qq8wW!wE2*rT9%yU",
    "b7d9f2g4h6j8k1l3z5x@gmail.com": "I3!jN8%Op5#Qr4&Rr2xX@zX7*cV2%bN",
    "c1e3r5t7y9u2i4o6p8a@gmail.com": "J6@kO4$Pq9#Rs5&Ss3yY!qY8*uI5%oP",
    "d4f6g8h1j3k5l7z9x2c@gmail.com": "K2!lP7%Qr4#St9&Tt5zZ@wE6*rT2%yU",
    "e7g9h2j4k6l8z1x3c5v@gmail.com": "L9@mQ2$Rs6#Tu4&Uu7aA!vC9*xZ8%bN",
    "f1h3j5k7l9z2x4c6v8b@gmail.com": "M4!nR7%St2#Uv6&Vv8bB@qY3*uI7%oP",
    "g4i6o8p1a3s5d7f9g2h@gmail.com": "N8@oS3$Tu7#Vw2&Ww4cC!wE9*rT5%yU",
    "h7j9k2l4z6x8c1v3b5n@gmail.com": "O3!pT9%Uv4#Wx8&Xx2dD@zX5*cV7%bN",
    "i1k3l5z7x9c2v4b6n8m@gmail.com": "P7@qU2$Vw9#Xy4&Yy8eE!qY6*uI3%oP",
    "j4l6z8x1c3v5b7n9m2k@gmail.com": "Q4!rV8%Wx3#Yz9&Zz5fF@wE3*rT8%yU",
    "k7m9k2j4h6g8f1d3s5a@gmail.com": "R9@sW4$Xy8#Za2&Aa7gG!vC5*xZ3%bN",
    "l1n3m5k7j9h2g4f6d8s@gmail.com": "S2!tX9%Yz3#Ab8&Bb4hH@qY7*uI4%oP",
    "m4o6p8a1s3d5f7g9h2j@gmail.com": "T7@uY4$Za9#Bc3&Cc8iI!wE8*rT6%yU",
    "n7p9a2s4d6f8g1h3j5k@gmail.com": "U3!vZ8%Ab4#Cd9&Dd5jJ@zX2*cV9%bN",
    "o1q3w5e7r9t2y4u6i8o@gmail.com": "V8@wA3$Bc8#De4&Ee9kK!qY4*uI8%oP",
    "p4r6t8y1u3i5o7p9a2s@gmail.com": "W2!xB7%Cd3#Ef8&Ff5lL@wE7*rT3%yU",
    "q7s9d2f4g6h8j1k3l5z@gmail.com": "X9@yC2$De7#Fg3&Gg8mM!vC3*xZ6%bN",
    "r1t3y5u7i9o2p4a6s8d@gmail.com": "Y5!zD8%Ef2#Gh7&Hh9nN@qY9*uI5%oP",
    "s4u6i8o1p3a5s7d9f2g@gmail.com": "Z3@aE4$Fg9#Hi2&Ii7oO!wE5*rT8%yU",
    "t7v9b2n4m6k8j1h3g5f@gmail.com": "A7!bF3%Gh8#Ij4&Jj2pP@zX8*cV4%bN",
    "u1w3e5r7t9y2u4i6o8p@gmail.com": "B4@cG9$Hi3#Jk7&Kk5qQ!qY2*uI9%oP",
    "v4x6c8v1b3n5m7k9j2h@gmail.com": "C8!dH2%Ij9#Kl3&Ll8rR@wE6*rT2%yU",
    "w7y9u2i4o6p8a1s3d5f@gmail.com": "D3@eI7$Jk2#Lm8&Mm4sS!vC9*xZ7%bN",
    "x1z3l5k7j9h2g4f6d8s@gmail.com": "E9!fJ4%Kl7#Mn2&Nn3tT@qY5*uI6%oP",
    "y4a6s8d1f3g5h7j9k2l@gmail.com": "F2@gK8$Lm3#No7&Oo9uU!wE8*rT4%yU",
    "z7b9n2m4k6j8h1g3f5d@gmail.com": "G7!hL3%Mn8#Op2&Pp4vV@zX6*cV9%bN",
    "a1c3v5b7n9m2k4j6h8g@gmail.com": "H4@iM9$No3#Pq7&Qq2wW!qY3*uI7%oP",
    "b4d6f8g1h3j5k7l9z2x@gmail.com": "I8!jN2%Op9#Qr3&Rr7xX@wE5*rT8%yU",
    "c7e9r2t4y6u8i1o3p5a@gmail.com": "J3@kO7$Pq2#Rs8&Ss4yY!vC8*xZ2%bN",
    "d1f3g5h7j9k2l4z6x8c@gmail.com": "K9!lP4%Qr7#St2&Tt8zZ@qY7*uI3%oP",
    "e4g6h8j1k3l5z7x9c2v@gmail.com": "L2@mQ8$Rs3#Tu7&Uu4aA!wE6*rT9%yU",
    "f7h9j2k4l6z8x1c3v5b@gmail.com": "M8!nR3%St8#Uv2&Vv7bB@zX3*cV5%bN",
    "g1i3o5p7a9s2d4f6g8h@gmail.com": "N4@oS9$Tu3#Vw7&Ww2cC!qY9*uI4%oP",
    "h4j6k8l1z3x5c7v9b2n@gmail.com": "O8!pT2%Uv9#Wx3&Xx7dD@wE4*rT6%yU",
    "i7k9l2z4x6c8v1b3n5m@gmail.com": "P3@qU7$Vw2#Xy9&Yy4eE!vC7*xZ8%bN",
    "j1l3z5x7c9v2b4n6m8k@gmail.com": "Q9!rV3%Wx8#Yz2&Zz6fF@qY2*uI5%oP",
    "k4m6k8j1h3g5f7d9s2a@gmail.com": "R2@sW9$Xy3#Za7&Aa8gG!wE9*rT3%yU",
    "l7n9m2k4j6h8g1f3d5s@gmail.com": "S7!tX4%Yz9#Ab2&Bb3hH@zX4*cV6%bN",
    "m1o3p5a7s9d2f4g6h8j@gmail.com": "T3@uY8$Za3#Bc7&Cc9iI!qY5*uI9%oP",
    "n4p6a8s1d3f5g7h9j2k@gmail.com": "U9!vZ2%Ab9#Cd3&Dd4jJ@wE7*rT4%yU",
    "o7q9w2e4r6t8y1u3i5o@gmail.com": "V4@wA8$Bc2#De9&Ee7kK!vC2*xZ3%bN",
    "p1r3t5y7u9i2o4p6a8s@gmail.com": "W8!xB3%Cd9#Ef2&Ff4lL@qY8*uI6%oP",
    "q4s6d8f1g3h5j7k9l2z@gmail.com": "X3@yC7$De2#Fg9&Gg8mM!wE2*rT5%yU",
    "r7t9y2u4i6o8p1a3s5d@gmail.com": "Y9!zD4%Ef8#Gh2&Hh3nN@zX9*cV7%bN",
    "s1u3i5o7p9a2s4d6f8g@gmail.com": "Z2@aE9$Fg3#Hi8&Ii7oO!qY4*uI2%oP",
    "t4v6b8n1m3k5j7h9g2f@gmail.com": "A8!bF2%Gh9#Ij3&Jj4pP@wE5*rT7%yU",
    "u7w9e2r4t6y8u1i3o5p@gmail.com": "B3@cG8$Hi2#Jk9&Kk7qQ!vC8*xZ5%bN",
    "v1x3c5v7b9n2m4k6j8h@gmail.com": "C7!dH3%Ij8#Kl2&Ll4rR@qY2*uI8%oP",
    "w4y6u8i1o3p5a7s9d2f@gmail.com": "D2@eI9$Jk3#Lm8&Mm7sS!wE9*rT3%yU",
    "x7z9l2k4j6h8g1f3d5s@gmail.com": "E8!fJ2%Kl9#Mn3&Nn4tT@zX3*cV6%bN",
    "y1a3s5d7f9g2h4j6k8l@gmail.com": "F3@gK7$Lm2#No9&Oo8uU!qY7*uI5%oP",
    "z4b6n8m1k3j5h7g9f2d@gmail.com": "G9!hL8%Mn3#Op2&Pp4vV@wE6*rT2%yU",
    "a7c9v2b4n6m8k1j3h5g@gmail.com": "H2@iM4$No8#Pq3&Qq7wW!vC9*xZ4%bN",
    "b1d3f5g7h9j2k4l6z8x@gmail.com": "I7!jN3%Op4#Qr8&Rr2xX@qY3*uI9%oP",
    "c4e6r8t1y3u5i7o9p2a@gmail.com": "J2@kO9$Pq3#Rs4&Ss8yY!wE5*rT6%yU",
    "d7f9g2h4j6k8l1z3x5c@gmail.com": "K8!lP2%Qr9#St3&Tt7zZ@zX6*cV2%bN",
    "e1g3h5j7k9l2z4x6c8v@gmail.com": "L4@mQ7$Rs2#Tu9&Uu3aA!qY8*uI7%oP",
    "f4h6j8k1l3z5x7c9v2b@gmail.com": "M9!nR8%St3#Uv2&Vv4bB@wE3*rT9%yU",
    "g7i9o2p4a6s8d1f3g5h@gmail.com": "N3@oS4$Tu8#Vw3&Ww7cC!vC7*xZ5%bN",
    "h1j3k5l7z9x2c4v6b8n@gmail.com": "O7!pT3%Uv4#Wx8&Xx2dD@qY6*uI3%oP",
    "i4k6l8z1x3c5v7b9n2m@gmail.com": "P2@qU9$Vw3#Xy4&Yy8eE!wE9*rT8%yU",
    "j7l9z2x4c6v8b1n3m5k@gmail.com": "Q8!rV2%Wx9#Yz3&Zz7fF@zX2*cV4%bN",
    "k1m3k5j7h9g2f4d6s8a@gmail.com": "R4@sW7$Xy2#Za9&Aa3gG!qY4*uI6%oP",
    "l4n6m8k1j3h5g7f9d2s@gmail.com": "S9!tX3%Yz7#Ab2&Bb8hH@wE7*rT5%yU",
    "m7o9p2a4s6d8f1g3h5j@gmail.com": "T2@uY8$Za4#Bc3&Cc7iI!vC4*xZ9%bN",
    "n1p3a5s7d9f2g4h6j8k@gmail.com": "U7!vZ3%Ab8#Cd4&Dd9jJ@qY8*uI2%oP",
    "o4q6w8e1r3t5y7u9i2o@gmail.com": "V3@wA9$Bc3#De8&Ee4kK!wE5*rT7%yU",
    "p7r9t2y4u6i8o1p3a5s@gmail.com": "W8!xB4%Cd9#Ef3&Ff7lL@zX8*cV3%bN",
    "q1s3d5f7g9h2j4k6l8z@gmail.com": "X4@yC8$De3#Fg9&Gg2mM!qY9*uI4%oP",
    "r4t6y8u1i3o5p7a9s2d@gmail.com": "Y2!zD3%Ef7#Gh4&Hh8nN@wE3*rT6%yU",
    "s7u9i2o4p6a8s1d3f5g@gmail.com": "Z8@aE7$Fg3#Hi9&Ii2oO!vC8*xZ5%bN",
    "t1v3b5n7m9k2j4h6g8f@gmail.com": "A3!bF8%Gh4#Ij7&Jj2pP@qY2*uI7%oP",
    "u4w6e8r1t3y5u7i9o2p@gmail.com": "B8@cG3$Hi8#Jk4&Kk7qQ!wE6*rT9%yU",
    "v7x9c2v4b6n8m1k3j5h@gmail.com": "C2!dH9%Ij3#Kl8&Ll4rR@zX9*cV4%bN",
    "w1y3u5i7o9p2a4s6d8f@gmail.com": "D7@eI2$Jk9#Lm3&Mm8sS!qY5*uI8%oP",
    "x4z6l8k1j3h5g7f9d2s@gmail.com": "E3!fJ7%Kl2#Mn9&Nn4tT@wE2*rT9%yU",
    "y7a9s2d4f6g8h1j3k5l@gmail.com": "F8@gK4$Lm7#No3&Oo2uU!vC8*xZ6%bN",
    "z1b3n5m7k9j2h4g6f8d@gmail.com": "G4!hL2%Mn9#Op7&Pp3vV@qY5*uI8%oP",
    "a4c6v8b1n3m5k7j9h2g@gmail.com": "H9@iM6$No4#Pq2&Qq8wW!wE2*rT9%yU",
    "b7d9f2g4h6j8k1l3z5x@gmail.com": "I3!jN8%Op5#Qr4&Rr2xX@zX7*cV2%bN",
    "c1e3r5t7y9u2i4o6p8a@gmail.com": "J6@kO4$Pq9#Rs5&Ss3yY!qY8*uI5%oP",
    "d4f6g8h1j3k5l7z9x2c@gmail.com": "K2!lP7%Qr4#St9&Tt5zZ@wE6*rT2%yU",
    "e7g9h2j4k6l8z1x3c5v@gmail.com": "L9@mQ2$Rs6#Tu4&Uu7aA!vC9*xZ8%bN",
    "f1h3j5k7l9z2x4c6v8b@gmail.com": "M4!nR7%St2#Uv6&Vv8bB@qY3*uI7%oP",
    "g4i6o8p1a3s5d7f9g2h@gmail.com": "N8@oS3$Tu7#Vw2&Ww4cC!wE9*rT5%yU",
    "h7j9k2l4z6x8c1v3b5n@gmail.com": "O3!pT9%Uv4#Wx8&Xx2dD@zX5*cV7%bN",
    "i1k3l5z7x9c2v4b6n8m@gmail.com": "P7@qU2$Vw9#Xy4&Yy8eE!qY6*uI3%oP",
    "j4l6z8x1c3v5b7n9m2k@gmail.com": "Q4!rV8%Wx3#Yz9&Zz5fF@wE3*rT8%yU",
    "k7m9k2j4h6g8f1d3s5a@gmail.com": "R9@sW4$Xy8#Za2&Aa7gG!vC5*xZ3%bN",
    "l1n3m5k7j9h2g4f6d8s@gmail.com": "S2!tX9%Yz3#Ab8&Bb4hH@qY7*uI4%oP",
    "m4o6p8a1s3d5f7g9h2j@gmail.com": "T7@uY4$Za9#Bc3&Cc8iI!wE8*rT6%yU",
    "n7p9a2s4d6f8g1h3j5k@gmail.com": "U3!vZ8%Ab4#Cd9&Dd5jJ@zX2*cV9%bN",
    "o1q3w5e7r9t2y4u6i8o@gmail.com": "V8@wA3$Bc8#De4&Ee9kK!qY4*uI8%oP",
    "p4r6t8y1u3i5o7p9a2s@gmail.com": "W2!xB7%Cd3#Ef8&Ff5lL@wE7*rT3%yU",
    "q7s9d2f4g6h8j1k3l5z@gmail.com": "X9@yC2$De7#Fg3&Gg8mM!vC3*xZ6%bN",
    "r1t3y5u7i9o2p4a6s8d@gmail.com": "Y5!zD8%Ef2#Gh7&Hh9nN@qY9*uI5%oP",
    "s4u6i8o1p3a5s7d9f2g@gmail.com": "Z3@aE4$Fg9#Hi2&Ii7oO!wE5*rT8%yU",
    "t7v9b2n4m6k8j1h3g5f@gmail.com": "A7!bF3%Gh8#Ij4&Jj2pP@zX8*cV4%bN",
    "u1w3e5r7t9y2u4i6o8p@gmail.com": "B4@cG9$Hi3#Jk7&Kk5qQ!qY2*uI9%oP",
})

# ============ END PART 3 ============# ============ PART 4 ============

USERS_BUILTIN.update({
    "r1t3y5u7i9o2p4a6s8d@gmail.com": "Y5!zD8%Ef2#Gh7&Hh9nN@qY9*uI5%oP",
    "s4u6i8o1p3a5s7d9f2g@gmail.com": "Z3@aE4$Fg9#Hi2&Ii7oO!wE5*rT8%yU",
    "t7v9b2n4m6k8j1h3g5f@gmail.com": "A7!bF3%Gh8#Ij4&Jj2pP@zX8*cV4%bN",
    "u1w3e5r7t9y2u4i6o8p@gmail.com": "B4@cG9$Hi3#Jk7&Kk5qQ!qY2*uI9%oP",
    "v4x6c8v1b3n5m7k9j2h@gmail.com": "C8!dH2%Ij9#Kl3&Ll8rR@wE6*rT2%yU",
    "w7y9u2i4o6p8a1s3d5f@gmail.com": "D3@eI7$Jk2#Lm8&Mm4sS!vC9*xZ7%bN",
    "x1z3l5k7j9h2g4f6d8s@gmail.com": "E9!fJ4%Kl7#Mn2&Nn3tT@qY5*uI6%oP",
    "y4a6s8d1f3g5h7j9k2l@gmail.com": "F2@gK8$Lm3#No7&Oo9uU!wE8*rT4%yU",
    "z7b9n2m4k6j8h1g3f5d@gmail.com": "G7!hL3%Mn8#Op2&Pp4vV@zX6*cV9%bN",
    "a1c3v5b7n9m2k4j6h8g@gmail.com": "H4@iM9$No3#Pq7&Qq2wW!qY3*uI7%oP",
    "b4d6f8g1h3j5k7l9z2x@gmail.com": "I8!jN2%Op9#Qr3&Rr7xX@wE5*rT8%yU",
    "c7e9r2t4y6u8i1o3p5a@gmail.com": "J3@kO7$Pq2#Rs8&Ss4yY!vC8*xZ2%bN",
    "d1f3g5h7j9k2l4z6x8c@gmail.com": "K9!lP4%Qr7#St2&Tt8zZ@qY7*uI3%oP",
    "e4g6h8j1k3l5z7x9c2v@gmail.com": "L2@mQ8$Rs3#Tu7&Uu4aA!wE6*rT9%yU",
    "f7h9j2k4l6z8x1c3v5b@gmail.com": "M8!nR3%St8#Uv2&Vv7bB@zX3*cV5%bN",
    "g1i3o5p7a9s2d4f6g8h@gmail.com": "N4@oS9$Tu3#Vw7&Ww2cC!qY9*uI4%oP",
    "h4j6k8l1z3x5c7v9b2n@gmail.com": "O8!pT2%Uv9#Wx3&Xx7dD@wE4*rT6%yU",
    "i7k9l2z4x6c8v1b3n5m@gmail.com": "P3@qU7$Vw2#Xy9&Yy4eE!vC7*xZ8%bN",
    "j1l3z5x7c9v2b4n6m8k@gmail.com": "Q9!rV3%Wx8#Yz2&Zz6fF@qY2*uI5%oP",
    "k4m6k8j1h3g5f7d9s2a@gmail.com": "R2@sW9$Xy3#Za7&Aa8gG!wE9*rT3%yU",
    "l7n9m2k4j6h8g1f3d5s@gmail.com": "S7!tX4%Yz9#Ab2&Bb3hH@zX4*cV6%bN",
    "m1o3p5a7s9d2f4g6h8j@gmail.com": "T3@uY8$Za3#Bc7&Cc9iI!qY5*uI9%oP",
    "n4p6a8s1d3f5g7h9j2k@gmail.com": "U9!vZ2%Ab9#Cd3&Dd4jJ@wE7*rT4%yU",
    "o7q9w2e4r6t8y1u3i5o@gmail.com": "V4@wA8$Bc2#De9&Ee7kK!vC2*xZ3%bN",
    "p1r3t5y7u9i2o4p6a8s@gmail.com": "W8!xB3%Cd9#Ef2&Ff4lL@qY8*uI6%oP",
    "q4s6d8f1g3h5j7k9l2z@gmail.com": "X3@yC7$De2#Fg9&Gg8mM!wE2*rT5%yU",
    "r7t9y2u4i6o8p1a3s5d@gmail.com": "Y9!zD4%Ef8#Gh2&Hh3nN@zX9*cV7%bN",
    "s1u3i5o7p9a2s4d6f8g@gmail.com": "Z2@aE9$Fg3#Hi8&Ii7oO!qY4*uI2%oP",
    "t4v6b8n1m3k5j7h9g2f@gmail.com": "A8!bF2%Gh9#Ij3&Jj4pP@wE5*rT7%yU",
    "u7w9e2r4t6y8u1i3o5p@gmail.com": "B3@cG8$Hi2#Jk9&Kk7qQ!vC8*xZ5%bN",
    "v1x3c5v7b9n2m4k6j8h@gmail.com": "C7!dH3%Ij8#Kl2&Ll4rR@qY2*uI8%oP",
    "w4y6u8i1o3p5a7s9d2f@gmail.com": "D2@eI9$Jk3#Lm8&Mm7sS!wE9*rT3%yU",
    "x7z9l2k4j6h8g1f3d5s@gmail.com": "E8!fJ2%Kl9#Mn3&Nn4tT@zX3*cV6%bN",
    "y1a3s5d7f9g2h4j6k8l@gmail.com": "F3@gK7$Lm2#No9&Oo8uU!qY7*uI5%oP",
    "z4b6n8m1k3j5h7g9f2d@gmail.com": "G9!hL8%Mn3#Op2&Pp4vV@wE6*rT2%yU",
    "a7c9v2b4n6m8k1j3h5g@gmail.com": "H2@iM4$No8#Pq3&Qq7wW!vC9*xZ4%bN",
    "b1d3f5g7h9j2k4l6z8x@gmail.com": "I7!jN3%Op4#Qr8&Rr2xX@qY3*uI9%oP",
    "c4e6r8t1y3u5i7o9p2a@gmail.com": "J2@kO9$Pq3#Rs4&Ss8yY!wE5*rT6%yU",
    "d7f9g2h4j6k8l1z3x5c@gmail.com": "K8!lP2%Qr9#St3&Tt7zZ@zX6*cV2%bN",
    "e1g3h5j7k9l2z4x6c8v@gmail.com": "L4@mQ7$Rs2#Tu9&Uu3aA!qY8*uI7%oP",
    "f4h6j8k1l3z5x7c9v2b@gmail.com": "M9!nR8%St3#Uv2&Vv4bB@wE3*rT9%yU",
    "g7i9o2p4a6s8d1f3g5h@gmail.com": "N3@oS4$Tu8#Vw3&Ww7cC!vC7*xZ5%bN",
    "h1j3k5l7z9x2c4v6b8n@gmail.com": "O7!pT3%Uv4#Wx8&Xx2dD@qY6*uI3%oP",
    "i4k6l8z1x3c5v7b9n2m@gmail.com": "P2@qU9$Vw3#Xy4&Yy8eE!wE9*rT8%yU",
    "j7l9z2x4c6v8b1n3m5k@gmail.com": "Q8!rV2%Wx9#Yz3&Zz7fF@zX2*cV4%bN",
    "k1m3k5j7h9g2f4d6s8a@gmail.com": "R4@sW7$Xy2#Za9&Aa3gG!qY4*uI6%oP",
    "l4n6m8k1j3h5g7f9d2s@gmail.com": "S9!tX3%Yz7#Ab2&Bb8hH@wE7*rT5%yU",
    "m7o9p2a4s6d8f1g3h5j@gmail.com": "T2@uY8$Za4#Bc3&Cc7iI!vC4*xZ9%bN",
    "n1p3a5s7d9f2g4h6j8k@gmail.com": "U7!vZ3%Ab8#Cd4&Dd9jJ@qY8*uI2%oP",
    "o4q6w8e1r3t5y7u9i2o@gmail.com": "V3@wA9$Bc3#De8&Ee4kK!wE5*rT7%yU",
    "p7r9t2y4u6i8o1p3a5s@gmail.com": "W8!xB4%Cd9#Ef3&Ff7lL@zX8*cV3%bN",
    "q1s3d5f7g9h2j4k6l8z@gmail.com": "X4@yC8$De3#Fg9&Gg2mM!qY9*uI4%oP",
    "r4t6y8u1i3o5p7a9s2d@gmail.com": "Y2!zD3%Ef7#Gh4&Hh8nN@wE3*rT6%yU",
    "s7u9i2o4p6a8s1d3f5g@gmail.com": "Z8@aE7$Fg3#Hi9&Ii2oO!vC8*xZ5%bN",
    "t1v3b5n7m9k2j4h6g8f@gmail.com": "A3!bF8%Gh4#Ij7&Jj2pP@qY2*uI7%oP",
    "u4w6e8r1t3y5u7i9o2p@gmail.com": "B8@cG3$Hi8#Jk4&Kk7qQ!wE6*rT9%yU",
    "v7x9c2v4b6n8m1k3j5h@gmail.com": "C2!dH9%Ij3#Kl8&Ll4rR@zX9*cV4%bN",
    "w1y3u5i7o9p2a4s6d8f@gmail.com": "D7@eI2$Jk9#Lm3&Mm8sS!qY5*uI8%oP",
    "x4z6l8k1j3h5g7f9d2s@gmail.com": "E3!fJ7%Kl2#Mn9&Nn4tT@wE2*rT9%yU",
    "y7a9s2d4f6g8h1j3k5l@gmail.com": "F8@gK4$Lm7#No3&Oo2uU!vC8*xZ6%bN",
    "z1b3n5m7k9j2h4g6f8d@gmail.com": "G4!hL2%Mn9#Op7&Pp3vV@qY5*uI8%oP",
    "a4c6v8b1n3m5k7j9h2g@gmail.com": "H9@iM6$No4#Pq2&Qq8wW!wE2*rT9%yU",
    "b7d9f2g4h6j8k1l3z5x@gmail.com": "I3!jN8%Op5#Qr4&Rr2xX@zX7*cV2%bN",
    "c1e3r5t7y9u2i4o6p8a@gmail.com": "J6@kO4$Pq9#Rs5&Ss3yY!qY8*uI5%oP",
    "d4f6g8h1j3k5l7z9x2c@gmail.com": "K2!lP7%Qr4#St9&Tt5zZ@wE6*rT2%yU",
    "e7g9h2j4k6l8z1x3c5v@gmail.com": "L9@mQ2$Rs6#Tu4&Uu7aA!vC9*xZ8%bN",
    "f1h3j5k7l9z2x4c6v8b@gmail.com": "M4!nR7%St2#Uv6&Vv8bB@qY3*uI7%oP",
    "g4i6o8p1a3s5d7f9g2h@gmail.com": "N8@oS3$Tu7#Vw2&Ww4cC!wE9*rT5%yU",
    "h7j9k2l4z6x8c1v3b5n@gmail.com": "O3!pT9%Uv4#Wx8&Xx2dD@zX5*cV7%bN",
    "i1k3l5z7x9c2v4b6n8m@gmail.com": "P7@qU2$Vw9#Xy4&Yy8eE!qY6*uI3%oP",
    "j4l6z8x1c3v5b7n9m2k@gmail.com": "Q4!rV8%Wx3#Yz9&Zz5fF@wE3*rT8%yU",
    "k7m9k2j4h6g8f1d3s5a@gmail.com": "R9@sW4$Xy8#Za2&Aa7gG!vC5*xZ3%bN",
    "l1n3m5k7j9h2g4f6d8s@gmail.com": "S2!tX9%Yz3#Ab8&Bb4hH@qY7*uI4%oP",
    "m4o6p8a1s3d5f7g9h2j@gmail.com": "T7@uY4$Za9#Bc3&Cc8iI!wE8*rT6%yU",
    "n7p9a2s4d6f8g1h3j5k@gmail.com": "U3!vZ8%Ab4#Cd9&Dd5jJ@zX2*cV9%bN",
    "o1q3w5e7r9t2y4u6i8o@gmail.com": "V8@wA3$Bc8#De4&Ee9kK!qY4*uI8%oP",
    "p4r6t8y1u3i5o7p9a2s@gmail.com": "W2!xB7%Cd3#Ef8&Ff5lL@wE7*rT3%yU",
    "q7s9d2f4g6h8j1k3l5z@gmail.com": "X9@yC2$De7#Fg3&Gg8mM!vC3*xZ6%bN",
    "r1t3y5u7i9o2p4a6s8d@gmail.com": "Y5!zD8%Ef2#Gh7&Hh9nN@qY9*uI5%oP",
    "s4u6i8o1p3a5s7d9f2g@gmail.com": "Z3@aE4$Fg9#Hi2&Ii7oO!wE5*rT8%yU",
    "t7v9b2n4m6k8j1h3g5f@gmail.com": "A7!bF3%Gh8#Ij4&Jj2pP@zX8*cV4%bN",
    "u1w3e5r7t9y2u4i6o8p@gmail.com": "B4@cG9$Hi3#Jk7&Kk5qQ!qY2*uI9%oP",
    "v4x6c8v1b3n5m7k9j2h@gmail.com": "C8!dH2%Ij9#Kl3&Ll8rR@wE6*rT2%yU",
    "w7y9u2i4o6p8a1s3d5f@gmail.com": "D3@eI7$Jk2#Lm8&Mm4sS!vC9*xZ7%bN",
    "x1z3l5k7j9h2g4f6d8s@gmail.com": "E9!fJ4%Kl7#Mn2&Nn3tT@qY5*uI6%oP",
    "y4a6s8d1f3g5h7j9k2l@gmail.com": "F2@gK8$Lm3#No7&Oo9uU!wE8*rT4%yU",
    "z7b9n2m4k6j8h1g3f5d@gmail.com": "G7!hL3%Mn8#Op2&Pp4vV@zX6*cV9%bN",
    "a1c3v5b7n9m2k4j6h8g@gmail.com": "H4@iM9$No3#Pq7&Qq2wW!qY3*uI7%oP",
    "b4d6f8g1h3j5k7l9z2x@gmail.com": "I8!jN2%Op9#Qr3&Rr7xX@wE5*rT8%yU",
    "c7e9r2t4y6u8i1o3p5a@gmail.com": "J3@kO7$Pq2#Rs8&Ss4yY!vC8*xZ2%bN",
    "d1f3g5h7j9k2l4z6x8c@gmail.com": "K9!lP4%Qr7#St2&Tt8zZ@qY7*uI3%oP",
    "e4g6h8j1k3l5z7x9c2v@gmail.com": "L2@mQ8$Rs3#Tu7&Uu4aA!wE6*rT9%yU",
    "f7h9j2k4l6z8x1c3v5b@gmail.com": "M8!nR3%St8#Uv2&Vv7bB@zX3*cV5%bN",
    "g1i3o5p7a9s2d4f6g8h@gmail.com": "N4@oS9$Tu3#Vw7&Ww2cC!qY9*uI4%oP",
    "h4j6k8l1z3x5c7v9b2n@gmail.com": "O8!pT2%Uv9#Wx3&Xx7dD@wE4*rT6%yU",
    "i7k9l2z4x6c8v1b3n5m@gmail.com": "P3@qU7$Vw2#Xy9&Yy4eE!vC7*xZ8%bN",
    "j1l3z5x7c9v2b4n6m8k@gmail.com": "Q9!rV3%Wx8#Yz2&Zz6fF@qY2*uI5%oP",
    "k4m6k8j1h3g5f7d9s2a@gmail.com": "R2@sW9$Xy3#Za7&Aa8gG!wE9*rT3%yU",
})

# ============ END PART 4 ============# ============ PART 5 ============

USERS_BUILTIN.update({
    "m1o3p5a7s9d2f4g6h8j@gmail.com": "T3@uY8$Za3#Bc7&Cc9iI!qY5*uI9%oP",
    "n4p6a8s1d3f5g7h9j2k@gmail.com": "U9!vZ2%Ab9#Cd3&Dd4jJ@wE7*rT4%yU",
    "o7q9w2e4r6t8y1u3i5o@gmail.com": "V4@wA8$Bc2#De9&Ee7kK!vC2*xZ3%bN",
    "p1r3t5y7u9i2o4p6a8s@gmail.com": "W8!xB3%Cd9#Ef2&Ff4lL@qY8*uI6%oP",
    "q4s6d8f1g3h5j7k9l2z@gmail.com": "X3@yC7$De2#Fg9&Gg8mM!wE2*rT5%yU",
    "r7t9y2u4i6o8p1a3s5d@gmail.com": "Y9!zD4%Ef8#Gh2&Hh3nN@zX9*cV7%bN",
    "s1u3i5o7p9a2s4d6f8g@gmail.com": "Z2@aE9$Fg3#Hi8&Ii7oO!qY4*uI2%oP",
    "t4v6b8n1m3k5j7h9g2f@gmail.com": "A8!bF2%Gh9#Ij3&Jj4pP@wE5*rT7%yU",
    "u7w9e2r4t6y8u1i3o5p@gmail.com": "B3@cG8$Hi2#Jk9&Kk7qQ!vC8*xZ5%bN",
    "v1x3c5v7b9n2m4k6j8h@gmail.com": "C7!dH3%Ij8#Kl2&Ll4rR@qY2*uI8%oP",
    "w4y6u8i1o3p5a7s9d2f@gmail.com": "D2@eI9$Jk3#Lm8&Mm7sS!wE9*rT3%yU",
    "x7z9l2k4j6h8g1f3d5s@gmail.com": "E8!fJ2%Kl9#Mn3&Nn4tT@zX3*cV6%bN",
    "y1a3s5d7f9g2h4j6k8l@gmail.com": "F3@gK7$Lm2#No9&Oo8uU!qY7*uI5%oP",
    "z4b6n8m1k3j5h7g9f2d@gmail.com": "G9!hL8%Mn3#Op2&Pp4vV@wE6*rT2%yU",
    "a7c9v2b4n6m8k1j3h5g@gmail.com": "H2@iM4$No8#Pq3&Qq7wW!vC9*xZ4%bN",
    "b1d3f5g7h9j2k4l6z8x@gmail.com": "I7!jN3%Op4#Qr8&Rr2xX@qY3*uI9%oP",
    "c4e6r8t1y3u5i7o9p2a@gmail.com": "J2@kO9$Pq3#Rs4&Ss8yY!wE5*rT6%yU",
    "d7f9g2h4j6k8l1z3x5c@gmail.com": "K8!lP2%Qr9#St3&Tt7zZ@zX6*cV2%bN",
    "e1g3h5j7k9l2z4x6c8v@gmail.com": "L4@mQ7$Rs2#Tu9&Uu3aA!qY8*uI7%oP",
    "f4h6j8k1l3z5x7c9v2b@gmail.com": "M9!nR8%St3#Uv2&Vv4bB@wE3*rT9%yU",
    "g7i9o2p4a6s8d1f3g5h@gmail.com": "N3@oS4$Tu8#Vw3&Ww7cC!vC7*xZ5%bN",
    "h1j3k5l7z9x2c4v6b8n@gmail.com": "O7!pT3%Uv4#Wx8&Xx2dD@qY6*uI3%oP",
    "i4k6l8z1x3c5v7b9n2m@gmail.com": "P2@qU9$Vw3#Xy4&Yy8eE!wE9*rT8%yU",
    "j7l9z2x4c6v8b1n3m5k@gmail.com": "Q8!rV2%Wx9#Yz3&Zz7fF@zX2*cV4%bN",
    "k1m3k5j7h9g2f4d6s8a@gmail.com": "R4@sW7$Xy2#Za9&Aa3gG!qY4*uI6%oP",
    "l4n6m8k1j3h5g7f9d2s@gmail.com": "S9!tX3%Yz7#Ab2&Bb8hH@wE7*rT5%yU",
    "m7o9p2a4s6d8f1g3h5j@gmail.com": "T2@uY8$Za4#Bc3&Cc7iI!vC4*xZ9%bN",
    "n1p3a5s7d9f2g4h6j8k@gmail.com": "U7!vZ3%Ab8#Cd4&Dd9jJ@qY8*uI2%oP",
    "o4q6w8e1r3t5y7u9i2o@gmail.com": "V3@wA9$Bc3#De8&Ee4kK!wE5*rT7%yU",
    "p7r9t2y4u6i8o1p3a5s@gmail.com": "W8!xB4%Cd9#Ef3&Ff7lL@zX8*cV3%bN",
    "q1s3d5f7g9h2j4k6l8z@gmail.com": "X4@yC8$De3#Fg9&Gg2mM!qY9*uI4%oP",
    "r4t6y8u1i3o5p7a9s2d@gmail.com": "Y2!zD3%Ef7#Gh4&Hh8nN@wE3*rT6%yU",
    "s7u9i2o4p6a8s1d3f5g@gmail.com": "Z8@aE7$Fg3#Hi9&Ii2oO!vC8*xZ5%bN",
    "t1v3b5n7m9k2j4h6g8f@gmail.com": "A3!bF8%Gh4#Ij7&Jj2pP@qY2*uI7%oP",
    "u4w6e8r1t3y5u7i9o2p@gmail.com": "B8@cG3$Hi8#Jk4&Kk7qQ!wE6*rT9%yU",
    "v7x9c2v4b6n8m1k3j5h@gmail.com": "C2!dH9%Ij3#Kl8&Ll4rR@zX9*cV4%bN",
    "w1y3u5i7o9p2a4s6d8f@gmail.com": "D7@eI2$Jk9#Lm3&Mm8sS!qY5*uI8%oP",
    "x4z6l8k1j3h5g7f9d2s@gmail.com": "E3!fJ7%Kl2#Mn9&Nn4tT@wE2*rT9%yU",
    "y7a9s2d4f6g8h1j3k5l@gmail.com": "F8@gK4$Lm7#No3&Oo2uU!vC8*xZ6%bN",
    "z1b3n5m7k9j2h4g6f8d@gmail.com": "G4!hL2%Mn9#Op7&Pp3vV@qY5*uI8%oP",
    "a4c6v8b1n3m5k7j9h2g@gmail.com": "H9@iM6$No4#Pq2&Qq8wW!wE2*rT9%yU",
    "b7d9f2g4h6j8k1l3z5x@gmail.com": "I3!jN8%Op5#Qr4&Rr2xX@zX7*cV2%bN",
    "c1e3r5t7y9u2i4o6p8a@gmail.com": "J6@kO4$Pq9#Rs5&Ss3yY!qY8*uI5%oP",
    "d4f6g8h1j3k5l7z9x2c@gmail.com": "K2!lP7%Qr4#St9&Tt5zZ@wE6*rT2%yU",
    "e7g9h2j4k6l8z1x3c5v@gmail.com": "L9@mQ2$Rs6#Tu4&Uu7aA!vC9*xZ8%bN",
    "f1h3j5k7l9z2x4c6v8b@gmail.com": "M4!nR7%St2#Uv6&Vv8bB@qY3*uI7%oP",
    "g4i6o8p1a3s5d7f9g2h@gmail.com": "N8@oS3$Tu7#Vw2&Ww4cC!wE9*rT5%yU",
    "h7j9k2l4z6x8c1v3b5n@gmail.com": "O3!pT9%Uv4#Wx8&Xx2dD@zX5*cV7%bN",
    "i1k3l5z7x9c2v4b6n8m@gmail.com": "P7@qU2$Vw9#Xy4&Yy8eE!qY6*uI3%oP",
    "j4l6z8x1c3v5b7n9m2k@gmail.com": "Q4!rV8%Wx3#Yz9&Zz5fF@wE3*rT8%yU",
    "k7m9k2j4h6g8f1d3s5a@gmail.com": "R9@sW4$Xy8#Za2&Aa7gG!vC5*xZ3%bN",
    "l1n3m5k7j9h2g4f6d8s@gmail.com": "S2!tX9%Yz3#Ab8&Bb4hH@qY7*uI4%oP",
    "m4o6p8a1s3d5f7g9h2j@gmail.com": "T7@uY4$Za9#Bc3&Cc8iI!wE8*rT6%yU",
    "n7p9a2s4d6f8g1h3j5k@gmail.com": "U3!vZ8%Ab4#Cd9&Dd5jJ@zX2*cV9%bN",
    "o1q3w5e7r9t2y4u6i8o@gmail.com": "V8@wA3$Bc8#De4&Ee9kK!qY4*uI8%oP",
    "p4r6t8y1u3i5o7p9a2s@gmail.com": "W2!xB7%Cd3#Ef8&Ff5lL@wE7*rT3%yU",
    "q7s9d2f4g6h8j1k3l5z@gmail.com": "X9@yC2$De7#Fg3&Gg8mM!vC3*xZ6%bN",
    "r1t3y5u7i9o2p4a6s8d@gmail.com": "Y5!zD8%Ef2#Gh7&Hh9nN@qY9*uI5%oP",
    "s4u6i8o1p3a5s7d9f2g@gmail.com": "Z3@aE4$Fg9#Hi2&Ii7oO!wE5*rT8%yU",
    "t7v9b2n4m6k8j1h3g5f@gmail.com": "A7!bF3%Gh8#Ij4&Jj2pP@zX8*cV4%bN",
    "u1w3e5r7t9y2u4i6o8p@gmail.com": "B4@cG9$Hi3#Jk7&Kk5qQ!qY2*uI9%oP",
    "v4x6c8v1b3n5m7k9j2h@gmail.com": "C8!dH2%Ij9#Kl3&Ll8rR@wE6*rT2%yU",
    "w7y9u2i4o6p8a1s3d5f@gmail.com": "D3@eI7$Jk2#Lm8&Mm4sS!vC9*xZ7%bN",
    "x1z3l5k7j9h2g4f6d8s@gmail.com": "E9!fJ4%Kl7#Mn2&Nn3tT@qY5*uI6%oP",
    "y4a6s8d1f3g5h7j9k2l@gmail.com": "F2@gK8$Lm3#No7&Oo9uU!wE8*rT4%yU",
    "z7b9n2m4k6j8h1g3f5d@gmail.com": "G7!hL3%Mn8#Op2&Pp4vV@zX6*cV9%bN",
    "a1c3v5b7n9m2k4j6h8g@gmail.com": "H4@iM9$No3#Pq7&Qq2wW!qY3*uI7%oP",
    "b4d6f8g1h3j5k7l9z2x@gmail.com": "I8!jN2%Op9#Qr3&Rr7xX@wE5*rT8%yU",
    "c7e9r2t4y6u8i1o3p5a@gmail.com": "J3@kO7$Pq2#Rs8&Ss4yY!vC8*xZ2%bN",
    "d1f3g5h7j9k2l4z6x8c@gmail.com": "K9!lP4%Qr7#St2&Tt8zZ@qY7*uI3%oP",
    "e4g6h8j1k3l5z7x9c2v@gmail.com": "L2@mQ8$Rs3#Tu7&Uu4aA!wE6*rT9%yU",
    "f7h9j2k4l6z8x1c3v5b@gmail.com": "M8!nR3%St8#Uv2&Vv7bB@zX3*cV5%bN",
    "g1i3o5p7a9s2d4f6g8h@gmail.com": "N4@oS9$Tu3#Vw7&Ww2cC!qY9*uI4%oP",
    "h4j6k8l1z3x5c7v9b2n@gmail.com": "O8!pT2%Uv9#Wx3&Xx7dD@wE4*rT6%yU",
    "i7k9l2z4x6c8v1b3n5m@gmail.com": "P3@qU7$Vw2#Xy9&Yy4eE!vC7*xZ8%bN",
    "j1l3z5x7c9v2b4n6m8k@gmail.com": "Q9!rV3%Wx8#Yz2&Zz6fF@qY2*uI5%oP",
    "k4m6k8j1h3g5f7d9s2a@gmail.com": "R2@sW9$Xy3#Za7&Aa8gG!wE9*rT3%yU",
    "l7n9m2k4j6h8g1f3d5s@gmail.com": "S7!tX4%Yz9#Ab2&Bb3hH@zX4*cV6%bN",
    "m1o3p5a7s9d2f4g6h8j@gmail.com": "T3@uY8$Za3#Bc7&Cc9iI!qY5*uI9%oP",
    "n4p6a8s1d3f5g7h9j2k@gmail.com": "U9!vZ2%Ab9#Cd3&Dd4jJ@wE7*rT4%yU",
    "o7q9w2e4r6t8y1u3i5o@gmail.com": "V4@wA8$Bc2#De9&Ee7kK!vC2*xZ3%bN",
    "p1r3t5y7u9i2o4p6a8s@gmail.com": "W8!xB3%Cd9#Ef2&Ff4lL@qY8*uI6%oP",
    "q4s6d8f1g3h5j7k9l2z@gmail.com": "X3@yC7$De2#Fg9&Gg8mM!wE2*rT5%yU",
    "r7t9y2u4i6o8p1a3s5d@gmail.com": "Y9!zD4%Ef8#Gh2&Hh3nN@zX9*cV7%bN",
    "s1u3i5o7p9a2s4d6f8g@gmail.com": "Z2@aE9$Fg3#Hi8&Ii7oO!qY4*uI2%oP",
    "t4v6b8n1m3k5j7h9g2f@gmail.com": "A8!bF2%Gh9#Ij3&Jj4pP@wE5*rT7%yU",
    "u7w9e2r4t6y8u1i3o5p@gmail.com": "B3@cG8$Hi2#Jk9&Kk7qQ!vC8*xZ5%bN",
    "v1x3c5v7b9n2m4k6j8h@gmail.com": "C7!dH3%Ij8#Kl2&Ll4rR@qY2*uI8%oP",
    "w4y6u8i1o3p5a7s9d2f@gmail.com": "D2@eI9$Jk3#Lm8&Mm7sS!wE9*rT3%yU",
    "x7z9l2k4j6h8g1f3d5s@gmail.com": "E8!fJ2%Kl9#Mn3&Nn4tT@zX3*cV6%bN",
    "y1a3s5d7f9g2h4j6k8l@gmail.com": "F3@gK7$Lm2#No9&Oo8uU!qY7*uI5%oP",
    "z4b6n8m1k3j5h7g9f2d@gmail.com": "G9!hL8%Mn3#Op2&Pp4vV@wE6*rT2%yU",
    "a7c9v2b4n6m8k1j3h5g@gmail.com": "H2@iM4$No8#Pq3&Qq7wW!vC9*xZ4%bN",
    "b1d3f5g7h9j2k4l6z8x@gmail.com": "I7!jN3%Op4#Qr8&Rr2xX@qY3*uI9%oP",
    "c4e6r8t1y3u5i7o9p2a@gmail.com": "J2@kO9$Pq3#Rs4&Ss8yY!wE5*rT6%yU",
    "d7f9g2h4j6k8l1z3x5c@gmail.com": "K8!lP2%Qr9#St3&Tt7zZ@zX6*cV2%bN",
    "e1g3h5j7k9l2z4x6c8v@gmail.com": "L4@mQ7$Rs2#Tu9&Uu3aA!qY8*uI7%oP",
    "f4h6j8k1l3z5x7c9v2b@gmail.com": "M9!nR8%St3#Uv2&Vv4bB@wE3*rT9%yU",
    "g7i9o2p4a6s8d1f3g5h@gmail.com": "N3@oS4$Tu8#Vw3&Ww7cC!vC7*xZ5%bN",
})

# ============ END PART 5 ============# ============ PART 6 ============


# ============================================================
# تخزين التفعيل
# ============================================================
def load_activated() -> dict:
    if not ACTIVATED_FILE.exists():
        return {}
    try:
        return json.loads(ACTIVATED_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_activated(data: dict) -> None:
    ACTIVATED_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


ACTIVATED = load_activated()


def check_subscription(email: str) -> tuple[bool, str]:
    """يرجّع (صالح؟, رسالة). أول مرة → يخزّن تاريخ التفعيل."""
    now = datetime.now()
    rec = ACTIVATED.get(email)

    if not rec:
        ACTIVATED[email] = {
            "first_activated": now.isoformat(timespec="seconds"),
            "expires_at": (now + timedelta(days=SUBSCRIPTION_DAYS)).isoformat(timespec="seconds"),
        }
        save_activated(ACTIVATED)
        return True, f"تم التفعيل — صالح لمدة {SUBSCRIPTION_DAYS} يوم"

    expires = datetime.fromisoformat(rec["expires_at"])
    if now > expires:
        days_ago = (now - expires).days
        return False, f"انتهى الاشتراك منذ {days_ago} يوم"

    days_left = (expires - now).days
    return True, f"صالح — متبقّي {days_left} يوم"


# ============================================================
# Pydantic Models
# ============================================================
class LoginRequest(BaseModel):
    email: str
    password: str


class AccountIn(BaseModel):
    email: str
    password: str
    recovery: str = ""
    year: str = ""
    totp: str = ""
    backupCodes: str = ""


class OptionsIn(BaseModel):
    changePw: bool = True
    changeRecovery: bool = False
    change2fa: bool = False
    changeBackup: bool = False
    signout: bool = False
    removePhones: bool = False
    gather: bool = False
    gatherYoutube: bool = False
    gatherMaps: bool = False
    gatherDrive: bool = False
    gatherApps: bool = False
    gatherBusiness: bool = False
    gatherCountry: bool = False
    coloring: bool = False
    passwordSystem: str = "ahm"
    manualPassword: str = ""
    customPrefix: str = ""
    randomLength: int = Field(default=16, ge=16, le=32)
    outputFilename: str = "rotated"
    newRecovery: str = ""
    isPro: bool = False
    userEmail: str = ""


class RotateRequest(BaseModel):
    accounts: list[AccountIn]
    options: OptionsIn


# ============================================================
# Sessions
# ============================================================
@dataclass
class Session:
    id: str
    total: int
    done: int = 0
    success: int = 0
    fail: int = 0
    finished: bool = False
    logs: list = field(default_factory=list)
    results: list = field(default_factory=list)
    excel_path: str = ""
    text_path: str = ""
    started_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


SESSIONS: dict[str, Session] = {}


def log_sess(sess: Session, level: str, message: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    entry = {"level": level, "message": message, "ts": ts}
    sess.logs.append(entry)
    if len(sess.logs) > 800:
        sess.logs = sess.logs[-800:]
    try:
        print(f"[{ts}] [{level}] {message}")
    except Exception:
        pass


# ============================================================
# Helpers — Password Generation
# ============================================================
_LOWER = string.ascii_lowercase
_UPPER = string.ascii_uppercase
_DIGITS = string.digits
_ALL_POOL = _LOWER + _UPPER + _DIGITS


def gen_password(system: str, length: int, custom_prefix: str = "") -> str:
    length = max(16, min(32, length))

    if system == "ahm":
        prefix = "AHM-"
    elif system == "rdw":
        prefix = "RDW-"
    elif system == "custom":
        prefix = (custom_prefix or "").strip()
        if not prefix:
            prefix = "CUSTOM-"
        if not prefix.endswith(("-", "_")):
            prefix += "-"
    else:
        prefix = "AHM-"

    remaining = max(6, length - len(prefix))
    body = "".join(secrets.choice(_ALL_POOL) for _ in range(remaining))
    return prefix + body


def normalize_password(pw: str) -> str:
    pw = pw.strip().replace(" ", "")
    if len(pw) < 8:
        pw += "".join(secrets.choice(_DIGITS) for _ in range(8 - len(pw)))
    return pw


def parse_backup_codes(raw: str) -> list[str]:
    if not raw:
        return []
    tokens = re.findall(r"[A-Z0-9]{4}", raw.upper())
    return [" ".join(tokens[i:i + 2]) for i in range(0, len(tokens), 2)]


def generate_backup_code() -> str:
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return f"{''.join(secrets.choice(chars) for _ in range(4))} " \
           f"{''.join(secrets.choice(chars) for _ in range(4))}"


def generate_totp_secret() -> str:
    return pyotp.random_base32(length=32)


# ============================================================
# Excel + TXT Writer
# ============================================================
HEADERS = [
    "email", "password", "recovery", "year", "totp", "backup_codes",
    "drive_storage", "linked_apps_count", "linked_apps_list", "country",
    "google_maps", "maps_status", "my_business",
    "youtube_status", "youtube_created", "youtube_subs", "youtube_videos", "youtube_url",
    "facebook",
    "status", "notes",
]

HEADER_FILL = PatternFill(start_color="1e40af", end_color="1e40af", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)

GREEN_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
RED_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
YELLOW_FILL = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
GRAY_FILL = PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid")

GREEN_FONT = Font(color="006100")
RED_FONT = Font(color="9C0006")
YELLOW_FONT = Font(color="9C6500")
GRAY_FONT = Font(color="606060")


def write_outputs(sess: Session, filename: str, coloring: bool = False) -> None:
    """يحفظ Excel + TXT. يتنادى بعد كل حساب."""
    safe_name = re.sub(r"[^\w\-]", "_", filename) or "rotated"
    excel_path = OUTPUT_DIR / f"{safe_name}_{sess.id}.xlsx"
    text_path = OUTPUT_DIR / f"{safe_name}_{sess.id}.txt"

    wb = Workbook()
    ws = wb.active
    ws.title = "results"
    ws.append(HEADERS)

    for col_idx in range(1, len(HEADERS) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = HEADER_ALIGN

    widths = [30, 25, 30, 8, 40, 60, 20, 18, 55, 15,
              60, 14, 14, 16, 16, 14, 14, 35, 12, 14, 40]
    for i, w in enumerate(widths, start=1):
        try:
            ws.column_dimensions[get_column_letter(i)].width = w
        except Exception:
            pass

    txt_lines: list[str] = []

    for r_idx, r in enumerate(sess.results, start=2):
        row = [
            r.get("email", ""),
            r.get("new_password", ""),
            r.get("recovery", ""),
            r.get("year", ""),
            r.get("new_totp", ""),
            r.get("new_backup", ""),
            r.get("drive_storage", "N/A"),
            r.get("apps_count", "N/A"),
            r.get("apps_list", "N/A"),
            r.get("country", "N/A"),
            r.get("google_maps", "N/A"),
            r.get("maps_status", "N/A"),
            r.get("my_business", "N/A"),
            r.get("youtube_status", "N/A"),
            r.get("youtube_created", "N/A"),
            r.get("youtube_subs", "N/A"),
            r.get("youtube_videos", "N/A"),
            r.get("youtube_url", "N/A"),
            r.get("facebook", "N/A"),
            r.get("status", ""),
            r.get("notes", ""),
        ]
        ws.append(row)

        if coloring:
            status = r.get("status", "")
            if status in ("success", "rotated"):
                fill, font = GREEN_FILL, GREEN_FONT
            elif status in ("partial", "pw_changed"):
                fill, font = YELLOW_FILL, YELLOW_FONT
            elif status in ("failed", "error", "pw_failed", "login_failed", "fatal_error"):
                fill, font = RED_FILL, RED_FONT
            else:
                fill, font = GRAY_FILL, GRAY_FONT

            for col_idx in range(1, len(HEADERS) + 1):
                cell = ws.cell(row=r_idx, column=col_idx)
                cell.fill = fill
                cell.font = font

        txt_lines.append("\t".join(str(v) for v in row[:6]))

    wb.save(excel_path)
    text_path.write_text("\n".join(txt_lines), encoding="utf-8")

    sess.excel_path = str(excel_path)
    sess.text_path = str(text_path)


# ============================================================
# Device Fingerprint
# ============================================================
def get_machine_fingerprint() -> str:
    parts = [
        platform.node(),
        platform.system(),
        platform.machine(),
        str(uuid.getnode()),
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# ============ END PART 6 ============# ============ PART 7 ============


# ============================================================
# GmailRotator — الفئة الرئيسية
# ============================================================
class GmailRotator:
    def __init__(self, browser, sess: Session, opts: OptionsIn):
        self.browser = browser
        self.sess = sess
        self.opts = opts

    async def new_ctx(self):
        return await self.browser.new_context(
            viewport={"width": 1400, "height": 900},
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

    async def shot(self, page, tag: str, email: str):
        try:
            safe = re.sub(r"[^a-zA-Z0-9]", "_", email)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = SHOTS_DIR / f"{safe}_{ts}_{tag}.png"
            await page.screenshot(path=str(path), full_page=True)
        except Exception:
            pass

    async def safe_click(self, page, selectors: list, timeout_ms: int = 3000) -> bool:
        for sel in selectors:
            try:
                await page.click(sel, timeout=timeout_ms)
                return True
            except PWTimeout:
                continue
            except Exception:
                continue
        return False

    # --------------------------------------------------------
    # تسجيل الدخول
    # --------------------------------------------------------
    async def login(self, page, acc: AccountIn) -> bool:
        log_sess(self.sess, "info", f"{acc.email}: فتح جوجل")

        try:
            await page.goto(
                "https://accounts.google.com/signin",
                wait_until="domcontentloaded",
                timeout=NAV_TIMEOUT,
            )
        except PWTimeout:
            log_sess(self.sess, "error", f"{acc.email}: مهلة صفحة الدخول")
            return False

        await page.wait_for_timeout(1500)

        # 1) الإيميل
        try:
            await page.wait_for_selector('input[type="email"]', timeout=ACTION_TIMEOUT)
            await page.fill('input[type="email"]', acc.email)
            await page.wait_for_timeout(400)
            await self.safe_click(page, ["#identifierNext", 'button:has-text("Next")'])
            await page.wait_for_timeout(2200)
        except Exception as e:
            await self.shot(page, "email_fail", acc.email)
            log_sess(self.sess, "error", f"{acc.email}: فشل الإيميل — {e}")
            return False

        # 2) الباسورد
        try:
            await page.wait_for_selector('input[type="password"]', timeout=ACTION_TIMEOUT)
            await page.fill('input[type="password"]', acc.password)
            await page.wait_for_timeout(400)
            await self.safe_click(page, ["#passwordNext", 'button:has-text("Next")'])
            await page.wait_for_timeout(2800)
        except PWTimeout:
            await self.shot(page, "pw_fail", acc.email)
            log_sess(self.sess, "error", f"{acc.email}: مفيش خانة الباسورد")
            return False
        except Exception as e:
            await self.shot(page, "pw_exception", acc.email)
            log_sess(self.sess, "error", f"{acc.email}: استثناء الباسورد — {e}")
            return False

        # 3) TOTP
        if acc.totp:
            await self._handle_totp(page, acc)

        # 4) نتحقق
        await page.wait_for_timeout(2000)
        current_url = page.url

        if "myaccount.google.com" in current_url or "mail.google.com" in current_url:
            return True

        try:
            await page.wait_for_url(
                re.compile(r"myaccount\.google\.com|mail\.google\.com"),
                timeout=8_000,
            )
            return True
        except PWTimeout:
            pass

        if "challenge" in current_url or "signin" in current_url:
            await self.shot(page, "extra_verification", acc.email)
            log_sess(self.sess, "error", f"{acc.email}: مطلوب تحقق إضافي")
            return False

        return True

    async def _handle_totp(self, page, acc: AccountIn) -> bool:
        try:
            await page.wait_for_selector(
                'input[type="tel"], input[name="totpPin"], '
                'input[aria-label*="code"], input[id*="totp"], '
                'input[autocomplete="one-time-code"]',
                timeout=10_000,
            )
        except PWTimeout:
            log_sess(self.sess, "info", f"{acc.email}: مفيش طلب TOTP")
            return True

        try:
            code = pyotp.TOTP(acc.totp).now()
            log_sess(self.sess, "info", f"{acc.email}: TOTP = {code}")
            box = page.locator(
                'input[type="tel"], input[name="totpPin"], '
                'input[aria-label*="code"], input[id*="totp"], '
                'input[autocomplete="one-time-code"]'
            ).first
            await box.fill(code)
            await page.wait_for_timeout(400)
            await self.safe_click(
                page,
                ['#totpNext', 'button:has-text("Next")', 'button:has-text("Verify")'],
            )
            await page.wait_for_timeout(3000)
            return True
        except Exception as e:
            await self.shot(page, "totp_fail", acc.email)
            log_sess(self.sess, "error", f"{acc.email}: فشل TOTP — {e}")
            return False

    # --------------------------------------------------------
    # تغيير الباسورد
    # --------------------------------------------------------
    async def change_password(self, page, acc: AccountIn, new_pw: str) -> bool:
        log_sess(self.sess, "info", f"{acc.email}: صفحة الباسورد")

        try:
            await page.goto(
                "https://myaccount.google.com/signinoptions/password",
                wait_until="domcontentloaded",
                timeout=NAV_TIMEOUT,
            )
        except PWTimeout:
            log_sess(self.sess, "error", f"{acc.email}: مهلة صفحة الباسورد")
            return False

        await page.wait_for_timeout(3000)
        await self.shot(page, "pw_page", acc.email)

        # إعادة تحقق لو مطلوب
        if "signin" in page.url:
            log_sess(self.sess, "info", f"{acc.email}: إعادة تحقق...")
            try:
                await page.fill('input[type="password"]', acc.password)
                await self.safe_click(page, ["#passwordNext", 'button:has-text("Next")'])
                await page.wait_for_timeout(3000)
            except Exception:
                pass

        try:
            await page.wait_for_timeout(1000)
            pwd_inputs = page.locator('input[type="password"]')
            count = await pwd_inputs.count()

            if count < 2:
                await self.shot(page, "pw_not_enough_inputs", acc.email)
                log_sess(self.sess, "error", f"{acc.email}: خانات الباسورد = {count}")
                return False

            await pwd_inputs.nth(0).fill(acc.password)
            await page.wait_for_timeout(300)
            await pwd_inputs.nth(1).fill(new_pw)
            await page.wait_for_timeout(300)

            if count >= 3:
                await pwd_inputs.nth(2).fill(new_pw)
                await page.wait_for_timeout(300)

            clicked = await self.safe_click(
                page,
                [
                    'button:has-text("Change password")',
                    'button:has-text("Save")',
                    'button:has-text("Next")',
                    'button:has-text("Change")',
                ],
            )
            if not clicked:
                await self.shot(page, "pw_no_button", acc.email)
                log_sess(self.sess, "error", f"{acc.email}: مفيش زر تغيير الباسورد")
                return False

            await page.wait_for_timeout(4000)
            await self.shot(page, "pw_after_click", acc.email)

            body = (await page.inner_text("body")).lower()
            if "error" in body or "wrong" in body or "incorrect" in body:
                log_sess(self.sess, "error", f"{acc.email}: الباسورد اترفض")
                return False

            return True

        except Exception as e:
            await self.shot(page, "pw_exception", acc.email)
            log_sess(self.sess, "error", f"{acc.email}: استثناء الباسورد — {e}")
            return False

    # --------------------------------------------------------
    # تغيير بريد الاسترداد
    # --------------------------------------------------------
    async def change_recovery(self, page, acc: AccountIn, new_recovery: str) -> bool:
        if not new_recovery:
            log_sess(self.sess, "info", f"{acc.email}: مفيش بريد استرداد جديد")
            return True

        log_sess(self.sess, "info", f"{acc.email}: صفحة بريد الاسترداد")

        try:
            await page.goto(
                "https://myaccount.google.com/signinoptions/recovery-options",
                wait_until="domcontentloaded",
                timeout=NAV_TIMEOUT,
            )
            await page.wait_for_timeout(3500)
            await self.shot(page, "recovery_page", acc.email)

            add_clicked = await self.safe_click(
                page,
                [
                    'a:has-text("Add recovery email")',
                    'button:has-text("Add recovery email")',
                    'a:has-text("إضافة بريد")',
                    'button:has-text("إضافة بريد")',
                    'div[role="button"]:has-text("Add")',
                    'div[role="button"]:has-text("إضافة")',
                ],
                timeout_ms=4000,
            )

            if not add_clicked:
                await self.shot(page, "recovery_no_add_btn", acc.email)
                log_sess(self.sess, "warn", f"{acc.email}: مفيش زر إضافة")
                return False

            await page.wait_for_timeout(2500)
            await self.shot(page, "recovery_add_form", acc.email)

            try:
                email_input = page.locator(
                    'input[type="email"], input[type="text"], input[name*="email"]'
                ).first
                await email_input.fill(new_recovery)
                await page.wait_for_timeout(500)

                await self.safe_click(
                    page,
                    [
                        'button:has-text("Next")',
                        'button:has-text("التالي")',
                        'button:has-text("Save")',
                        'button:has-text("حفظ")',
                    ],
                    timeout_ms=4000,
                )

                await page.wait_for_timeout(3000)
                await self.shot(page, "recovery_after_submit", acc.email)

                await self.safe_click(
                    page,
                    [
                        'button:has-text("Cancel")',
                        'button:has-text("إلغاء")',
                        'a:has-text("Cancel")',
                        'a:has-text("إلغاء")',
                    ],
                    timeout_ms=2500,
                )

                return True

            except Exception as e:
                log_sess(self.sess, "error", f"{acc.email}: Recovery — {e}")
                return False

        except Exception as e:
            log_sess(self.sess, "error", f"{acc.email}: Recovery — {e}")
            return False

# ============ END PART 7 ============# ============ PART 8 ============

    # --------------------------------------------------------
    # توليد رموز احتياطية جديدة
    # --------------------------------------------------------
    async def change_backup(self, page, acc: AccountIn) -> list[str]:
        log_sess(self.sess, "info", f"{acc.email}: صفحة Backup Codes")

        try:
            await page.goto(
                "https://myaccount.google.com/signinoptions/two-step-verification/backup-codes",
                wait_until="domcontentloaded",
                timeout=NAV_TIMEOUT,
            )
            await page.wait_for_timeout(3500)
            await self.shot(page, "backup_page", acc.email)

            await self.safe_click(
                page,
                [
                    'button:has-text("Get new codes")',
                    'button:has-text("Get backup codes")',
                    'button:has-text("Generate")',
                    'button:has-text("New codes")',
                    'button:has-text("Regenerate")',
                    'button:has-text("الحصول على رموز جديدة")',
                    'button:has-text("إنشاء")',
                ],
                timeout_ms=4000,
            )
            await page.wait_for_timeout(3500)
            await self.shot(page, "backup_after", acc.email)

            body = await page.inner_text("body")
            codes = re.findall(r"\b[A-Z0-9]{4}\s[A-Z0-9]{4}\b", body.upper())

            seen = set()
            unique = []
            for c in codes:
                if c not in seen:
                    seen.add(c)
                    unique.append(c)

            if len(unique) >= 5:
                return unique[:10]

            log_sess(self.sess, "warn", f"{acc.email}: قرأنا {len(unique)} رمز فقط")
            return []

        except Exception as e:
            log_sess(self.sess, "error", f"{acc.email}: Backup — {e}")
            return []

    # --------------------------------------------------------
    # تغيير TOTP
    # --------------------------------------------------------
    async def change_2fa(self, page, acc: AccountIn) -> str:
        log_sess(self.sess, "info", f"{acc.email}: صفحة 2FA")

        try:
            await page.goto(
                "https://myaccount.google.com/signinoptions/two-step-verification",
                wait_until="domcontentloaded",
                timeout=NAV_TIMEOUT,
            )
            await page.wait_for_timeout(3500)
            await self.shot(page, "2fa_page", acc.email)

            await self.safe_click(
                page,
                [
                    'a:has-text("Authenticator app")',
                    'div:has-text("Authenticator app")',
                    'button:has-text("Set up")',
                    'button:has-text("Change")',
                    'a:has-text("تطبيق Authenticator")',
                ],
                timeout_ms=3000,
            )
            await page.wait_for_timeout(3000)
            await self.shot(page, "2fa_setup", acc.email)

            clicked = await self.safe_click(
                page,
                [
                    'a:has-text("Can\'t scan it")',
                    'button:has-text("Can\'t scan it")',
                    'a:has-text("can\'t scan")',
                    'button:has-text("can\'t scan")',
                    'a:has-text("لا يمكنك المسح")',
                ],
                timeout_ms=3000,
            )
            if not clicked:
                log_sess(self.sess, "warn", f"{acc.email}: مفيش رابط Can't scan")
                return ""

            await page.wait_for_timeout(2000)
            await self.shot(page, "2fa_secret_reveal", acc.email)

            body = await page.inner_text("body")
            candidates = re.findall(r"\b[A-Z2-7]{32}\b", body.upper().replace(" ", ""))

            if not candidates:
                for el in await page.locator("code, kbd, samp, span[dir='ltr']").all():
                    try:
                        txt = (await el.inner_text()).strip().replace(" ", "")
                        if re.fullmatch(r"[A-Z2-7]{32}", txt.upper()):
                            candidates.append(txt.upper())
                    except Exception:
                        continue

            if candidates:
                return candidates[0]

            log_sess(self.sess, "warn", f"{acc.email}: مفيش 32 حرف ظهروا")
            return ""

        except Exception as e:
            log_sess(self.sess, "error", f"{acc.email}: 2FA — {e}")
            return ""

    # --------------------------------------------------------
    # تسجيل خروج من كل الأجهزة
    # --------------------------------------------------------
    async def signout_all(self, page, acc: AccountIn) -> bool:
        log_sess(self.sess, "info", f"{acc.email}: صفحة الأجهزة")

        try:
            await page.goto(
                "https://myaccount.google.com/device-activity",
                wait_until="domcontentloaded",
                timeout=NAV_TIMEOUT,
            )
            await page.wait_for_timeout(3500)
            await self.shot(page, "devices_page", acc.email)

            clicked = await self.safe_click(
                page,
                [
                    'button:has-text("Sign out of all devices")',
                    'button:has-text("Sign out all devices")',
                    'button:has-text("تسجيل الخروج من جميع الأجهزة")',
                    'button:has-text("تسجيل خروج")',
                ],
                timeout_ms=4000,
            )

            if not clicked:
                log_sess(self.sess, "warn", f"{acc.email}: مفيش زر تسجيل خروج")
                return False

            await page.wait_for_timeout(2500)
            await self.shot(page, "signout_confirm", acc.email)

            if acc.totp:
                try:
                    await page.wait_for_selector(
                        'input[type="tel"], input[type="password"], input[name*="totp"]',
                        timeout=6000,
                    )
                    try:
                        code = pyotp.TOTP(acc.totp).now()
                        await page.fill('input[type="tel"]', code)
                    except Exception:
                        await page.fill('input[type="password"]', acc.password)

                    await self.safe_click(
                        page,
                        ['button:has-text("Next")', 'button:has-text("Verify")',
                         'button:has-text("Confirm")', 'button:has-text("تأكيد")'],
                        timeout_ms=3000,
                    )
                    await page.wait_for_timeout(3000)
                except Exception:
                    pass

            await self.shot(page, "signout_after", acc.email)
            return True

        except Exception as e:
            log_sess(self.sess, "error", f"{acc.email}: Signout — {e}")
            return False

    # --------------------------------------------------------
    # حذف أرقام الاسترداد
    # --------------------------------------------------------
    async def remove_phones(self, page, acc: AccountIn) -> tuple[int, int]:
        """يرجّع (اتحذف, الإجمالي)."""
        log_sess(self.sess, "info", f"{acc.email}: صفحة الأرقام")

        try:
            await page.goto(
                "https://myaccount.google.com/signinoptions/recovery-phone",
                wait_until="domcontentloaded",
                timeout=NAV_TIMEOUT,
            )
            await page.wait_for_timeout(3500)
            await self.shot(page, "phones_page", acc.email)

            removed = 0
            total = 0

            for attempt in range(5):
                remove_btns = page.locator(
                    'button:has-text("Remove"), button:has-text("Delete"), '
                    'button:has-text("إزالة"), button:has-text("حذف")'
                )
                cnt = await remove_btns.count()
                if cnt == 0:
                    break

                total += cnt

                try:
                    await remove_btns.first.click(timeout=3000)
                    await page.wait_for_timeout(2500)

                    body = (await page.inner_text("body")).lower()
                    if "sms" in body or "verification" in body or "code" in body:
                        await self.shot(page, "phones_sms_required", acc.email)
                        log_sess(self.sess, "warn", f"{acc.email}: مطلوب كود SMS")
                        break

                    await self.safe_click(
                        page,
                        ['button:has-text("Confirm")', 'button:has-text("OK")',
                         'button:has-text("Remove")', 'button:has-text("تأكيد")'],
                        timeout_ms=2500,
                    )
                    await page.wait_for_timeout(2500)
                    removed += 1
                except Exception:
                    break

            await self.shot(page, "phones_after", acc.email)
            return removed, total

        except Exception as e:
            log_sess(self.sess, "error", f"{acc.email}: Phones — {e}")
            return 0, 0

    # --------------------------------------------------------
    # جمع مساحة Drive
    # --------------------------------------------------------
    async def gather_drive(self, page, acc: AccountIn) -> str:
        try:
            await page.goto(
                "https://drive.google.com/settings/storage",
                wait_until="domcontentloaded",
                timeout=NAV_TIMEOUT,
            )
            await page.wait_for_timeout(3500)
            await self.shot(page, "drive_page", acc.email)

            body = await page.inner_text("body")
            patterns = [
                r"(\d+(?:\.\d+)?)\s*(?:GB|MB|TB)\s*(?:of|من)\s*(\d+(?:\.\d+)?)\s*(?:GB|MB|TB)",
                r"(\d+(?:\.\d+)?)\s*(?:جيجا|ميجا|تيرا).*?من.*?(\d+(?:\.\d+)?)",
            ]
            for p in patterns:
                m = re.search(p, body, re.IGNORECASE)
                if m:
                    return f"{m.group(1)} / {m.group(2)}"

            return "N/A"
        except Exception:
            return "N/A"

    # --------------------------------------------------------
    # جمع التطبيقات المرتبطة
    # --------------------------------------------------------
    async def gather_apps(self, page, acc: AccountIn) -> tuple[str, str, str]:
        """يرجّع (عدد, أسماء, فيسبوك)"""
        try:
            await page.goto(
                "https://myaccount.google.com/connections",
                wait_until="domcontentloaded",
                timeout=NAV_TIMEOUT,
            )
            await page.wait_for_timeout(3500)
            await self.shot(page, "apps_page", acc.email)

            names = []
            try:
                items = page.locator('div[role="button"], a[href*="/connections/"]')
                cnt = await items.count()
                for i in range(min(cnt, 100)):
                    try:
                        txt = (await items.nth(i).inner_text()).strip()
                        if txt and 2 <= len(txt) <= 60 and "\n" not in txt:
                            names.append(txt)
                    except Exception:
                        continue
            except Exception:
                pass

            seen = set()
            unique = []
            for n in names:
                if n not in seen:
                    seen.add(n)
                    unique.append(n)

            apps_list = " ".join(unique[:50]) if unique else "N/A"
            apps_count = str(len(unique)) if unique else "0"
            facebook = "Facebook" if any("facebook" in n.lower() for n in unique) else "N/A"

            return apps_count, apps_list, facebook

        except Exception:
            return "N/A", "N/A", "N/A"

    # --------------------------------------------------------
    # جمع الدولة
    # --------------------------------------------------------
    async def gather_country(self, page, acc: AccountIn) -> str:
        try:
            await page.goto(
                "https://myaccount.google.com/",
                wait_until="domcontentloaded",
                timeout=NAV_TIMEOUT,
            )
            await page.wait_for_timeout(3500)
            await self.shot(page, "country_page", acc.email)

            body = await page.inner_text("body")
            patterns = [
                r"النسخة المطابقة للبلد\s*[:：]\s*([^\n]+)",
                r"Country version\s*[:：]\s*([^\n]+)",
            ]
            for p in patterns:
                m = re.search(p, body)
                if m:
                    return m.group(1).strip()[:50]

            return "N/A"
        except Exception:
            return "N/A"

    # --------------------------------------------------------
    # جمع يوتيوب
    # --------------------------------------------------------
    async def gather_youtube(self, page, acc: AccountIn) -> dict:
        result = {
            "youtube_status": "N/A",
            "youtube_created": "N/A",
            "youtube_subs": "N/A",
            "youtube_videos": "N/A",
            "youtube_url": "N/A",
        }

        try:
            await page.goto(
                "https://www.youtube.com/",
                wait_until="domcontentloaded",
                timeout=NAV_TIMEOUT,
            )
            await page.wait_for_timeout(3500)
            await self.shot(page, "youtube_home", acc.email)

            body = await page.inner_text("body")

            if "Create a channel" in body or "إنشاء قناة" in body:
                result["youtube_status"] = "لا يوجد قناة"
                return result

            try:
                await page.goto(
                    "https://studio.youtube.com/",
                    wait_until="domcontentloaded",
                    timeout=NAV_TIMEOUT,
                )
                await page.wait_for_timeout(4000)
                await self.shot(page, "youtube_studio", acc.email)

                body = await page.inner_text("body")
                result["youtube_status"] = "يوجد قناة"

                handle_match = re.search(r"@[\w\-\.]+", body)
                if handle_match:
                    result["youtube_url"] = f"youtube.com/{handle_match.group(0)}"

                subs_match = re.search(r"(\d+(?:\.\d+)?[KMB]?)\s*(?:subs|مشترك)", body, re.IGNORECASE)
                if subs_match:
                    result["youtube_subs"] = subs_match.group(1)

                vids_match = re.search(r"(\d+)\s*(?:videos|فيديو)", body, re.IGNORECASE)
                if vids_match:
                    result["youtube_videos"] = vids_match.group(1)

                date_match = re.search(r"(?:Joined|انضم|الانضمام)\s*[:：]?\s*(\d{4}[/\-]\d{2}[/\-]\d{2})", body)
                if date_match:
                    result["youtube_created"] = date_match.group(1)

            except Exception:
                pass

            return result

        except Exception:
            return result

    # --------------------------------------------------------
    # جمع Google Maps
    # --------------------------------------------------------
    async def gather_maps(self, page, acc: AccountIn) -> tuple[str, str]:
        try:
            await page.goto(
                "https://www.google.com/maps/contrib",
                wait_until="domcontentloaded",
                timeout=NAV_TIMEOUT,
            )
            await page.wait_for_timeout(4000)
            await self.shot(page, "maps_page", acc.email)

            body = await page.inner_text("body")
            parts = []

            level_match = re.search(r"(Local Guide\s*Level\s*\d+|مرشد محلي من المستوى\s*\d+)", body)
            if level_match:
                parts.append(level_match.group(1))

            points_match = re.search(r"(\d+)\s*(?:points|نقطة)", body)
            if points_match:
                parts.append(f"{points_match.group(1)} pts")

            contrib_match = re.search(r"(\d+)\s*(?:contributions|مساهمة)", body)
            if contrib_match:
                parts.append(f"{contrib_match.group(1)} contrib")

            views_match = re.search(r"(\d+)\s*(?:views|مشاهدة)", body)
            if views_match:
                parts.append(f"{views_match.group(1)} views")

            if not parts:
                return "Maps: fresh", "not used"

            data = "Maps: " + " | ".join(parts)
            return data, "used"

        except Exception:
            return "Maps: not accessible", "not accessible"

    # --------------------------------------------------------
    # جمع Google Business
    # --------------------------------------------------------
    async def gather_business(self, page, acc: AccountIn) -> str:
        try:
            await page.goto(
                "https://myaccount.google.com/",
                wait_until="domcontentloaded",
                timeout=NAV_TIMEOUT,
            )
            await page.wait_for_timeout(2500)

            try:
                await page.click(
                    'a[aria-label*="Google apps"], button[aria-label*="Google apps"]',
                    timeout=3000,
                )
                await page.wait_for_timeout(2000)
            except Exception:
                pass

            body = await page.inner_text("body")
            if "لوحة إدارة الأعمال" in body or "Business Profile" in body or "My Business" in body:
                return "used"
            return "not used"

        except Exception:
            return "not used"

# ============ END PART 8 ============# ============ PART 9 ============

    # --------------------------------------------------------
    # run — التشغيل الكامل لحساب واحد
    # --------------------------------------------------------
    async def run(self, acc: AccountIn, new_pw: str, new_recovery: str) -> dict:
        result = {
            "email": acc.email,
            "recovery": new_recovery if new_recovery else acc.recovery,
            "year": acc.year,
            "new_password": new_pw if self.opts.changePw else acc.password,
            "new_totp": acc.totp,
            "new_backup": " ".join(parse_backup_codes(acc.backupCodes)),
            "drive_storage": "N/A",
            "apps_count": "N/A",
            "apps_list": "N/A",
            "country": "N/A",
            "google_maps": "N/A",
            "maps_status": "N/A",
            "my_business": "N/A",
            "youtube_status": "N/A",
            "youtube_created": "N/A",
            "youtube_subs": "N/A",
            "youtube_videos": "N/A",
            "youtube_url": "N/A",
            "facebook": "N/A",
            "status": "pending",
            "notes": "",
        }

        ctx = await self.new_ctx()
        page = await ctx.new_page()
        page.set_default_timeout(ACTION_TIMEOUT)

        notes_list = []

        try:
            log_sess(self.sess, "info", f"━━━ {acc.email}: بدء ━━━")

            # 1) تسجيل الدخول
            if not await self.login(page, acc):
                result["status"] = "login_failed"
                result["notes"] = "فشل تسجيل الدخول"
                return result

            log_sess(self.sess, "success", f"✓ {acc.email}: دخل الحساب")

            # 2) جمع البيانات (قبل التغييرات)
            if self.opts.gatherDrive:
                try:
                    result["drive_storage"] = await self.gather_drive(page, acc)
                except Exception:
                    pass

            if self.opts.gatherApps:
                try:
                    cnt, lst, fb = await self.gather_apps(page, acc)
                    result["apps_count"] = cnt
                    result["apps_list"] = lst
                    result["facebook"] = fb
                except Exception:
                    pass

            if self.opts.gatherCountry:
                try:
                    result["country"] = await self.gather_country(page, acc)
                except Exception:
                    pass

            if self.opts.gatherYoutube:
                try:
                    yt = await self.gather_youtube(page, acc)
                    result.update(yt)
                except Exception:
                    pass

            if self.opts.gatherMaps:
                try:
                    maps_data, maps_status = await self.gather_maps(page, acc)
                    result["google_maps"] = maps_data
                    result["maps_status"] = maps_status
                except Exception:
                    pass

            if self.opts.gatherBusiness:
                try:
                    result["my_business"] = await self.gather_business(page, acc)
                except Exception:
                    pass

            # 3) تغيير الباسورد
            if self.opts.changePw:
                try:
                    if await self.change_password(page, acc, new_pw):
                        log_sess(self.sess, "success", f"✓ {acc.email}: الباسورد اتغير")
                    else:
                        notes_list.append("فشل تغيير الباسورد")
                except Exception as e:
                    notes_list.append(f"فشل الباسورد ({e})")

            # 4) تغيير بريد الاسترداد
            if self.opts.changeRecovery and new_recovery:
                try:
                    if await self.change_recovery(page, acc, new_recovery):
                        log_sess(self.sess, "success", f"✓ {acc.email}: البريد اتغير")
                    else:
                        notes_list.append("فشل تغيير بريد الاسترداد")
                except Exception:
                    notes_list.append("فشل تغيير بريد الاسترداد")

            # 5) رموز احتياطية
            if self.opts.changeBackup:
                try:
                    codes = await self.change_backup(page, acc)
                    if codes:
                        result["new_backup"] = " ".join(codes)
                        log_sess(self.sess, "success", f"✓ {acc.email}: رموز جديدة")
                    else:
                        notes_list.append("فشل توليد الرموز")
                except Exception:
                    notes_list.append("فشل توليد الرموز")

            # 6) تسجيل خروج من كل الأجهزة
            if self.opts.signout:
                try:
                    if await self.signout_all(page, acc):
                        log_sess(self.sess, "success", f"✓ {acc.email}: خرج من الأجهزة")
                    else:
                        notes_list.append("فشل تسجيل الخروج من الأجهزة")
                except Exception:
                    notes_list.append("فشل تسجيل الخروج")

            # 7) حذف أرقام الاسترداد
            if self.opts.removePhones:
                try:
                    removed, total = await self.remove_phones(page, acc)
                    if removed > 0:
                        log_sess(self.sess, "success", f"✓ {acc.email}: اتحذف {removed} من {total}")
                        if removed < total:
                            notes_list.append(f"اتحذف {removed} من {total} أرقام")
                    else:
                        notes_list.append("فشل حذف الأرقام")
                except Exception:
                    notes_list.append("فشل حذف الأرقام")

            # 8) تغيير TOTP
            if self.opts.change2fa:
                try:
                    new_totp = await self.change_2fa(page, acc)
                    if new_totp:
                        result["new_totp"] = new_totp
                        log_sess(self.sess, "success", f"✓ {acc.email}: TOTP اتغير")
                    else:
                        notes_list.append("فشل تغيير TOTP")
                except Exception:
                    notes_list.append("فشل تغيير TOTP")

            # نحدد الحالة
            if notes_list:
                if len(notes_list) >= 2:
                    result["status"] = "failed"
                else:
                    result["status"] = "partial"
                result["notes"] = " | ".join(notes_list)
            else:
                result["status"] = "success"

            return result

        except Exception as e:
            result["status"] = "error"
            result["notes"] = str(e)
            log_sess(self.sess, "error", f"✗ {acc.email}: {traceback.format_exc()[:200]}")
            return result
        finally:
            try:
                await ctx.close()
            except Exception:
                pass


# ============================================================
# Background Task — التشغيل الرئيسي
# ============================================================
async def run_rotation(sess: Session, req: RotateRequest):
    max_parallel = if req.options.isPro else TRIAL_MAX_PARALLEL

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=HEADLESS,
            slow_mo=SLOW_MO,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--start-maximized",
                "--disable-dev-shm-usage",
            ],
        )

        try:
            rot = GmailRotator(browser, sess, req.options)

            async def process(acc: AccountIn):
                if req.options.changePw:
                    if req.options.passwordSystem == "manual" and req.options.manualPassword.strip():
                        new_pw = normalize_password(req.options.manualPassword)
                    else:
                        new_pw = gen_password(
                            req.options.passwordSystem,
                            req.options.randomLength,
                            req.options.customPrefix,
                        )
                else:
                    new_pw = ""

                new_recovery = req.options.newRecovery or ""

                try:
                    result = await rot.run(acc, new_pw, new_recovery)
                except Exception as e:
                    result = {
                        "email": acc.email,
                        "recovery": acc.recovery,
                        "year": acc.year,
                        "new_password": new_pw,
                        "new_totp": acc.totp,
                        "new_backup": " ".join(parse_backup_codes(acc.backupCodes)),
                        "status": "fatal_error",
                        "notes": str(e),
                    }

                sess.results.append(result)
                sess.done += 1
                if result["status"] in ("success", "rotated"):
                    sess.success += 1
                else:
                    sess.fail += 1

                try:
                    write_outputs(sess, req.options.outputFilename, req.options.coloring)
                except Exception as e:
                    log_sess(sess, "error", f"فشل الحفظ: {e}")

            sem = asyncio.Semaphore(max_parallel)

            async def limited(acc):
                async with sem:
                    await process(acc)
                    await asyncio.sleep(2)

            tasks = [limited(acc) for acc in req.accounts]
            await asyncio.gather(*tasks, return_exceptions=True)

        finally:
            try:
                await browser.close()
            except Exception:
                pass

    sess.finished = True
    try:
        write_outputs(sess, req.options.outputFilename, req.options.coloring)
    except Exception as e:
        log_sess(sess, "error", f"حفظ نهائي فشل: {e}")

    log_sess(sess, "success", f"🎉 خلص — نجح: {sess.success} | فشل: {sess.fail}")


# ============ END PART 9 ============# ============ PART 10 ============


# ============================================================
# FastAPI App
# ============================================================
app = FastAPI(title="ShadowRotate", version="3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


@app.post("/auth")
async def auth(req: LoginRequest):
    email = req.email.strip()
    password = req.password

    if email not in USERS_BUILTIN:
        return {"success": False, "message": "الإيميل غير مسجّل"}

    if USERS_BUILTIN[email] != password:
        return {"success": False, "message": "كلمة المرور خاطئة"}

    valid, msg = check_subscription(email)
    if not valid:
        return {"success": False, "message": msg}

    return {"success": True, "message": msg, "email": email}


@app.post("/rotate")
async def rotate(req: RotateRequest):
    if not req.accounts:
        raise HTTPException(400, "مفيش حسابات")

    has_op = (
        req.options.changePw or req.options.change2fa or req.options.changeBackup
        or req.options.signout or req.options.removePhones or req.options.gather
        or req.options.changeRecovery
    )
    if not has_op:
        raise HTTPException(400, "اختار عملية واحدة على الأقل")

    sid = uuid.uuid4().hex[:12]
    sess = Session(id=sid, total=len(req.accounts))
    SESSIONS[sid] = sess

    asyncio.create_task(run_rotation(sess, req))

    return {"session_id": sid, "total": len(req.accounts)}


@app.get("/status/{sid}")
async def status(sid: str):
    if sid not in SESSIONS:
        raise HTTPException(404, "session not found")
    s = SESSIONS[sid]

    return {
        "session_id": sid,
        "total": s.total,
        "done": s.done,
        "success": s.success,
        "fail": s.fail,
        "finished": s.finished,
        "started_at": s.started_at,
        "new_logs": s.logs[-60:],
    }


@app.get("/download-excel/{sid}")
async def download_excel(sid: str):
    if sid not in SESSIONS:
        raise HTTPException(404)
    s = SESSIONS[sid]
    if not s.excel_path or not Path(s.excel_path).exists():
        raise HTTPException(404, "الملف لسه مش جاهز")
    return FileResponse(
        s.excel_path,
        filename=f"rotated_{sid}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/download-text/{sid}")
async def download_text(sid: str):
    if sid not in SESSIONS:
        raise HTTPException(404)
    s = SESSIONS[sid]
    if not s.text_path or not Path(s.text_path).exists():
        raise HTTPException(404, "الملف لسه مش جاهز")
    content = Path(s.text_path).read_text(encoding="utf-8")
    return PlainTextResponse(
        content,
        headers={"Content-Disposition": f"attachment; filename=rotated_{sid}.txt"},
    )


@app.get("/")
async def root():
    html = BASE_DIR / "index.html"
    if html.exists():
        return HTMLResponse(html.read_text(encoding="utf-8"))
    return HTMLResponse(
        "<h1>index.html مش موجود جنب server.py</h1>"
        "<p>حط index.html في نفس الفولدر مع server.py</p>"
    )


# ============================================================
# Chromium Check
# ============================================================
def ensure_chromium():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            _ = p.chromium.executable_path
            return
    except Exception:
        pass

    print("[setup] Chromium مش متثبت — جاري التثبيت (~150MB)")
    print("[setup] ممكن ياخد من دقيقة لخمس دقايق...")
    try:
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        print("[setup] Chromium اتثبت ✓")
    except subprocess.CalledProcessError as e:
        print(f"[setup] فشل تثبيت Chromium: {e}")
        print("[setup] شغّل يدوياً: python -m playwright install chromium")
        sys.exit(1)


# ============================================================
# Main
# ============================================================
def print_banner():
    print("=" * 65)
    print("  ◈ SHADOWROTATE — Server v3.0")
    print("=" * 65)
    print(f"  Output:      {OUTPUT_DIR}")
    print(f"  Shots:       {SHOTS_DIR}")
    print(f"  Users:       {len(USERS_BUILTIN)}")
    print(f"  Mode:        {'HEADLESS' if HEADLESS else 'VISIBLE (المتصفح ظاهر)'}")
    print(f"  Slow-Mo:     {SLOW_MO}ms")
    print("=" * 65)
    print()
    print("  افتح المتصفح على: http://127.0.0.1:8000")
    print()
    print("  للإيقاف: Ctrl+C")
    print("=" * 65)
    print()


if __name__ == "__main__":
    import uvicorn

    print_banner()
    ensure_chromium()

    try:
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="info",
            access_log=False,
        )
    except KeyboardInterrupt:
        print("\n[server] اتوقف بواسطة المستخدم")
    except Exception as e:
        print(f"\n[server] خطأ فادح: {e}")
        traceback.print_exc()
        sys.exit(1)


# ============ END PART 10 ============