# World Cup 2026 Sweepstake — Auto Poster

Posts two updates a day to the office WeCom group, on a clock, with no one in the loop:

- **8:00am NZT** — final scores for any games that finished overnight, then a preview of today's remaining games (team + the sweepstake player who drew it, with NZ kickoff times).
- **6:00pm NZT** — final scores for games that have finished so far today. Anything still in play rolls into the next morning's post.

A score is only ever posted once the match is **final** — never in-progress or predicted.

## How it works

GitHub Actions runs `send_update.py` on two cron schedules. The script asks the Anthropic API (with web search) to pull the live World Cup fixtures/scores, maps every team to its owner using `roster.csv`, builds the message, and posts it to your WeCom webhook.

## Setup — the easy way (one command)

Two one-time prerequisites:
1. Install the GitHub CLI: https://cli.github.com
2. Sign in: `gh auth login` (opens your browser — no tokens to paste anywhere)

Then, from inside the unzipped folder, run:

- **Mac / Linux / WSL / Git Bash:** `./setup.sh`
- **Windows PowerShell:** `./setup.ps1`

The script creates a private repo, pushes the files, asks for your two secrets (typed straight into your own terminal, hidden, never stored), sets them on the repo, and offers to fire a test post. That's the whole thing.

## Setup — manual (if you'd rather click through GitHub)

1. **Create a GitHub repo** (private is fine) and add these files to it:
   - `send_update.py`
   - `roster.csv`
   - `requirements.txt`
   - `.github/workflows/sweepstake.yml`

2. **Add two repository secrets** (repo → Settings → Secrets and variables → Actions → New repository secret):
   - `ANTHROPIC_API_KEY` — your Anthropic API key (console.anthropic.com → API keys).
   - `WECOM_WEBHOOK_URL` — the full office-group webhook URL (`https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...`).

   These live only in Secrets, never in the code.

3. **Test it before it goes live**: repo → Actions → "World Cup Sweepstake Update" → *Run workflow* → pick `morning` or `evening`. It posts immediately so you can check it in the group. The run log also prints the exact message it sent.

That's it — once the secrets are in, the 8am and 6pm posts fire automatically every day.

## Good to know

- **Timing**: the crons are `0 20 * * *` and `0 6 * * *` UTC, which are 8am and 6pm NZT *while NZ is on standard time (UTC+12)* — true for the whole tournament (June–July 2026). If you ever reuse this outside those months, adjust for NZ daylight saving (UTC+13 → use `0 19` and `0 5`).
- GitHub's scheduled runs can occasionally start a few minutes late under load; not an issue for this.
- WeCom messages can't be unsent. The evening post only contains finished games, and the morning post only scores finished games, so there's nothing to retract — but if you'd rather eyeball each one, just don't add the schedule and run it from the Actions tab (or from a chat with the skill) when you want it.
- To change the roster mid-tournament (someone swaps a team, etc.), edit `roster.csv` and push.
- Cost is tiny — two short API calls a day.
