#!/usr/bin/env python3
"""
World Cup 2026 sweepstake — scheduled WeCom poster.

Runs twice a day from GitHub Actions:
  MODE=morning  -> overnight final scores + preview of today's remaining games
  MODE=evening  -> final scores for games finished by 6pm NZT

Uses the Anthropic API (with web search) to build the message from live
fixtures/scores, maps every team to its sweepstake owner from roster.csv,
then posts to the WeCom group webhook.

Env vars (set as GitHub Secrets / workflow env):
  ANTHROPIC_API_KEY    your Anthropic API key
  WECOM_WEBHOOK_URL    full webhook, https://qyapi.weixin.qq.com/.../send?key=...
  MODE                 "morning" or "evening"
"""
import os, sys, csv, json, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
import anthropic

MODEL = "claude-sonnet-4-6"
NZ = ZoneInfo("Pacific/Auckland")
HERE = os.path.dirname(os.path.abspath(__file__))
FOOTER = "🤖 Automated by Claude on behalf of Kate Pilkinton"


def load_roster_text():
    rows = []
    with open(os.path.join(HERE, "roster.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(f"{r['team']} -> {r['person']}")
    return "\n".join(rows)


def build_message(mode, roster_text):
    now = datetime.now(NZ)
    now_str = now.strftime("%A %d %B %Y, %I:%M%p NZT")

    common = f"""You are writing a FIFA World Cup 2026 update for a New Zealand office sweepstake.
It is currently {now_str}.

SWEEPSTAKE ROSTER (team -> the person who drew it). This is the source of truth — never guess an owner:
{roster_text}

Five people drew two teams, so they may appear more than once. Every fixture you mention MUST name both
the country AND the person who drew it, for both teams.

Use web search to get the real, current World Cup 2026 fixtures and scores. Kickoffs are on US/Canada/Mexico
clocks; convert kickoff times to NZT (NZ is UTC+12 in June/July, no daylight saving). A score is only valid
once the match is FINAL — never report an in-progress, predicted, or unconfirmed score. If unsure a game is
finished, leave it out.

Resolve name variants to the roster: Czechia=Czech Republic, Korea Republic/Korea=South Korea,
United States/USMNT=USA, Turkiye=Turkey, Cabo Verde=Cape Verde, Bosnia and Herzegovina=Bosnia & Herzegovina,
Cote d'Ivoire=Ivory Coast, Curacao=Curaçao, DR Congo=Democratic Republic of the Congo.

Output ONLY the finished message text — no preamble, no explanation, no markdown code fences. Use a light,
fun office tone with country flag emoji. Plain text only (this goes to WeCom)."""

    if mode == "morning":
        task = """TASK — MORNING POST (8am NZT):
1) First, FINAL SCORES for any games that finished overnight (roughly since 6pm NZT yesterday up to now) that
   would not already have been reported in last evening's 6pm post. For each:
   "<flag> Team A (Owner A) X–Y Team B (Owner B) <flag>"
   then a line calling out the winner's owner, e.g. "   ✅ <Person> takes the win (<Team>)", or for a draw
   "   🤝 Draw — a point each for <Person A> and <Person B>". If no games finished overnight, skip this section.
2) Then, PREVIEW of the games still to come today (NZ date), each as
   "<flag> Team A (Person A)  vs  <flag> Team B (Person B)  —  <kickoff> NZT  ·  Group <X>".

Header: "⚽ WORLD CUP DAILY — <Day Date> (NZ)". If there were overnight results, put them under a
"Overnight results:" line first, then "Still to come today:" before the previews. End with a short
good-luck line. If there are genuinely no games today and none overnight, say so cheerfully."""
    else:
        task = """TASK — EVENING POST (6pm NZT):
FINAL SCORES only, for games that have finished by now today (NZ date) and were not already in this morning's
8am post. Any game still in play is omitted (it rolls into tomorrow morning's post). For each finished game:
"<flag> Team A (Owner A) X–Y Team B (Owner B) <flag>" then "   ✅ <Person> takes the win (<Team>)" or
"   🤝 Draw — a point each for <Person A> and <Person B>".
Header: "⚽ WORLD CUP RESULTS — <Day Date>". If no games have finished since the morning post, say so briefly."""

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1800,
        system=common,
        messages=[{"role": "user", "content": task}],
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
    return text


def post_to_wecom(message):
    url = os.environ["WECOM_WEBHOOK_URL"]
    full = f"{message}\n\n{FOOTER}"
    # WeCom hard limit is 2048 chars; split on blank lines if needed.
    chunks, cur = [], ""
    for block in full.split("\n\n"):
        if len(cur) + len(block) + 2 > 2000 and cur:
            chunks.append(cur.strip())
            cur = block
        else:
            cur = f"{cur}\n\n{block}" if cur else block
    if cur.strip():
        chunks.append(cur.strip())

    for i, chunk in enumerate(chunks):
        payload = json.dumps({"msgtype": "text", "text": {"content": chunk}}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as r:
            res = json.loads(r.read().decode())
        print(f"WeCom chunk {i+1}/{len(chunks)}: {res}")
        if res.get("errcode") != 0:
            sys.exit(f"WeCom send failed: {res}")


def main():
    mode = os.environ.get("MODE", "morning").strip().lower()
    if mode not in ("morning", "evening"):
        sys.exit(f"Invalid MODE: {mode!r} (expected morning or evening)")
    message = build_message(mode, load_roster_text())
    if not message:
        sys.exit("Model returned an empty message — nothing sent.")
    print("----- MESSAGE -----\n" + message + "\n-------------------")
    post_to_wecom(message)
    print("Done.")


if __name__ == "__main__":
    main()
