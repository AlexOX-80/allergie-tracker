# Allergie-Tagebuch App mit Streamlit
# Beschreibung: Diese App zieht Wetter- und Pollen­daten von Meteostat, DWD und Pollenstiftung
# und erlaubt das Erfassen eigener Symptome.

import streamlit as st
import pandas as pd
from datetime import date
from datetime import datetime
import requests
import os
from meteostat import Daily, Stations

# -- Konfiguration --
# DWD Open Data (Wetter) - optional, bisher nutzen wir Meteostat für Wetter
# Pollenstiftung (Web-API/Datenquelle)
# (URL und Parameter je nach Verfügbarkeit anpassen)
POLLENSTIFTUNG_API_URL = "https://www.pollenstiftung.de/services/forecast"
# DWD Pollen-CSV-Verzeichnis (Beispielpfad)
DWD_POLLEN_BASE_URL   = "https://opendata.dwd.de/climate_environment/health/pollen_stations"

# -- Funktionen --


def get_weather(dt, lat, lon):
    # Sicherstellen, dass dt ein datetime.date ist
    if isinstance(dt, str):
        dt = datetime.strptime(dt, "%Y-%m-%d").date()
    elif isinstance(dt, pd.Timestamp):
        dt = dt.date()

    station = Stations().nearby(lat, lon).fetch(1)
    if station.empty:
        return None

    station = station.index[0]
    data = Daily(station, dt, dt).fetch()
    return data



def get_pollenstiftung(lat, lon):
    """Holt Pollenflug-Vorhersage von Pollenstiftung.de"""
    try:
        params = {'lat': lat, 'lng': lon}
        resp = requests.get(POLLENSTIFTUNG_API_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        # Beispielannahme: data enthält keys 'birke','gräser','ambrosia'
        return {
            'birke':    data.get('birke', {}).get('index'),
            'gräser':   data.get('gräser', {}).get('index'),
            'ambrosia': data.get('ambrosia', {}).get('index')
        }
    except Exception:
        return {'birke': None, 'gräser': None, 'ambrosia': None}


def get_dwd_pollen(lat, lon, dt):
    """Lädt DWD-Pollen-Daten aus CSV herunter und filtert nach Datum und Station."""
    # Hinweis: Passe station_id entsprechend deiner Region an oder implementiere nearest-station-Logik
    station_id = '001'  # Beispiel-Station
    url = f"{DWD_POLLEN_BASE_URL}/{station_id}.csv"
    try:
        df = pd.read_csv(url, parse_dates=['date'], dayfirst=True)
        row = df[df['date'] == pd.to_datetime(dt)].iloc[0]
        return {
            'birke':    row.get('Birke'),
            'gräser':   row.get('Gräser'),
            'ambrosia': row.get('Ambrosia')
        }
    except Exception:
        return {'birke': None, 'gräser': None, 'ambrosia': None}

# -- Streamlit UI --
st.title("🌿 Allergie-Tagebuch")
st.markdown("Diese App ruft Wetter- und Pollen­daten (Meteostat, Pollenstiftung, DWD) ab und speichert deine Symptome.")

# Sidebar: Standort
dt = st.date_input("Datum", value=date.today())
lat = st.sidebar.number_input("Breitengrad", value=51.16, format="%.6f")
lon = st.sidebar.number_input("Längengrad", value=10.45, format="%.6f")
source = st.sidebar.selectbox("Pollen-Datenquelle", ["Pollenstiftung.de", "DWD Open Data"])

if st.button("Daten abrufen & Symptome erfassen"):
    # Wetterdaten
    weather = get_weather(dt, lat, lon)
    st.subheader("🌦️ Wetterdaten (Meteostat)")
    st.write(f"Temperatur (°C): {weather['tavg']}")
    st.write(f"Luftfeuchte (%): {weather['rhum']}")
    st.write(f"Niederschlag (mm): {weather['prcp']}")

    # Pollendaten
    if source == "Pollenstiftung.de":
        pollen = get_pollenstiftung(lat, lon)
        st.subheader("🌸 Pollendaten (Pollenstiftung.de)")
    else:
        pollen = get_dwd_pollen(lat, lon, dt)
        st.subheader("🌸 Pollendaten (DWD Open Data)")

    st.write(f"Birke: {pollen['birke']}")
    st.write(f"Gräser: {pollen['gräser']}")
    st.write(f"Ambrosia: {pollen['ambrosia']}")

    # Symptome erfassen
    st.subheader("📝 Symptome eingeben")
    fatigue   = st.slider("Müdigkeit", 0, 10, 5)
    runnynose = st.slider("Nase laufen", 0, 10, 0)
    sorethroat= st.slider("Halsweh", 0, 10, 0)
    notes     = st.text_area("Anmerkungen", height=80)

    # Speichern
    if st.button("Eintrag speichern"):
        entry = {
            'Datum': dt,
            'lat': lat, 'lon': lon,
            'tavg': weather['tavg'], 'rhum': weather['rhum'], 'prcp': weather['prcp'],
            'birke': pollen['birke'], 'gräser': pollen['gräser'], 'ambrosia': pollen['ambrosia'],
            'muedigkeit': fatigue, 'nase_laufen': runnynose, 'halsweh': sorethroat,
            'anmerkungen': notes
        }
        df = pd.DataFrame([entry])
        file = "allergie_tagebuch.csv"
        if os.path.exists(file):
            df.to_csv(file, mode='a', header=False, index=False)
        else:
            df.to_csv(file, index=False)
        st.success("✅ Eintrag gespeichert in `allergie_tagebuch.csv`")
        st.write(df)
