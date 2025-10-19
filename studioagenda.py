from datetime import datetime, timedelta
from astral import LocationInfo
from astral.sun import sun
import calendar
import tkinter as tk
from tkinter import messagebox
from tkcalendar import DateEntry
from zoneinfo import ZoneInfo
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import mplcursors
import os
import webbrowser

# Location: Breda
location = LocationInfo("Breda", "Netherlands", "Europe/Amsterdam", 51.5833, 4.7667)
tz = ZoneInfo("Europe/Amsterdam")

def round_to_nearest_half_hour(dt):
    minute = dt.minute
    if minute < 15:
        return dt.replace(minute=0, second=0, microsecond=0)
    elif minute < 45:
        return dt.replace(minute=30, second=0, microsecond=0)
    else:
        dt += timedelta(hours=1)
        return dt.replace(minute=0, second=0, microsecond=0)

def calculate_daylight(start_date, end_date, earliest_open, latest_close):
    days = []
    current_date = start_date
    while current_date <= end_date:
        s = sun(location.observer, date=current_date, tzinfo=tz)
        raw_sunrise = s["sunrise"]
        raw_sunset = s["sunset"]

        sunrise = raw_sunrise + timedelta(minutes=30)
        sunset = raw_sunset - timedelta(minutes=30)

        earliest_dt = datetime.combine(current_date, earliest_open, tzinfo=tz)
        latest_dt = datetime.combine(current_date, latest_close, tzinfo=tz)

        opening_time = round_to_nearest_half_hour(max(sunrise, earliest_dt))
        closing_time = round_to_nearest_half_hour(min(sunset, latest_dt))
        duration = max(0, (closing_time - opening_time).total_seconds() / 3600)

        days.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "day": calendar.day_name[current_date.weekday()],
            "open": opening_time.strftime("%H:%M"),
            "close": closing_time.strftime("%H:%M"),
            "hours": round(duration, 2)
        })

        current_date += timedelta(days=1)
    return days

def generate_ics_file(day_data):
    print("📅 generate_ics_file() called")
    ics_path = "studio_daylight.ics"
    header = "BEGIN:VCALENDAR\nVERSION:2.0\nCALSCALE:GREGORIAN\nMETHOD:PUBLISH\n"
    events = []

    for day in day_data:
        open_dt = datetime.strptime(f"{day['date']} {day['open']}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
        close_dt = datetime.strptime(f"{day['date']} {day['close']}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)

        event1 = f"""BEGIN:VEVENT
SUMMARY:Daylight Block - {day['day']}
DTSTART;TZID=Europe/Amsterdam:{open_dt.strftime('%Y%m%dT000000')}
DTEND;TZID=Europe/Amsterdam:{open_dt.strftime('%Y%m%dT%H%M%S')}
DESCRIPTION:Closed before opening
END:VEVENT
"""

        end_of_day = close_dt.replace(hour=23, minute=59)
        event2 = f"""BEGIN:VEVENT
SUMMARY:Daylight Block - {day['day']}
DTSTART;TZID=Europe/Amsterdam:{close_dt.strftime('%Y%m%dT%H%M%S')}
DTEND;TZID=Europe/Amsterdam:{end_of_day.strftime('%Y%m%dT%H%M%S')}
DESCRIPTION:Closed after closing
END:VEVENT
"""

        events.extend([event1, event2])

    with open(ics_path, "w") as f:
        f.write(header)
        f.writelines(events)
        f.write("END:VCALENDAR\n")
    print(f"✅ File written: {ics_path}")
    messagebox.showinfo("Success", f".ics file saved: {ics_path}")

def export_txt(day_data):
    path = "studio_daylight_export.txt"
    with open(path, "w") as f:
        for d in day_data:
            f.write(f"{d['date']} | Open: {d['open']} | Close: {d['close']}\n")
    webbrowser.open(f"file://{os.path.abspath(path)}")

# GUI setup
root = tk.Tk()
root.title("Studio Daylight Calendar")
root.geometry("1000x600")

# Inputs
tk.Label(root, text="Start Date:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
start_entry = DateEntry(root, date_pattern='yyyy-mm-dd')
start_entry.grid(row=0, column=1, padx=5)

tk.Label(root, text="End Date:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
end_entry = DateEntry(root, date_pattern='yyyy-mm-dd')
end_entry.grid(row=1, column=1, padx=5)

tk.Label(root, text="Earliest Open (HH:MM):").grid(row=2, column=0, sticky="e", padx=5, pady=5)
earliest_entry = tk.Entry(root)
earliest_entry.insert(0, "09:00")
earliest_entry.grid(row=2, column=1, padx=5)

tk.Label(root, text="Latest Close (HH:MM):").grid(row=3, column=0, sticky="e", padx=5, pady=5)
latest_entry = tk.Entry(root)
latest_entry.insert(0, "21:00")
latest_entry.grid(row=3, column=1, padx=5)

# Chart area
chart_frame = tk.Frame(root)
chart_frame.grid(row=5, column=0, columnspan=4, padx=10, pady=10)
chart_canvas = None

def get_user_input():
    start = datetime.strptime(start_entry.get(), "%Y-%m-%d")
    end = datetime.strptime(end_entry.get(), "%Y-%m-%d")
    if start > end:
        raise ValueError("Start date must be before end date.")
    earliest = datetime.strptime(earliest_entry.get(), "%H:%M").time()
    latest = datetime.strptime(latest_entry.get(), "%H:%M").time()
    return start, end, earliest, latest

def on_preview():
    global chart_canvas
    try:
        for widget in chart_frame.winfo_children():
            widget.destroy()

        start, end, earliest, latest = get_user_input()
        data = calculate_daylight(start, end, earliest, latest)

        labels = [d["date"] for d in data]
        hours = [d["hours"] for d in data]
        max_day = max(data, key=lambda d: d["hours"])
        min_day = min(data, key=lambda d: d["hours"])

        fig, ax = plt.subplots(figsize=(10, 4))
        bars = ax.bar(range(len(hours)), hours, color='skyblue')

        for i, bar in enumerate(bars):
            if data[i]["date"] == max_day["date"]:
                bar.set_color("green")
            elif data[i]["date"] == min_day["date"]:
                bar.set_color("red")

        ax.set_ylabel("Open hours")
        ax.set_title("Studio Opening Hours Per Day")
        ax.set_xticks([])
        fig.tight_layout()

        cursor = mplcursors.cursor(bars, hover=True)
        @cursor.connect("add")
        def on_add(sel):
            i = sel.index
            sel.annotation.set(text=f"{labels[i]}\n{hours[i]} hrs")

        chart_canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        chart_canvas.draw()
        chart_canvas.get_tk_widget().pack()

    except Exception as e:
        messagebox.showerror("Error", str(e))

def on_generate_ics():
    try:
        start, end, earliest, latest = get_user_input()
        data = calculate_daylight(start, end, earliest, latest)
        generate_ics_file(data)
    except Exception as e:
        messagebox.showerror("Error", str(e))

def on_export_txt():
    try:
        start, end, earliest, latest = get_user_input()
        data = calculate_daylight(start, end, earliest, latest)
        export_txt(data)
    except Exception as e:
        messagebox.showerror("Error", str(e))

# Buttons
tk.Button(root, text="📊 Generate Preview", command=on_preview).grid(row=4, column=0, padx=10, pady=10)
tk.Button(root, text="📅 Generate .ics", command=on_generate_ics).grid(row=4, column=1, padx=10, pady=10)
tk.Button(root, text="📄 Export as TXT", command=on_export_txt).grid(row=4, column=2, padx=10, pady=10)

root.mainloop()
