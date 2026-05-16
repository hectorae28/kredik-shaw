"""
fetch_wakatime.py
Corre cada domingo via GitHub Actions.
Lee WAKATIME_API_KEY del entorno, llama a la API, y acumula
los datos de la semana en data/wakatime.json.
"""

import os, json, base64, datetime, pathlib
import requests

API_BASE = "https://wakatime.com/api/v1"
KEY      = os.environ["WAKATIME_API_KEY"]
AUTH     = base64.b64encode(KEY.encode()).decode()
HEADERS  = {"Authorization": f"Basic {AUTH}"}
OUT_FILE = pathlib.Path("data/wakatime.json")


def get(path, params=None):
    r = requests.get(f"{API_BASE}{path}", headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_week():
    today = datetime.date.today()
    # La semana que acaba de terminar (lunes-domingo anterior)
    end   = today - datetime.timedelta(days=today.weekday() + 1)
    start = end - datetime.timedelta(days=6)

    stats    = get("/users/current/stats/last_7_days")["data"]
    summaries = get("/users/current/summaries", {
        "start": start.isoformat(),
        "end":   end.isoformat(),
    })

    daily = []
    for day in summaries.get("data", []):
        daily.append({
            "date":          day["range"]["date"],
            "total_seconds": day["grand_total"]["total_seconds"],
        })

    def top(items, n=8):
        return [{"name": x["name"], "total_seconds": x["total_seconds"]}
                for x in sorted(items, key=lambda x: x["total_seconds"], reverse=True)[:n]]

    return {
        "week_start":     start.isoformat(),
        "week_end":       end.isoformat(),
        "fetched_at":     datetime.datetime.utcnow().isoformat() + "Z",
        "total_seconds":  stats.get("total_seconds", 0),
        "daily_average":  stats.get("daily_average", 0),
        "best_day":       stats.get("best_day", {}),
        "languages":      top(stats.get("languages", [])),
        "projects":       top(stats.get("projects", [])),
        "editors":        top(stats.get("editors", [])),
        "operating_systems": top(stats.get("operating_systems", [])),
        "categories":     top(stats.get("categories", [])),
        "machines":       top(stats.get("machines", [])),
        "daily":          daily,
    }


def main():
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Cargar histórico existente
    if OUT_FILE.exists():
        db = json.loads(OUT_FILE.read_text())
    else:
        db = {"weeks": []}

    week = fetch_week()

    # Evitar duplicados por week_start
    existing_starts = {w["week_start"] for w in db["weeks"]}
    if week["week_start"] not in existing_starts:
        db["weeks"].append(week)
        db["weeks"].sort(key=lambda w: w["week_start"])
        print(f"✅ Semana {week['week_start']} → {week['week_end']} agregada ({len(db['weeks'])} total)")
    else:
        # Actualizar la semana si ya existía (p.ej. re-run manual)
        db["weeks"] = [w if w["week_start"] != week["week_start"] else week for w in db["weeks"]]
        print(f"🔄 Semana {week['week_start']} actualizada")

    OUT_FILE.write_text(json.dumps(db, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
