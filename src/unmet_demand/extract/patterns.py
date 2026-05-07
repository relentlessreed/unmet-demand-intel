from __future__ import annotations

import re


REQUEST_PATTERNS = [
    re.compile(r"\bI wish there (?:was|were)\b(?P<request>[^.?!]{4,220})", re.I),
    re.compile(r"\bwhy doesn't this exist\b(?P<request>[^.?!]{0,220})", re.I),
    re.compile(r"\bcan someone make\b(?P<request>[^.?!]{4,220})", re.I),
    re.compile(r"\bI hate that\b(?P<request>[^.?!]{4,220})", re.I),
    re.compile(r"\bthere should be\b(?P<request>[^.?!]{4,220})", re.I),
    re.compile(r"\bis there a plugin for\b(?P<request>[^.?!]{4,220})", re.I),
    re.compile(r"\blooking for a tool that\b(?P<request>[^.?!]{4,220})", re.I),
    re.compile(r"\bI can't find\b(?P<request>[^.?!]{4,220})", re.I),
]

URGENCY_TERMS = {
    "blocked": 5,
    "deadline": 5,
    "urgent": 5,
    "shipping": 4,
    "wasting hours": 4,
    "every project": 4,
    "again": 3,
    "manual": 3,
}

EMOTION_TERMS = {
    "hate": 5,
    "painful": 5,
    "frustrating": 4,
    "annoying": 4,
    "impossible": 4,
    "tired": 4,
    "wish": 3,
}

MONETIZATION_TERMS = {
    "pay": 5,
    "paid": 5,
    "buy": 5,
    "commercial": 4,
    "client": 4,
    "studio": 4,
    "asset": 3,
    "plugin": 3,
    "tool": 3,
}
