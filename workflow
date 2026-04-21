name: Update YouTube Subscriber Count

on:
  schedule:
    - cron: "*/10 * * * *"   # every 10 min
  workflow_dispatch:

permissions:
  contents: write

jobs:
  update-readme:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Fetch live count from SocialCounts API
        id: subs
        run: |
          set -e

          CHANNEL_ID="UCw3J_tpKsFmVPVbWXcKqD_g"
          API_URL="https://api.socialcounts.org/youtube-live-subscriber-count/${CHANNEL_ID}"

          echo "Fetching: $API_URL"
          JSON=$(curl -sS "$API_URL")
          echo "API response: $JSON"

          # Parse count safely using Python (no jq dependency issues)
          COUNT=$(python3 - << 'PY'
import json,sys
raw = """$JSON"""
try:
    data = json.loads(raw)
    c = data.get("est_sub")
    if c is None:
        c = data.get("count")
    if c is None:
        raise ValueError("No est_sub/count in response")
    print(int(c))
except Exception as e:
    print("", end="")
PY
)

          if [ -z "$COUNT" ]; then
            echo "Could not parse count from SocialCounts API."
            exit 1
          fi

          FORMATTED=$(python3 - << PY
n = int("$COUNT")
print(f"{n:,}")
PY
)
          echo "count=$COUNT" >> "$GITHUB_OUTPUT"
          echo "formatted=$FORMATTED" >> "$GITHUB_OUTPUT"
          echo "Final formatted count: $FORMATTED"

      - name: Update README marker
        env:
          NEW_COUNT: ${{ steps.subs.outputs.formatted }}
        run: |
          python3 - << 'PY'
import os, re
from pathlib import Path

p = Path("README.md")
text = p.read_text(encoding="utf-8")
new_count = os.environ["NEW_COUNT"]

pattern = r"(<!-- YT_SUB_COUNT -->)(.*?)(<!-- /YT_SUB_COUNT -->)"
repl = r"\1" + new_count + r"\3"
new_text, n = re.subn(pattern, repl, text, flags=re.DOTALL)

if n == 0:
    raise SystemExit("Marker not found: <!-- YT_SUB_COUNT --> ... <!-- /YT_SUB_COUNT -->")

p.write_text(new_text, encoding="utf-8")
print(f"Updated README count to: {new_count}")
PY

      - name: Commit and push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

          git add README.md
          git diff --staged --quiet && echo "No changes to commit" && exit 0

          git commit -m "chore: update YouTube subscriber count"
          git push
