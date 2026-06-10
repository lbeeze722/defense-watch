#!/usr/bin/env python3
"""Defense Watch data fetcher.

Pulls quotes for a defense/aerospace universe from Yahoo Finance,
flags movers beyond +/-3%, pulls news from Google News RSS, and
writes everything to data.js for the dashboard to render.
"""

import json
import sys
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

OUT = Path(__file__).parent / "data.js"

# symbol: (name, vertical, description)
UNIVERSE = {
    "LMT": ("Lockheed Martin", "Prime Contractors",
            "Largest US defense prime — F-35 fighter, missiles & fire control (PAC-3, HIMARS), Sikorsky helicopters, and space systems."),
    "RTX": ("RTX Corp", "Prime Contractors",
            "Defense and aerospace giant — Raytheon missiles & air defense (Patriot, AMRAAM), Pratt & Whitney engines, Collins Aerospace avionics."),
    "NOC": ("Northrop Grumman", "Prime Contractors",
            "Prime behind the B-21 stealth bomber, Sentinel ICBM, military space systems, and advanced sensors."),
    "GD": ("General Dynamics", "Prime Contractors",
           "Abrams tanks and combat vehicles, nuclear submarines (Electric Boat), Gulfstream business jets, and defense IT (GDIT)."),
    "BA": ("Boeing", "Prime Contractors",
           "Commercial jets plus defense: F-15EX, KC-46 tanker, Apache helicopter, satellites, and weapons programs."),
    "LHX": ("L3Harris", "Prime Contractors",
            "Tactical radios, ISR and space sensors, electronic warfare, and Aerojet Rocketdyne solid rocket motors."),
    "ESLT": ("Elbit Systems", "Prime Contractors",
             "Israel's largest defense company — drones, electro-optics, EW, munitions, and land systems; a direct beneficiary of Israeli conflict demand."),
    "HII": ("Huntington Ingalls", "Shipbuilding & Naval",
            "America's largest military shipbuilder — nuclear aircraft carriers and submarines (Newport News) plus surface combatants (Ingalls)."),
    "BWXT": ("BWX Technologies", "Shipbuilding & Naval",
             "Sole maker of nuclear reactors for US Navy carriers and submarines; also nuclear fuel and government nuclear services."),
    "GE": ("GE Aerospace", "Engines & Suppliers",
           "World's largest jet engine maker — military (F110, T700) and commercial (LEAP, GE9X) propulsion and services."),
    "HWM": ("Howmet Aerospace", "Engines & Suppliers",
            "Engineered metal components — jet engine airfoils, fasteners, and titanium structures for commercial and defense aircraft."),
    "TDG": ("TransDigm", "Engines & Suppliers",
            "Roll-up of proprietary aerospace components with strong pricing power; large aftermarket and defense exposure."),
    "HEI": ("HEICO", "Engines & Suppliers",
            "FAA-approved replacement parts and niche defense/space electronics; serial acquirer in aerospace aftermarket."),
    "TXT": ("Textron", "Engines & Suppliers",
            "Bell helicopters (V-280 FLRAA winner), Cessna/Beechcraft aircraft, and Textron Systems unmanned/land platforms."),
    "CW": ("Curtiss-Wright", "Engines & Suppliers",
           "Flow control for naval nuclear propulsion, embedded defense computing, and actuation systems."),
    "ATRO": ("Astronics", "Engines & Suppliers",
             "Aircraft lighting, power distribution, and test systems for commercial and military aviation."),
    "OSK": ("Oshkosh", "Ground & Vehicles",
            "Tactical military trucks (JLTV legacy), aircraft rescue vehicles, and specialty/access equipment."),
    "PLTR": ("Palantir", "Defense Tech & Software",
             "AI/data platforms (Gotham, Maven) powering US and allied military intelligence, targeting, and enterprise ops."),
    "AXON": ("Axon Enterprise", "Defense Tech & Software",
             "Tasers, body cameras, and the Axon Evidence cloud for law enforcement; expanding into drones and counter-drone."),
    "KTOS": ("Kratos Defense", "Defense Tech & Software",
             "Low-cost jet drones (Valkyrie), target drones, hypersonics test vehicles, and microwave electronics."),
    "MRCY": ("Mercury Systems", "Defense Tech & Software",
             "Secure processing subsystems — radar, EW, and avionics computing boards embedded in major weapons programs."),
    "DRS": ("Leonardo DRS", "Defense Tech & Software",
            "Sensing, network computing, force protection, and naval electric propulsion; majority-owned by Italy's Leonardo."),
    "KULR": ("KULR Technology", "Defense Tech & Software",
             "Thermal management and battery-safety tech for space, defense, and energy storage; also holds bitcoin treasury."),
    "AVAV": ("AeroVironment", "Drones & Counter-UAS",
             "Switchblade loitering munitions and small recon drones (Puma/Raven); acquired BlueHalo for space/counter-UAS scale."),
    "ONDS": ("Ondas Holdings", "Drones & Counter-UAS",
             "Autonomous drone platforms (American Robotics, Airobotics) and counter-drone systems plus industrial wireless networks."),
    "RCAT": ("Red Cat Holdings", "Drones & Counter-UAS",
             "Small military drones — won the US Army's Short Range Reconnaissance program with its Black Widow drone."),
    "UMAC": ("Unusual Machines", "Drones & Counter-UAS",
             "NDAA-compliant drone components and FPV drones; positioned in the US drone supply-chain onshoring push."),
    "RKLB": ("Rocket Lab", "Space",
             "Electron small-launch rocket, Neutron medium rocket in development, and a growing satellite/components business."),
    "RDW": ("Redwire", "Space",
            "Space infrastructure — solar arrays, sensors, in-space manufacturing; expanding into defense space and drones (Edge Autonomy)."),
    "LUNR": ("Intuitive Machines", "Space",
             "Lunar landers and services for NASA (CLPS, Near Space Network); first commercial company to land on the Moon."),
    "ACHR": ("Archer Aviation", "eVTOL & Air Mobility",
             "Midnight electric air taxi in FAA certification; defense arm partnering with Anduril on hybrid VTOL aircraft."),
    "JOBY": ("Joby Aviation", "eVTOL & Air Mobility",
             "Leading eVTOL air-taxi developer backed by Toyota and Delta; supplies aircraft to the US Air Force via Agility Prime."),
    "LDOS": ("Leidos", "Gov Services & IT",
             "Largest federal IT/services contractor — defense digital modernization, hypersonics support, health and intel missions."),
    "BAH": ("Booz Allen", "Gov Services & IT",
            "Consulting and AI/cyber services deeply embedded in defense and intelligence agencies."),
    "SAIC": ("SAIC", "Gov Services & IT",
             "Systems integration and IT modernization for defense, space, and civilian agencies."),
    "CACI": ("CACI Intl", "Gov Services & IT",
             "Intelligence services, signals/EW technology, and federal network modernization."),
    "KBR": ("KBR", "Gov Services & IT",
            "Government engineering and logistics plus sustainable technology solutions; major military base and space support."),
    "VSEC": ("VSE Corp", "Gov Services & IT",
             "Aviation aftermarket parts distribution and MRO services for commercial and defense fleets."),
    "VVX": ("V2X", "Gov Services & IT",
            "Global military base operations, logistics, and aircraft maintenance across combatant commands."),
    "PSN": ("Parsons", "Gov Services & IT",
            "Cyber/EW, missile defense engineering, space ground systems, and critical infrastructure for federal customers."),
}

