name: Update YouTube Subscriber Count

on:
  schedule:
    - cron: "*/10 * * * *"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  update-readme:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Get subscriber count from YouTube API
        id: subs
        env:
          YOUTUBE_API_KEY: ${{ secrets.YOUTUBE_API_KEY }}
          CHANNEL_ID: UCw3J_tpKsFmVPVbWXcKqD_g
        run: |
          set -euo pipefail

          URL="https://www.googleapis.com/youtube/v3/channels?part=statistics&id=${CHANNEL_ID}&key=${YOUTUBE_API_KEY}"
          JSON=$(curl -sS "$URL")
          echo "API response: $JSON"

          COUNT=$(python3 - << 'PY'
import json, os
raw = os.popen('cat <<EOF\n'"$JSON"'\nEOF').read()
data = json.loads(raw)
items = data.get("items", [])
if not items:
    raise SystemExit("No items returned. Check API key/channel ID/quota.")
count = items[0]["statistics"]["subscriberCount"]
print(count)
PY
)

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
    raise SystemExit("Marker not found in README.md")

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
