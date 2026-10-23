#!/usr/bin/env python3
"""Generate a dark neon GitHub 31-day contribution line/area SVG.

Uses GitHub's contribution calendar via the official GraphQL API.
No third-party image host or non-standard Python packages required.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen

USERNAME = os.environ.get("GITHUB_ACTIVITY_USERNAME", "mdjunayet10")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUTPUT = Path("assets/github-activity-graph.svg")


def fetch_daily_counts(today):
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN is required; run this using the provided GitHub Actions workflow")

    first_day = today - timedelta(days=30)
    query = """query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            weeks { contributionDays { date contributionCount } }
          }
        }
      }
    }"""
    payload = json.dumps({
        "query": query,
        "variables": {
            "login": USERNAME,
            "from": first_day.isoformat() + "T00:00:00Z",
            "to": today.isoformat() + "T23:59:59Z",
        },
    }).encode("utf-8")
    request = Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "github-profile-activity-svg",
            "Accept": "application/vnd.github+json",
        },
        method="POST",
    )
    with urlopen(request, timeout=40) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError(f"GitHub GraphQL query failed: {result['errors']}")
    user = (result.get("data") or {}).get("user")
    if not user:
        raise RuntimeError(f"GitHub user {USERNAME!r} not found or could not be read")

    calendar = user["contributionsCollection"]["contributionCalendar"]
    counts = {}
    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            counts[day["date"]] = int(day["contributionCount"])

    dates = [first_day + timedelta(days=i) for i in range(31)]
    return dates, [counts.get(day.isoformat(), 0) for day in dates]


def svg_path(points):
    """A smooth Catmull-Rom-like curve through the actual daily points."""
    commands = [f"M {points[0][0]:.2f} {points[0][1]:.2f}"]
    for i in range(len(points) - 1):
        prev = points[max(i - 1, 0)]
        curr = points[i]
        nxt = points[i + 1]
        future = points[min(i + 2, len(points) - 1)]
        control1y = curr[1] + (nxt[1] - prev[1]) / 6
        control2y = nxt[1] - (future[1] - curr[1]) / 6
        low, high = sorted([curr[1], nxt[1]])
        control1y = min(max(control1y, low), high)
        control2y = min(max(control2y, low), high)
        dx = (nxt[0] - curr[0]) / 3
        commands.append(
            f"C {curr[0]+dx:.2f} {control1y:.2f}, "
            f"{nxt[0]-dx:.2f} {control2y:.2f}, {nxt[0]:.2f} {nxt[1]:.2f}"
        )
    return " ".join(commands)


def render_svg(dates, counts):
    width, height = 1120, 330
    left, right, top, bottom = 74, 25, 64, 275
    plot_w = width - left - right
    plot_h = bottom - top
    peak = max(counts)
    step = max(1, (peak + 3) // 4)
    max_y = max(4, step * 4)
    points = [
        (left + i * plot_w / 30, bottom - min(n, max_y) * plot_h / max_y)
        for i, n in enumerate(counts)
    ]
    curve = svg_path(points)
    area = curve + f" L {points[-1][0]:.2f} {bottom} L {points[0][0]:.2f} {bottom} Z"
    parts = [f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">GitHub Contribution Activity — {escape(USERNAME)}</title>
<desc id="desc">Daily GitHub contribution counts for the past 31 days shown as a purple line with yellow points on a dark background. Data updated {dates[-1].isoformat()} UTC.</desc>
<defs>
  <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#8B5CF6" stop-opacity="0.31"/>
    <stop offset="100%" stop-color="#8B5CF6" stop-opacity="0.025"/>
  </linearGradient>
  <filter id="glow" x="-20%" y="-100%" width="140%" height="300%">
    <feGaussianBlur stdDeviation="4"/>
  </filter>
</defs>
<rect width="{width}" height="{height}" rx="12" fill="#0D1117"/>
<text x="74" y="35" font-size="18" font-weight="700" fill="#00E5FF" font-family="Arial, sans-serif">GitHub Contribution Activity</text>
<text x="1043" y="34" text-anchor="end" font-size="12" fill="#8B949E" font-family="Arial, sans-serif">LAST 31 DAYS</text>"""]
    for i in range(5):
        value = i * step
        y = bottom - value * plot_h / max_y
        parts.append(f'<line x1="{left}" x2="{width-right}" y1="{y:.2f}" y2="{y:.2f}" stroke="#283344" stroke-width="1" stroke-dasharray="4 5"/>')
        parts.append(f'<text x="{left-17}" y="{y+4:.2f}" text-anchor="end" font-size="12" fill="#8B949E" font-family="Arial, sans-serif">{value}</text>')
    for i in (0, 5, 10, 15, 20, 25, 30):
        x, _ = points[i]
        label = escape(dates[i].strftime("%b %d"))
        parts.append(f'<text x="{x:.2f}" y="{bottom+25}" text-anchor="middle" font-size="12" fill="#8B949E" font-family="Arial, sans-serif">{label}</text>')
    parts.append(f'<path d="{area}" fill="url(#area)"/>')
    parts.append(f'<path d="{curve}" fill="none" stroke="#8B5CF6" stroke-width="8" opacity="0.20" filter="url(#glow)"/>')
    parts.append(f'<path d="{curve}" fill="none" stroke="#8B5CF6" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>')
    for x, y in points:
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.8" fill="#FACC15" stroke="#0D1117" stroke-width="1.4"/>')
    parts.append(f'<text x="{width-right}" y="{height-10}" text-anchor="end" font-size="11" fill="#768390" font-family="Arial, sans-serif">Updated daily via GitHub Actions</text>')
    parts.append('</svg>')
    return "\n".join(parts) + "\n"


def main():
    today = datetime.now(timezone.utc).date()
    dates, counts = fetch_daily_counts(today)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render_svg(dates, counts), encoding="utf-8")
    print(f"Wrote {OUTPUT} ({sum(counts)} public/profile-visible contributions in 31 days)")


if __name__ == "__main__":
    main()
