name: Update YouTube Subscriber Count

on:
  schedule:
    - cron: "*/10 * * * *"   # every 10 minutes
  workflow_dispatch:

permissions:
  contents: write

jobs:
  update-readme:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Fetch subscriber count from SocialCounts
        id: subs
        run: |
          CHANNEL_ID="UCw3J_tpKsFmVPVbWXcKqD_g"
          URL="https://socialcounts.org/youtube-live-subscriber-count/${CHANNEL_ID}"

          # Fetch page HTML
          HTML=$(curl -sL "$URL")

          # Try to extract count like 78,859 from JSON/script content
          COUNT=$(echo "$HTML" | grep -oE '"count":[0-9]+' | head -n1 | grep -oE '[0-9]+')

          # Fallback: look for large comma-formatted number in page
          if [ -z "$COUNT" ]; then
            RAW=$(echo "$HTML" | grep -oE '[0-9]{1,3}(,[0-9]{3})+' | head -n1)
            COUNT=$(echo "$RAW" | tr -d ',')
          fi

          if [ -z "$COUNT" ]; then
            echo "Could not parse subscriber count"
            exit 1
          fi

          # Format with commas
          FORMATTED=$(printf "%'d\n" "$COUNT" 2>/dev/null || echo "$COUNT")
          echo "formatted=$FORMATTED" >> $GITHUB_OUTPUT
          echo "count=$COUNT" >> $GITHUB_OUTPUT

      - name: Update README marker
        run: |
          python3 - << 'PY'
          import re
          from pathlib import Path

          readme = Path("README.md")
          text = readme.read_text(encoding="utf-8")

          new_count = "${{ steps.subs.outputs.formatted }}"
          pattern = r"(<!-- YT_SUB_COUNT -->)(.*?)(<!-- /YT_SUB_COUNT -->)"
          repl = r"\1" + new_count + r"\3"

          new_text, n = re.subn(pattern, repl, text, flags=re.DOTALL)

          if n == 0:
              raise SystemExit("Marker not found in README.md")

          readme.write_text(new_text, encoding="utf-8")
          print(f"Updated subscriber count to {new_count}")
          PY

      - name: Commit changes
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

          git add README.md
          git diff --staged --quiet && echo "No changes to commit" && exit 0

          git commit -m "chore: update YouTube subscriber count"
          git push
