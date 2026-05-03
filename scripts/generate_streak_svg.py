import datetime as dt
import html
import json
import os
import pathlib
import urllib.request


USERNAME = os.environ.get("USERNAME", "mdjunayet10")
TOKEN = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")

OUTPUT_PATH = pathlib.Path("assets/streak.svg")


def graphql_request(query, variables):
    if not TOKEN:
        raise RuntimeError("Missing GITHUB_TOKEN or GH_PAT.")

    payload = json.dumps(
        {
            "query": query,
            "variables": variables,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "github-streak-svg-generator",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"], indent=2))

    return data["data"]


def get_user_created_at():
    query = """
    query($login: String!) {
      user(login: $login) {
        createdAt
      }
    }
    """

    data = graphql_request(query, {"login": USERNAME})
    created_at = data["user"]["createdAt"]
    return dt.datetime.fromisoformat(created_at.replace("Z", "+00:00")).date()


def get_contribution_counts(start_date, end_date):
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """

    counts = {}

    current_start = start_date
    while current_start <= end_date:
        current_end = min(current_start + dt.timedelta(days=365), end_date)

        variables = {
            "login": USERNAME,
            "from": f"{current_start.isoformat()}T00:00:00Z",
            "to": f"{current_end.isoformat()}T23:59:59Z",
        }

        data = graphql_request(query, variables)
        weeks = data["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]

        for week in weeks:
            for day in week["contributionDays"]:
                day_date = dt.date.fromisoformat(day["date"])
                if start_date <= day_date <= end_date:
                    counts[day_date] = day["contributionCount"]

        current_start = current_end + dt.timedelta(days=1)

    return counts


def date_range(start_date, end_date):
    current = start_date
    while current <= end_date:
        yield current
        current += dt.timedelta(days=1)


def format_date(date_value):
    if date_value is None:
        return "-"
    return f"{date_value.strftime('%b')} {date_value.day}"


def calculate_current_streak(counts, today):
    if counts.get(today, 0) > 0:
        streak_end = today
    elif counts.get(today - dt.timedelta(days=1), 0) > 0:
        streak_end = today - dt.timedelta(days=1)
    else:
        return 0, None, None

    streak_start = streak_end
    streak_count = 0
    current = streak_end

    while counts.get(current, 0) > 0:
        streak_count += 1
        streak_start = current
        current -= dt.timedelta(days=1)

    return streak_count, streak_start, streak_end


def calculate_longest_streak(counts, start_date, end_date):
    best_count = 0
    best_start = None
    best_end = None

    current_count = 0
    current_start = None

    for day in date_range(start_date, end_date):
        if counts.get(day, 0) > 0:
            if current_count == 0:
                current_start = day
            current_count += 1

            if current_count > best_count:
                best_count = current_count
                best_start = current_start
                best_end = day
        else:
            current_count = 0
            current_start = None

    return best_count, best_start, best_end


def make_svg(total, current_streak, current_start, current_end, longest_streak, longest_start, longest_end):
    username = html.escape(USERNAME)

    current_range = f"{format_date(current_start)} - {format_date(current_end)}"
    longest_range = f"{format_date(longest_start)} - {format_date(longest_end)}"

    return f"""<svg width="760" height="300" viewBox="0 0 760 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="760" height="300" rx="18" fill="#050810"/>

  <text x="380" y="42" text-anchor="middle" fill="#06D6DB" font-family="Arial, Helvetica, sans-serif" font-size="24" font-weight="700">
    GitHub Streak Stats
  </text>

  <text x="380" y="70" text-anchor="middle" fill="#8A8FBD" font-family="Arial, Helvetica, sans-serif" font-size="13">
    @{username}
  </text>

  <line x1="253" y1="100" x2="253" y2="245" stroke="#06D6DB" stroke-opacity="0.8"/>
  <line x1="506" y1="100" x2="506" y2="245" stroke="#06D6DB" stroke-opacity="0.8"/>

  <text x="126" y="140" text-anchor="middle" fill="#FFFFFF" font-family="Arial, Helvetica, sans-serif" font-size="38" font-weight="700">
    {total}
  </text>
  <text x="126" y="178" text-anchor="middle" fill="#FFFFFF" font-family="Arial, Helvetica, sans-serif" font-size="18" font-weight="600">
    Total Contributions
  </text>
  <text x="126" y="210" text-anchor="middle" fill="#8A8FBD" font-family="Arial, Helvetica, sans-serif" font-size="15">
    All Time
  </text>

  <circle cx="380" cy="142" r="54" stroke="#7C6FFF" stroke-width="8"/>
  <text x="380" y="154" text-anchor="middle" fill="#FF61DC" font-family="Arial, Helvetica, sans-serif" font-size="38" font-weight="700">
    {current_streak}
  </text>
  <text x="380" y="210" text-anchor="middle" fill="#06D6DB" font-family="Arial, Helvetica, sans-serif" font-size="20" font-weight="700">
    Current Streak
  </text>
  <text x="380" y="238" text-anchor="middle" fill="#8A8FBD" font-family="Arial, Helvetica, sans-serif" font-size="15">
    {current_range}
  </text>

  <text x="633" y="140" text-anchor="middle" fill="#FFFFFF" font-family="Arial, Helvetica, sans-serif" font-size="38" font-weight="700">
    {longest_streak}
  </text>
  <text x="633" y="178" text-anchor="middle" fill="#FFFFFF" font-family="Arial, Helvetica, sans-serif" font-size="18" font-weight="600">
    Longest Streak
  </text>
  <text x="633" y="210" text-anchor="middle" fill="#8A8FBD" font-family="Arial, Helvetica, sans-serif" font-size="15">
    {longest_range}
  </text>
</svg>
"""


def main():
    today = dt.datetime.now(dt.timezone.utc).date()
    created_at = get_user_created_at()

    counts = get_contribution_counts(created_at, today)

    total = sum(counts.values())
    current_streak, current_start, current_end = calculate_current_streak(counts, today)
    longest_streak, longest_start, longest_end = calculate_longest_streak(counts, created_at, today)

    svg = make_svg(
        total=total,
        current_streak=current_streak,
        current_start=current_start,
        current_end=current_end,
        longest_streak=longest_streak,
        longest_start=longest_start,
        longest_end=longest_end,
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(svg, encoding="utf-8")

    print(f"Generated {OUTPUT_PATH}")
    print(f"Current streak: {current_streak}")
    print(f"Current range: {format_date(current_start)} - {format_date(current_end)}")


if __name__ == "__main__":
    main()
