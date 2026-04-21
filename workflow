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
          JSON="$(curl -fsSL "$URL")"
          echo "$JSON" > yt.json

          COUNT="$(python3 - << 'PY'
import json
with open("yt.json", "r", encoding="utf-8") as f:
    data = json.load(f)

items = data.get("items", [])
if not items:
    raise SystemExit("No items returned. Check API key, channel ID, or quota.")

count = items[0].get("statistics", {}).get("subscriberCount")
if count is None:
    raise SystemExit("subscriberCount not found in API response.")

print(count)
PY
)"
          FORMATTED="$(python3 - << PY
n = int("$COUNT")
print(f"{n:,}")
PY
)"

          echo "count=$COUNT" >> "$GITHUB_OUTPUT"
          echo "formatted=$FORMATTED" >> "$GITHUB_OUTPUT"
          echo "Final formatted count: $FORMATTED"

      - name: Update README marker
        env:
          NEW_COUNT: ${{ steps.subs.outputs.formatted }}
        run: |
          python3 - << 'PY'
import os
import re
from pathlib import Path

p = Path("README.md")
text = p.read_text(encoding="utf-8")
new_count = os.environ["NEW_COUNT"]

pattern = r"(<!-- YT_SUB_COUNT -->)(.*?)(<!-- /YT_SUB_COUNT -->)"
replacement = r"\1" + new_count + r"\3"
new_text, n = re.subn(pattern, replacement, text, flags=re.DOTALL)

if n == 0:
    raise SystemExit("Marker not found: <!-- YT_SUB_COUNT -->...<!-- /YT_SUB_COUNT -->")

p.write_text(new_text, encoding="utf-8")
print(f"Updated README count to: {new_count}")
PY

      - name: Commit and push
        run: |
          set -e
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

          git add README.md
          git diff --staged --quiet && { echo "No changes to commit"; exit 0; }

          git commit -m "chore: update YouTube subscriber count"
          git push
