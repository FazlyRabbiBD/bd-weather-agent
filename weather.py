import os, requests, pandas as pd
from datetime import datetime, timezone, timedelta
from openai import OpenAI

MODEL = "openrouter/free"
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])

CITIES = {"Dhaka": (23.81, 90.41), "Chattogram": (22.36, 91.78), "Khulna": (22.85, 89.54),
          "Rajshahi": (24.37, 88.60), "Barishal": (22.70, 90.37), "Sylhet": (24.89, 91.87),
          "Rangpur": (25.74, 89.28), "Mymensingh": (24.75, 90.41)}
SKY = {0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Cloudy", 45: "Fog", 48: "Fog",
       51: "Drizzle", 53: "Drizzle", 55: "Drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
       80: "Showers", 81: "Showers", 82: "Heavy showers", 95: "Thunderstorm"}

def get_weather(lat, lon):
    url = ("https://api.open-meteo.com/v1/forecast"
           f"?latitude={lat}&longitude={lon}&timezone=Asia/Dhaka"
           "&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m")
    c = requests.get(url, timeout=15).json()["current"]
    return {"Temp °C": c["temperature_2m"], "Humidity %": c["relative_humidity_2m"],
            "Rain mm": c["precipitation"], "Wind km/h": c["wind_speed_10m"],
            "Sky": SKY.get(c["weather_code"], f"Code {c['weather_code']}")}

# 1. Fetch
table = pd.DataFrame([{"City": city, **get_weather(*xy)} for city, xy in CITIES.items()])

# 2. Summarise
summary = None
try:
    prompt = ("Current weather in Bangladesh's 8 divisional cities:\n\n" + table.to_string(index=False)
              + "\n\nSummarise in 2-3 short lines: overall condition, hottest and coolest city, any rain. "
                "Use only these numbers. Reply with the summary only. /no_think")
    r = client.chat.completions.create(model=MODEL, max_tokens=1000,
                                       messages=[{"role": "user", "content": prompt}])
    summary = r.choices[0].message.content
except Exception as e:
    print("Model error:", e)

if not summary:   # backup if the model fails
    hot, cool = table.loc[table["Temp °C"].idxmax()], table.loc[table["Temp °C"].idxmin()]
    summary = (f"Hottest: {hot['City']} ({hot['Temp °C']}°C), coolest: {cool['City']} "
               f"({cool['Temp °C']}°C). Most common sky: {table['Sky'].mode()[0]}.")

# 3. Build the web page
now = datetime.now(timezone(timedelta(hours=6))).strftime("%d %b %Y, %I:%M %p")
html = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bangladesh Weather</title>
<style>
 body{{font-family:system-ui,sans-serif;max-width:760px;margin:40px auto;padding:0 16px;
      background:#f7f7f5;color:#222}}
 .card{{background:#fff;border:1px solid #e3e3e0;border-radius:10px;padding:16px 20px;margin:16px 0}}
 table{{width:100%;border-collapse:collapse;font-size:15px}}
 th,td{{padding:8px;border-bottom:1px solid #eee;text-align:left}}
 th{{color:#666;font-weight:600}}
 .muted{{color:#777;font-size:14px}}
 .wrap{{overflow-x:auto}}
</style></head><body>
<h1>Bangladesh Weather</h1>
<p class="muted">Updated {now} (Dhaka time) · Data: Open-Meteo · Summary: {MODEL}</p>
<div class="card"><strong>Summary</strong><p>{summary}</p></div>
<div class="card wrap">{table.to_html(index=False, border=0)}</div>
</body></html>"""

open("index.html", "w", encoding="utf-8").write(html)
print(summary)