VERTICAL_ORDER = [
    "Prime Contractors", "Defense Tech & Software", "Drones & Counter-UAS",
    "Space", "Shipbuilding & Naval", "Engines & Suppliers",
    "eVTOL & Air Mobility", "Ground & Vehicles", "Gov Services & IT",
]

MOVER_THRESHOLD = 3.0
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}


def http_get(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_spark(symbol):
    """5-day close series for sparklines, plus average full-day volume."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=90m&range=5d"
    result = json.loads(http_get(url))["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    closes = [round(c, 2) for c in quote["close"] if c is not None]

    et = ZoneInfo("America/New_York")
    today = datetime.now(et).date()
    day_vol = {}
    for ts, vol in zip(result.get("timestamp", []), quote.get("volume") or []):
        if vol:
            d = datetime.fromtimestamp(ts, et).date()
            day_vol[d] = day_vol.get(d, 0) + vol
    full_days = [v for d, v in day_vol.items() if d != today]
    avg_vol = sum(full_days) / len(full_days) if full_days else None
    return closes, avg_vol


def session_fraction():
    """Fraction of the regular trading session elapsed (1.0 outside market hours)."""
    now = datetime.now(ZoneInfo("America/New_York"))
    mins = now.hour * 60 + now.minute
    if now.weekday() < 5 and 570 <= mins < 960:
        return max((mins - 570) / 390, 0.08)
    return 1.0


def fetch_ext_hours(symbol):
    """Latest pre-market or after-hours trade, with % change vs the right baseline."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=5m&range=1d&includePrePost=true"
    result = json.loads(http_get(url))["chart"]["result"][0]
    meta = result["meta"]
    regular = meta.get("currentTradingPeriod", {}).get("regular", {})
    pairs = [(t, c) for t, c in zip(result.get("timestamp", []),
                                    result["indicators"]["quote"][0]["close"]) if c is not None]
    if not pairs or not regular:
        return None
    ts, close = pairs[-1]
    if ts < regular.get("start", 0):
        label, base = "pre-market", meta.get("chartPreviousClose")
    elif ts >= regular.get("end", float("inf")):
        label, base = "after-hours", meta.get("regularMarketPrice")
    else:
        return None  # regular session is trading; no extended-hours quote
    if not base:
        return None
    return {"label": label, "price": round(close, 2),
            "changePct": round((close - base) / base * 100, 2)}


def fetch_quote(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
    meta = json.loads(http_get(url))["chart"]["result"][0]["meta"]
    price = meta.get("regularMarketPrice")
    prev = meta.get("chartPreviousClose") or meta.get("previousClose")
    if not price or not prev:
        return None
    name, vertical, desc = UNIVERSE.get(symbol, (meta.get("shortName", symbol), "Other", ""))
    try:
        spark, avg_vol = fetch_spark(symbol)
    except Exception:
        spark, avg_vol = [], None
    try:
        ext = fetch_ext_hours(symbol)
    except Exception:
        ext = None
    vol = meta.get("regularMarketVolume")
    rel_vol = round(vol / (avg_vol * session_fraction()), 1) if vol and avg_vol else None
    return {
        "spark": spark,
        "ext": ext,
        "relVol": rel_vol,
        "avgVolume": int(avg_vol) if avg_vol else None,
        "symbol": symbol,
        "name": name,
        "vertical": vertical,
        "description": desc,
        "price": round(price, 2),
        "prevClose": round(prev, 2),
        "changePct": round((price - prev) / prev * 100, 2),
        "volume": meta.get("regularMarketVolume"),
        "dayHigh": meta.get("regularMarketDayHigh"),
        "dayLow": meta.get("regularMarketDayLow"),
        "fiftyTwoWeekHigh": meta.get("fiftyTwoWeekHigh"),
        "fiftyTwoWeekLow": meta.get("fiftyTwoWeekLow"),
        "marketTime": meta.get("regularMarketTime"),
    }


def fetch_news(query, limit=8):
    q = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    items = []
    try:
        root = ET.fromstring(http_get(url))
        for item in root.iter("item"):
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            pub = item.findtext("pubDate") or ""
            source = item.findtext("source") or ""
            items.append({"title": title, "link": link, "pubDate": pub, "source": source})
            if len(items) >= limit:
                break
    except Exception as e:
        print(f"  news fetch failed for '{query}': {e}")
    return items


def fetch_dod_awards(days=45, limit=12):
    """Top new DoD contract awards from USAspending (official record; reported with a lag)."""
    from datetime import timedelta, date
    end = date.today()
    start = end - timedelta(days=days)
    body = json.dumps({
        "filters": {
            "agencies": [{"type": "awarding", "tier": "toptier", "name": "Department of Defense"}],
            "time_period": [{"start_date": str(start), "end_date": str(end), "date_type": "new_awards_only"}],
            "award_type_codes": ["A", "B", "C", "D"],
        },
        "fields": ["Award ID", "Recipient Name", "Award Amount", "Description",
                   "Awarding Sub Agency", "Start Date"],
        "sort": "Award Amount", "order": "desc", "limit": limit,
    }).encode()
    req = urllib.request.Request(
        "https://api.usaspending.gov/api/v2/search/spending_by_award/",
        data=body, headers={**HEADERS, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            results = json.loads(r.read())["results"]
    except Exception as e:
        print(f"  usaspending failed: {e}")
        return []
    return [{
        "recipient": a.get("Recipient Name"),
        "amount": a.get("Award Amount"),
        "agency": a.get("Awarding Sub Agency"),
        "date": a.get("Start Date"),
        "description": (a.get("Description") or "").capitalize(),
        "awardId": a.get("Award ID"),
    } for a in results]


def main():
    print("Fetching quotes...")
    quotes = []
    for sym in UNIVERSE:
        try:
            q = fetch_quote(sym)
            if q:
                quotes.append(q)
        except Exception as e:
            print(f"  quote failed for {sym}: {e}")
        time.sleep(0.25)  # be polite to Yahoo

    quotes.sort(key=lambda q: abs(q["changePct"]), reverse=True)
    movers = [q for q in quotes if abs(q["changePct"]) >= MOVER_THRESHOLD]

    print(f"{len(quotes)} quotes, {len(movers)} movers beyond +/-{MOVER_THRESHOLD}%")

    existing = load_existing()
    news_light = "--news-light" in sys.argv
    quotes_only = "--quotes-only" in sys.argv and not news_light

    if quotes_only or news_light:
        old_news = {q["symbol"]: q.get("news", []) for q in existing.get("quotes", [])}
        for q in quotes:
            q["news"] = old_news.get(q["symbol"], [])
        geo = existing.get("geopolitical", [])
        mna = existing.get("mna", [])
        sector_news = existing.get("sectorNews", [])
        industrials = existing.get("industrialsNews", [])
        contract_news = existing.get("contractNews", [])
        sda_news = existing.get("sdaNews", [])
        ipo_news = existing.get("ipoNews", [])
        dod_awards = existing.get("dodAwards", [])
        if news_light:
            # Refresh the fast-moving feeds + headlines for current movers only
            print("News-light mode: refreshing mover headlines and fast topic feeds")
            for m in movers:
                m["news"] = fetch_news(f'"{m["name"]}" stock', limit=5) or m["news"]
                time.sleep(0.3)
            geo = fetch_news("geopolitical conflict military when:1d", limit=12) or geo
            sector_news = fetch_news("aerospace defense industry when:1d", limit=10) or sector_news
            contract_news = fetch_news('Pentagon OR DoD OR Army OR Navy OR "Air Force" defense contract awarded when:3d', limit=12) or contract_news
        else:
            print("Quotes-only mode: carrying news/awards over from previous run")
    else:
        print("Fetching company news...")
        for q in quotes:
            limit = 5 if abs(q["changePct"]) >= MOVER_THRESHOLD else 4
            q["news"] = fetch_news(f'"{q["name"]}" stock', limit=limit)
            time.sleep(0.3)

        print("Fetching topic news...")
        geo = fetch_news("geopolitical conflict military when:1d", limit=12)
        mna = fetch_news('aerospace defense "acquisition" OR "merger" OR "acquire" when:7d', limit=10)
        sector_news = fetch_news("aerospace defense industry when:1d", limit=10)
        industrials = fetch_news("industrials sector manufacturing when:1d", limit=8)
        contract_news = fetch_news('Pentagon OR DoD OR Army OR Navy OR "Air Force" defense contract awarded when:3d', limit=12)
        sda_news = fetch_news('"Space Development Agency" when:30d', limit=8)
        ipo_news = fetch_news('defense OR aerospace company IPO when:14d', limit=10)

        print("Fetching DoD awards from USAspending...")
        dod_awards = fetch_dod_awards()
    analysis = existing.get("analysis", {"summary": "", "moverNotes": {}, "geoBriefing": "", "ipoWatch": []})

    # Rolling 7-day history: one entry per ET calendar day, latest data wins.
    from zoneinfo import ZoneInfo
    et_today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    advancers = sum(1 for q in quotes if q["changePct"] > 0)
    today_entry = {
        "date": et_today,
        "advancers": advancers,
        "decliners": len(quotes) - advancers,
        "avgChangePct": round(sum(q["changePct"] for q in quotes) / max(len(quotes), 1), 2),
        "topMovers": [{"symbol": q["symbol"], "changePct": q["changePct"]} for q in quotes[:5]],
        "summary": analysis.get("summary", ""),
    }
    history = [h for h in existing.get("history", []) if h.get("date") != et_today]
    history.append(today_entry)
    history = sorted(history, key=lambda h: h["date"])[-7:]

    data = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "threshold": MOVER_THRESHOLD,
        "verticalOrder": VERTICAL_ORDER,
        "history": history,
        "quotes": quotes,
        "movers": movers,
        "geopolitical": geo,
        "mna": mna,
        "sectorNews": sector_news,
        "industrialsNews": industrials,
        "contractNews": contract_news,
        "sdaNews": sda_news,
        "ipoNews": ipo_news,
        "dodAwards": dod_awards,
        # The hourly Claude task overwrites this with a written briefing.
        "analysis": analysis,
    }

    OUT.write_text("window.DASHBOARD_DATA = " + json.dumps(data, indent=1) + ";\n")
    print(f"Wrote {OUT}")


def load_existing():
    try:
        return json.loads(OUT.read_text().split("=", 1)[1].rstrip().rstrip(";"))
    except Exception:
        return {}


if __name__ == "__main__":
    main()
