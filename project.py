import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime, date, timedelta

try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
except ImportError:
    mysql = None
    MySQLError = Exception

CLINIC_NAME = "RAMSY MEDICAL LABORATORIES"

# ---------------- DATABASE CONFIG ----------------
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "GROUP1",
    "password": "BSEM@1234",
    "database": "ramsey_medical_laboratories_record_system",
}

def get_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except MySQLError as e:
        messagebox.showerror("Database Error", f"Could not connect to database:\n{e}")
        return None

def run_query(query, params=None, fetch=False, commit=False):
    conn = get_connection()
    if conn is None:
        return [] if fetch else False
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        if commit:
            conn.commit()
        result = cursor.fetchall() if fetch else True
        cursor.close()
        return result
    except MySQLError as e:
        messagebox.showerror("Database Error", f"Query failed:\n{e}")
        return [] if fetch else False
    finally:
        conn.close()

def insert_and_get_id(query, params):
    conn = get_connection()
    if conn is None:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        new_id = cursor.lastrowid
        cursor.close()
        return new_id
    except MySQLError as e:
        messagebox.showerror("Database Error", f"Insert failed:\n{e}")
        return None
    finally:
        conn.close()

# ================================================================
#  SESSION  (tracks the currently logged-in user)
# ================================================================
SESSION = {
    "user_id":   None,
    "username":  None,
    "role":      None,
    "logged_in": False,
}

SESSION_TIMEOUT_MINUTES = 5   # auto-logout after this many idle minutes
_last_activity = datetime.now()

def reset_activity_timer(event=None):
    """Call this on any user interaction to reset the idle timer."""
    global _last_activity
    _last_activity = datetime.now()

def check_session_timeout():
    """Runs every 30 s; logs out if the user has been idle too long."""
    if SESSION["logged_in"]:
        idle = datetime.now() - _last_activity
        if idle > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
            messagebox.showwarning(
                "Session Expired",
                f"You have been logged out after {SESSION_TIMEOUT_MINUTES} minutes of inactivity."
            )
            logout()
            return
    # reschedule
    if window:
        window.after(30_000, check_session_timeout)

# ================================================================
#  AUDIT LOG
# ================================================================
def log_action(action, details=""):
    """Insert a row into the audit_log table (silent on failure)."""
    if not SESSION["logged_in"]:
        return
    run_query(
        """INSERT INTO audit_log (User_ID, Username, Role, Action, Details, Timestamp)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (SESSION["user_id"], SESSION["username"], SESSION["role"],
         action, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        commit=True
    )

def get_audit_logs():
    return run_query(
        "SELECT * FROM audit_log ORDER BY Timestamp DESC LIMIT 200",
        fetch=True
    ) or []

# ================================================================
#  USERS  (login / management)
# ================================================================
def verify_login(username, password, role):
    rows = run_query(
        "SELECT * FROM users WHERE Username=%s AND Password=%s AND Role=%s",
        (username, password, role), fetch=True
    )
    return rows[0] if rows else None

def get_all_users():
    return run_query("SELECT User_ID, Username, Role FROM users ORDER BY Username", fetch=True) or []

def create_user_db(username, password, role):
    ok = run_query(
        "INSERT INTO users (Username, Password, Role) VALUES (%s, %s, %s)",
        (username, password, role), commit=True
    )
    if ok:
        log_action("CREATE USER", f"Created user '{username}' with role '{role}'")
    return ok

def delete_user_db(user_id):
    ok = run_query("DELETE FROM users WHERE User_ID=%s", (user_id,), commit=True)
    if ok:
        log_action("DELETE USER", f"Deleted User_ID={user_id}")
    return ok

# ================================================================
#  TRIAGE LOGIC  (in-memory)
# ================================================================
DIAGNOSIS_RULES = [
    {"diagnosis_name": "Hypertension",      "keyword": "blood pressure", "specialty": "Internal Medicine"},
    {"diagnosis_name": "Angina",            "keyword": "chest pain",     "specialty": "Cardiology"},
    {"diagnosis_name": "Influenza",         "keyword": "flu",            "specialty": "General Medicine"},
    {"diagnosis_name": "Dermatitis",        "keyword": "rash",           "specialty": "Dermatology"},
    {"diagnosis_name": "Lower Back Strain", "keyword": "back pain",      "specialty": "Orthopedics"},
    {"diagnosis_name": "Migraine",          "keyword": "headache",       "specialty": "Neurology"},
    {"diagnosis_name": "Type 2 Diabetes",   "keyword": "diabetes",       "specialty": "Endocrinology"},
    {"diagnosis_name": "Common Cold",       "keyword": "cold",           "specialty": "General Medicine"},
    {"diagnosis_name": "Arthritis",         "keyword": "joint pain",     "specialty": "Rheumatology"},
    {"diagnosis_name": "Allergic Reaction", "keyword": "allergy",        "specialty": "Emergency Medicine"},
]

def determine_priority(age, symptoms):
    symptoms = symptoms.lower()
    for kw in ["chest pain", "bleeding", "unconscious", "difficulty breathing", "severe pain"]:
        if kw in symptoms:
            return "Emergency"
    if age < 5 or age >= 65:
        return "High Priority"
    return "Normal"

def match_diagnosis(symptoms):
    symptoms = symptoms.lower()
    for rule in DIAGNOSIS_RULES:
        if rule["keyword"] in symptoms:
            return rule["diagnosis_name"]
    return None

def assign_specialty(diagnosis_name):
    for rule in DIAGNOSIS_RULES:
        if rule["diagnosis_name"] == diagnosis_name:
            return rule["specialty"]
    return "General Medicine"

def calculate_age(dob):
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

# ================================================================
#  HEALTH WORKERS  (real DB)
# ================================================================
HEALTH_WORKERS = []
SPEC_COLUMN    = None

def detect_specialization_column():
    global SPEC_COLUMN
    cols  = run_query("SHOW COLUMNS FROM Health_Workers", fetch=True)
    names = [c["Field"] for c in cols] if cols else []
    for candidate in ["Specailization", "Specialization", "specailization", "specialization"]:
        if candidate in names:
            SPEC_COLUMN = candidate
            return
    SPEC_COLUMN = None

def load_health_workers():
    global HEALTH_WORKERS
    if SPEC_COLUMN is None:
        detect_specialization_column()
    spec_select = f"`{SPEC_COLUMN}` AS specialization" if SPEC_COLUMN else "NULL AS specialization"
    rows = run_query(
        f"SELECT Health_Worker_ID, Full_Name, {spec_select}, Role FROM Health_Workers",
        fetch=True
    )
    HEALTH_WORKERS = rows or []

def find_best_worker(specialty):
    if not HEALTH_WORKERS:
        return None
    candidates = [w for w in HEALTH_WORKERS
                  if w["specialization"] and w["specialization"].strip().lower() == specialty.strip().lower()]
    if not candidates:
        candidates = [w for w in HEALTH_WORKERS
                      if w["specialization"] and "general" in w["specialization"].lower()]
    if not candidates:
        candidates = list(HEALTH_WORKERS)
    today_str = date.today().strftime("%Y-%m-%d")
    counts    = run_query(
        "SELECT Health_Worker_ID, COUNT(*) AS cnt FROM appointment WHERE DATE(Appointment_Date)=%s GROUP BY Health_Worker_ID",
        (today_str,), fetch=True
    )
    count_map = {c["Health_Worker_ID"]: c["cnt"] for c in counts}
    candidates.sort(key=lambda w: count_map.get(w["Health_Worker_ID"], 0))
    return candidates[0]

# ================================================================
#  PATIENT  (real DB)
# ================================================================
def register_patient_db(full_name, dob, gender, phone, address, emergency_contact):
    pid = insert_and_get_id(
        """INSERT INTO PATIENT (Full_Name, Date_of_Birth, Gender, Phone_number, Address, Emergency_Contact, Date_Registered)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (full_name, dob.strftime("%Y-%m-%d"), gender, phone, address, emergency_contact,
         date.today().strftime("%Y-%m-%d"))
    )
    if pid:
        log_action("REGISTER PATIENT", f"Registered '{full_name}' (Patient ID {pid})")
    return pid

def search_patients_db(query_text):
    sql    = "SELECT Patient_ID, Full_Name, Gender, Date_of_Birth FROM PATIENT"
    params = []
    if query_text:
        sql += " WHERE Full_Name LIKE %s"
        params.append(f"%{query_text}%")
    sql += " ORDER BY Full_Name ASC LIMIT 25"
    return run_query(sql, params, fetch=True)

# ================================================================
#  PATIENT HISTORY  (uses vw_patient_records view)
# ================================================================
def get_patient_history(name_query):
    """Return all rows from the view matching the patient's name."""
    if not name_query.strip():
        return []
    return run_query(
        "SELECT * FROM vw_patient_records WHERE Full_Name LIKE %s ORDER BY Visit_Date DESC",
        (f"%{name_query}%",), fetch=True
    ) or []

# ================================================================
#  WAITING QUEUE  (in-memory)
# ================================================================
waiting_queue = []
queue_number  = 1

def sort_queue():
    priority_order = {"Emergency": 1, "High Priority": 2, "Normal": 3}
    waiting_queue.sort(key=lambda p: (priority_order[p["priority"]], p["queue_number"]))

def add_patient_to_queue(full_name, dob_text, gender, phone, address, emergency_contact, symptoms, win=None):
    global queue_number
    reset_activity_timer()
    if not full_name or not dob_text or not gender or not symptoms:
        messagebox.showerror("Input Error", "Name, Date of Birth, Gender, and Symptoms are required.")
        return
    try:
        dob = datetime.strptime(dob_text, "%Y-%m-%d").date()
    except ValueError:
        messagebox.showerror("Input Error", "Date of Birth must be in YYYY-MM-DD format.")
        return
    if dob > date.today():
        messagebox.showerror("Input Error", "Date of Birth cannot be in the future.")
        return

    age            = calculate_age(dob)
    priority       = determine_priority(age, symptoms)
    diagnosis_name = match_diagnosis(symptoms)
    specialty      = assign_specialty(diagnosis_name) if diagnosis_name else "General Medicine"

    patient_id = register_patient_db(full_name, dob, gender, phone, address, emergency_contact)
    if patient_id is None:
        return

    assigned_worker = find_best_worker(specialty)
    if assigned_worker:
        add_appointment_db(patient_id, assigned_worker["Health_Worker_ID"], datetime.now())

    entry = {
        "queue_number": queue_number,
        "patient_id":   patient_id,
        "name":         full_name,
        "age":          age,
        "gender":       gender,
        "symptoms":     symptoms,
        "priority":     priority,
        "diagnosis":    diagnosis_name or "Unknown",
        "specialty":    specialty,
        "worker_id":    assigned_worker["Health_Worker_ID"] if assigned_worker else None,
        "worker_name":  assigned_worker["Full_Name"]        if assigned_worker else "Unassigned",
    }
    waiting_queue.append(entry)
    queue_number += 1
    sort_queue()

    worker_line = (f"\nAssigned to: {entry['worker_name']}"
                   if assigned_worker else "\nNo matching health worker found — please assign manually.")
    messagebox.showinfo(
        "Success",
        f"{full_name} registered (Patient ID #{patient_id}).\n"
        f"Diagnosis: {entry['diagnosis']}\nSpecialty: {specialty}{worker_line}"
    )
    if win:
        win.destroy()
    refresh_dashboard()

def get_waiting(query_text=""):
    if not query_text:
        return list(waiting_queue)
    q = query_text.lower()
    return [p for p in waiting_queue
            if q in p["name"].lower() or q in p["priority"].lower()
            or q in p["diagnosis"].lower() or q in p["specialty"].lower()]

def serve_patient():
    reset_activity_timer()
    if not waiting_queue:
        messagebox.showinfo("Queue Empty", "There are no patients to serve.")
        return
    sort_queue()
    served = waiting_queue.pop(0)
    log_action("SERVE PATIENT", f"Served '{served['name']}' (Patient ID {served['patient_id']})")
    messagebox.showinfo("Patient Served", f"Now serving {served['name']} ({served['priority']})")
    refresh_dashboard()

def clear_queue():
    reset_activity_timer()
    confirm = messagebox.askyesno(
        "Confirm",
        "Are you sure you want to clear the waiting queue?\n"
        "(Patient records stay in the database — this only clears today's queue.)"
    )
    if confirm:
        waiting_queue.clear()
        log_action("CLEAR QUEUE", "Waiting queue cleared")
        messagebox.showinfo("Cleared", "Waiting queue has been cleared.")
        refresh_dashboard()

def export_queue():
    reset_activity_timer()
    if not waiting_queue:
        messagebox.showinfo("Export", "Queue is empty, nothing to export.")
        return
    with open("patient_queue.txt", "w") as f:
        for p in waiting_queue:
            f.write(
                f"#{p['queue_number']} (Patient ID {p['patient_id']}) | {p['name']} | {p['age']} | "
                f"{p['gender']} | {p['priority']} | {p['diagnosis']} | {p['specialty']}\n"
            )
    log_action("EXPORT QUEUE", "Queue exported to patient_queue.txt")
    messagebox.showinfo("Export", "Queue exported to patient_queue.txt")

def get_stats():
    total     = len(waiting_queue)
    emergency = sum(1 for p in waiting_queue if p["priority"] == "Emergency")
    high      = sum(1 for p in waiting_queue if p["priority"] == "High Priority")
    normal    = sum(1 for p in waiting_queue if p["priority"] == "Normal")
    return total, emergency, high, normal

# ================================================================
#  APPOINTMENTS  (real DB)
# ================================================================
REMINDER_WINDOW_MINUTES  = 30
notified_appointment_ids = set()

def get_appointments(query_text=""):
    spec_select = f"h.`{SPEC_COLUMN}` AS Worker_Specialty" if SPEC_COLUMN else "NULL AS Worker_Specialty"
    sql = (
        f"SELECT a.Appointment_ID, a.Appointment_Date, a.Patient_ID, a.Health_Worker_ID, p.Full_Name,"
        f"       h.Full_Name AS Worker_Name, {spec_select}"
        f" FROM appointment a"
        f" JOIN PATIENT p ON a.Patient_ID = p.Patient_ID"
        f" LEFT JOIN Health_Workers h ON a.Health_Worker_ID = h.Health_Worker_ID"
    )
    params = []
    if query_text:
        sql   += " WHERE p.Full_Name LIKE %s OR h.Full_Name LIKE %s"
        like   = f"%{query_text}%"
        params = [like, like]
    sql += " ORDER BY a.Appointment_Date ASC"
    return run_query(sql, params, fetch=True)

def add_appointment_db(patient_id, health_worker_id, appt_datetime):
    ok = run_query(
        "INSERT INTO appointment (Appointment_Date, Patient_ID, Health_Worker_ID) VALUES (%s, %s, %s)",
        (appt_datetime.strftime("%Y-%m-%d %H:%M:%S"), patient_id, health_worker_id),
        commit=True
    )
    if ok:
        log_action("BOOK APPOINTMENT", f"Patient ID {patient_id} → Worker ID {health_worker_id}")
    return ok

def check_appointment_notifications():
    due = run_query(
        """SELECT a.Appointment_ID, a.Appointment_Date, p.Full_Name
           FROM appointment a JOIN PATIENT p ON a.Patient_ID = p.Patient_ID
           WHERE a.Appointment_Date <= NOW()""",
        fetch=True
    ) or []

    new_due = [a for a in due if a["Appointment_ID"] not in notified_appointment_ids]
    for a in new_due:
        notified_appointment_ids.add(a["Appointment_ID"])

    if new_due:
        if len(new_due) == 1:
            a = new_due[0]
            messagebox.showinfo(
                "Appointment Reminder",
                f"It's time for {a['Full_Name']}'s appointment ({a['Appointment_Date']})"
            )
        else:
            lines = "\n".join(f"• {a['Full_Name']} — {a['Appointment_Date']}" for a in new_due)
            messagebox.showinfo("Appointment Reminders",
                                f"{len(new_due)} appointments are now due:\n\n{lines}")

    refresh_notification_banner()
    window.after(30_000, check_appointment_notifications)

# ================================================================
#  THEME
# ================================================================
BG_DARK       = "#1e1b4b"
BG_DARK_HOVER = "#312e81"
BG_MAIN       = "#eef0fa"
ACCENT        = "#4f46e5"
TXT_LIGHT     = "#e0e7ff"
CARD_WHITE    = "#ffffff"
TEXT_DARK     = "#1f2330"
TEXT_MUTED    = "#6b7280"
BORDER        = "#e2e4f3"
TINT_TOTAL    = ("#eef2ff", "#4338ca")
TINT_EMERGENCY= ("#fef2f2", "#dc2626")
TINT_HIGH     = ("#fffbeb", "#d97706")
TINT_NORMAL   = ("#f0fdf4", "#16a34a")
SUCCESS_GREEN = "#16a34a"
DANGER_RED    = "#dc2626"

# ================================================================
#  REUSABLE POPUP HELPER
# ================================================================
def styled_popup(title, size):
    win = tk.Toplevel(window)
    win.title(title)
    win.geometry(size)
    win.configure(bg=BG_MAIN)
    win.bind_all("<Motion>",  reset_activity_timer)
    win.bind_all("<KeyPress>", reset_activity_timer)

    header = tk.Frame(win, bg=ACCENT, height=50)
    header.pack(fill="x")
    tk.Label(header, text=title, bg=ACCENT, fg="white", font=("Arial", 13, "bold")).pack(pady=12)

    footer = tk.Frame(win, bg=BG_MAIN)
    footer.pack(side="bottom", fill="x", padx=20, pady=15)

    container = tk.Frame(win, bg=BG_MAIN)
    container.pack(side="top", fill="both", expand=True)

    canvas    = tk.Canvas(container, bg=BG_MAIN, highlightthickness=0)
    scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    content   = tk.Frame(canvas, bg=BG_MAIN)
    window_id = canvas.create_window((0, 0), window=content, anchor="nw")

    content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>",  lambda e: canvas.itemconfig(window_id, width=e.width))

    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", on_mousewheel))
    canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

    inner = tk.Frame(content, bg=BG_MAIN)
    inner.pack(fill="both", expand=True, padx=20, pady=15)

    return win, inner, footer

def form_row(parent, row, label_text, show=None):
    tk.Label(parent, text=label_text, bg=BG_MAIN, fg=TEXT_DARK, font=("Arial", 10, "bold")) \
        .grid(row=row, column=0, sticky="w", pady=8, padx=(0, 10))
    kw    = {"show": show} if show else {}
    entry = tk.Entry(parent, font=("Arial", 10), relief="flat",
                     highlightbackground=BORDER, highlightthickness=1, bg="white", **kw)
    entry.grid(row=row, column=1, sticky="ew", pady=8, ipady=4)
    parent.columnconfigure(1, weight=1)
    return entry

# ================================================================
#  LOGIN WINDOW
# ================================================================
def show_login_window():
    """Display the login screen; blocks until a successful login."""
    login_win = tk.Tk()
    login_win.title(f"{CLINIC_NAME} — Login")
    login_win.resizable(False, False)
    login_win.configure(bg=BG_DARK)

    # ---- Center on screen ----
    win_w, win_h = 580, 680
    login_win.update_idletasks()
    sw = login_win.winfo_screenwidth()
    sh = login_win.winfo_screenheight()
    x  = (sw - win_w) // 2
    y  = (sh - win_h) // 2
    login_win.geometry(f"{win_w}x{win_h}+{x}+{y}")

    # ---- Header ----
    hdr = tk.Frame(login_win, bg=BG_DARK)
    hdr.pack(pady=(52, 14))
    tk.Label(hdr, text="🏥", font=("Arial", 52), bg=BG_DARK, fg=TXT_LIGHT).pack()
    tk.Label(hdr, text=CLINIC_NAME, font=("Arial", 16, "bold"),
             bg=BG_DARK, fg=TXT_LIGHT, wraplength=480, justify="center").pack(pady=(10, 4))
    tk.Label(hdr, text="Staff Portal — Please sign in to continue",
             font=("Arial", 11), bg=BG_DARK, fg="#a5b4fc").pack()

    # ---- Card ----
    card = tk.Frame(login_win, bg=CARD_WHITE, padx=44, pady=36)
    card.pack(padx=52, pady=24, fill="x")

    def lbl(text):
        tk.Label(card, text=text, bg=CARD_WHITE, fg=TEXT_DARK,
                 font=("Arial", 11, "bold"), anchor="w").pack(fill="x", pady=(12, 3))

    lbl("Username")
    user_entry = tk.Entry(card, font=("Arial", 13), relief="flat",
                          highlightbackground=BORDER, highlightthickness=1,
                          bg=BG_MAIN)
    user_entry.pack(fill="x", ipady=8)

    lbl("Password")
    pass_entry = tk.Entry(card, font=("Arial", 13), relief="flat", show="•",
                          highlightbackground=BORDER, highlightthickness=1,
                          bg=BG_MAIN)
    pass_entry.pack(fill="x", ipady=8)

    lbl("Role")
    role_var = tk.StringVar(value="Receptionist")
    role_cb  = ttk.Combobox(card, textvariable=role_var,
                             values=["Admin", "Doctor", "Receptionist"],
                             state="readonly", font=("Arial", 13))
    role_cb.pack(fill="x", ipady=6)

    err_lbl = tk.Label(card, text="", bg=CARD_WHITE, fg=DANGER_RED,
                       font=("Arial", 10))
    err_lbl.pack(pady=(8, 0))

    def attempt_login(event=None):
        username = user_entry.get().strip()
        password = pass_entry.get()
        role     = role_var.get()
        if not username or not password:
            err_lbl.config(text="⚠  Please enter your username and password.")
            return
        user = verify_login(username, password, role)
        if user:
            SESSION["user_id"]   = user["User_ID"]
            SESSION["username"]  = user["Username"]
            SESSION["role"]      = user["Role"]
            SESSION["logged_in"] = True
            log_action("LOGIN", f"User '{username}' logged in as {role}")
            login_win.destroy()
        else:
            err_lbl.config(text="⚠  Invalid username, password, or role.")
            pass_entry.delete(0, "end")

    tk.Button(card, text="Sign In", bg=ACCENT, fg="white",
              font=("Arial", 13, "bold"), relief="flat",
              pady=12, cursor="hand2",
              command=attempt_login).pack(fill="x", pady=(18, 0))

    # ---- Footer note ----
    tk.Label(login_win, text="© RAMSY MEDICAL LABORATORIES — Authorized Staff Only",
             bg=BG_DARK, fg="#4f46a0", font=("Arial", 8)).pack(side="bottom", pady=12)

    login_win.bind("<Return>", attempt_login)
    user_entry.focus_set()
    login_win.mainloop()

# ================================================================
#  PATIENT HISTORY POPUP
# ================================================================
def open_patient_history_window():
    reset_activity_timer()
    win, body, footer = styled_popup("Patient History", "700x560")

    # ---- Search bar ----
    search_frame = tk.Frame(body, bg=BG_MAIN)
    search_frame.pack(fill="x", pady=(0, 12))
    tk.Label(search_frame, text="Search Patient Name:", bg=BG_MAIN, fg=TEXT_DARK,
             font=("Arial", 10, "bold")).pack(side="left", padx=(0, 8))
    search_var = tk.StringVar()
    search_entry = tk.Entry(search_frame, textvariable=search_var, font=("Arial", 11),
                            relief="flat", highlightbackground=BORDER, highlightthickness=1,
                            bg="white", width=28)
    search_entry.pack(side="left", ipady=4)
    search_entry.focus_set()

    # ---- Results area (scrollable text) ----
    result_frame = tk.Frame(body, bg=CARD_WHITE, relief="flat",
                            highlightbackground=BORDER, highlightthickness=1)
    result_frame.pack(fill="both", expand=True)

    text_scroll = tk.Scrollbar(result_frame)
    text_scroll.pack(side="right", fill="y")

    result_text = tk.Text(result_frame, font=("Courier", 9), bg=CARD_WHITE, fg=TEXT_DARK,
                          relief="flat", yscrollcommand=text_scroll.set,
                          wrap="word", state="disabled", padx=12, pady=10)
    result_text.pack(fill="both", expand=True)
    text_scroll.config(command=result_text.yview)

    # ---- Tag styles ----
    result_text.tag_config("header",    font=("Arial", 11, "bold"), foreground=ACCENT)
    result_text.tag_config("subheader", font=("Arial", 9,  "bold"), foreground=TEXT_DARK)
    result_text.tag_config("value",     font=("Courier", 9),        foreground="#374151")
    result_text.tag_config("divider",   foreground=BORDER)
    result_text.tag_config("muted",     foreground=TEXT_MUTED,      font=("Arial", 9, "italic"))
    result_text.tag_config("pill_em",   foreground=DANGER_RED,      font=("Arial", 9, "bold"))
    result_text.tag_config("pill_ok",   foreground=SUCCESS_GREEN,   font=("Arial", 9, "bold"))

    def do_search(event=None):
        reset_activity_timer()
        name   = search_var.get().strip()
        rows   = get_patient_history(name)

        result_text.config(state="normal")
        result_text.delete("1.0", "end")

        if not name:
            result_text.insert("end", "Type a patient name above and press Enter or click Search.\n", "muted")
            result_text.config(state="disabled")
            return

        if not rows:
            result_text.insert("end", f"No records found for '{name}'.\n", "muted")
            result_text.config(state="disabled")
            log_action("HISTORY SEARCH", f"No results for '{name}'")
            return

        log_action("HISTORY SEARCH", f"Viewed history for '{name}' ({len(rows)} record(s))")

        # Group rows by Patient_ID so we handle multiple visits cleanly
        seen_patient = None
        for r in rows:
            pid = r.get("Patient_ID")
            if pid != seen_patient:
                seen_patient = pid
                result_text.insert("end", f"\n{'━'*60}\n", "divider")
                result_text.insert("end",
                    f"  {r.get('Full_Name','—')}   |   "
                    f"DOB: {r.get('Date_of_Birth','—')}   |   "
                    f"Gender: {r.get('Gender','—')}\n", "header")
                result_text.insert("end", f"{'━'*60}\n", "divider")

            # Visit block
            visit_date = r.get("Visit_Date") or "—"
            reason     = r.get("Reason")     or "—"
            diag_name  = r.get("Diagnosis_Name") or "—"
            diag_desc  = r.get("Description")    or "—"
            dosage     = r.get("Dosage_Info")    or "—"
            doctor     = r.get("doctor_name")    or "—"

            result_text.insert("end", "\n  📅 Visit\n", "subheader")
            result_text.insert("end", f"     Date   : {visit_date}\n", "value")
            result_text.insert("end", f"     Reason : {reason}\n",     "value")

            result_text.insert("end", "\n  🩺 Diagnosis\n", "subheader")
            result_text.insert("end", f"     Name   : {diag_name}\n",  "value")
            result_text.insert("end", f"     Notes  : {diag_desc}\n",  "value")

            result_text.insert("end", "\n  💊 Treatment\n", "subheader")
            result_text.insert("end", f"     Dosage : {dosage}\n",     "value")

            result_text.insert("end", "\n  👨‍⚕️ Attending Doctor\n", "subheader")
            result_text.insert("end", f"     Name   : {doctor}\n",     "value")
            result_text.insert("end", "\n" + "  " + "─"*54 + "\n",    "divider")

        result_text.config(state="disabled")

    tk.Button(search_frame, text="Search", bg=ACCENT, fg="white", relief="flat",
              font=("Arial", 10, "bold"), padx=12, pady=3,
              cursor="hand2", command=do_search).pack(side="left", padx=(8, 0))

    search_entry.bind("<Return>", do_search)

    tk.Button(footer, text="Close", command=win.destroy, bg="white", fg=TEXT_DARK,
              relief="flat", highlightbackground=BORDER, highlightthickness=1,
              padx=15, pady=6).pack(side="right")

# ================================================================
#  AUDIT LOG POPUP
# ================================================================
def open_audit_log_window():
    reset_activity_timer()
    win, body, footer = styled_popup("Audit Log", "820x480")

    cols = ("Timestamp", "Username", "Role", "Action", "Details")
    tree = ttk.Treeview(body, columns=cols, show="headings", height=16)
    widths = [140, 110, 100, 140, 280]
    for col, w in zip(cols, widths):
        tree.heading(col, text=col)
        tree.column(col, width=w, minwidth=60)

    vsb = ttk.Scrollbar(body, orient="vertical",   command=tree.yview)
    hsb = ttk.Scrollbar(body, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    body.rowconfigure(0, weight=1)
    body.columnconfigure(0, weight=1)

    logs = get_audit_logs()
    for row in logs:
        tree.insert("", "end", values=(
            row.get("Timestamp",""),
            row.get("Username",""),
            row.get("Role",""),
            row.get("Action",""),
            row.get("Details",""),
        ))

    tk.Button(footer, text="Close", command=win.destroy, bg="white", fg=TEXT_DARK,
              relief="flat", highlightbackground=BORDER, highlightthickness=1,
              padx=15, pady=6).pack(side="right")

# ================================================================
#  USER MANAGEMENT POPUP  (Admin only — simple version)
# ================================================================
def open_user_management_window():
    reset_activity_timer()
    win, body, footer = styled_popup("User Management", "600x480")

    # ---- User list ----
    list_frame = tk.LabelFrame(body, text="Current Users", bg=BG_MAIN, fg=TEXT_DARK,
                               font=("Arial", 10, "bold"), padx=10, pady=8)
    list_frame.pack(fill="both", expand=True)

    cols = ("User_ID", "Username", "Role")
    tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=8)
    for col, w in zip(cols, [60, 180, 120]):
        tree.heading(col, text=col)
        tree.column(col, width=w)
    tree.pack(fill="both", expand=True)

    def refresh_list():
        tree.delete(*tree.get_children())
        for u in get_all_users():
            tree.insert("", "end", values=(u["User_ID"], u["Username"], u["Role"]))

    refresh_list()

    # ---- Add user ----
    add_frame = tk.LabelFrame(body, text="Add New User", bg=BG_MAIN, fg=TEXT_DARK,
                              font=("Arial", 10, "bold"), padx=10, pady=8)
    add_frame.pack(fill="x", pady=(12, 0))

    nu_entry  = form_row(add_frame, 0, "Username")
    np_entry  = form_row(add_frame, 1, "Password", show="•")

    tk.Label(add_frame, text="Role", bg=BG_MAIN, fg=TEXT_DARK,
             font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", pady=8)
    nr_var = tk.StringVar(value="Receptionist")
    ttk.Combobox(add_frame, textvariable=nr_var,
                 values=["Admin", "Doctor", "Receptionist"],
                 state="readonly", font=("Arial", 10)).grid(row=2, column=1, sticky="ew", pady=8)

    def add_user():
        uname = nu_entry.get().strip()
        pwd   = np_entry.get()
        role  = nr_var.get()
        if not uname or not pwd:
            messagebox.showerror("Error", "Username and password are required.")
            return
        if create_user_db(uname, pwd, role):
            messagebox.showinfo("Success", f"User '{uname}' created.")
            nu_entry.delete(0, "end")
            np_entry.delete(0, "end")
            refresh_list()

    def delete_selected():
        selected = tree.focus()
        if not selected:
            messagebox.showwarning("Select", "Please select a user to delete.")
            return
        vals = tree.item(selected, "values")
        uid  = vals[0]
        uname = vals[1]
        if uname == SESSION["username"]:
            messagebox.showerror("Error", "You cannot delete your own account.")
            return
        if messagebox.askyesno("Confirm", f"Delete user '{uname}'?"):
            if delete_user_db(uid):
                messagebox.showinfo("Deleted", f"User '{uname}' deleted.")
                refresh_list()

    btn_row = tk.Frame(add_frame, bg=BG_MAIN)
    btn_row.grid(row=3, column=0, columnspan=2, sticky="e", pady=(4, 0))
    tk.Button(btn_row, text="Add User", bg=ACCENT, fg="white", relief="flat",
              padx=12, pady=5, command=add_user).pack(side="left", padx=(0, 8))
    tk.Button(btn_row, text="Delete Selected", bg=DANGER_RED, fg="white", relief="flat",
              padx=12, pady=5, command=delete_selected).pack(side="left")

    tk.Button(footer, text="Close", command=win.destroy, bg="white", fg=TEXT_DARK,
              relief="flat", highlightbackground=BORDER, highlightthickness=1,
              padx=15, pady=6).pack(side="right")

# ================================================================
#  ADD PATIENT POPUP
# ================================================================
def open_add_patient_window():
    reset_activity_timer()
    win, body, footer = styled_popup("Register & Add to Queue", "440x600")

    info_frame = tk.LabelFrame(body, text="Patient Information", bg=BG_MAIN, fg=TEXT_DARK,
                               font=("Arial", 10, "bold"), padx=15, pady=10)
    info_frame.pack(fill="x")

    name_entry      = form_row(info_frame, 0, "Full Name")
    dob_entry       = form_row(info_frame, 1, "Date of Birth (YYYY-MM-DD)")

    tk.Label(info_frame, text="Gender", bg=BG_MAIN, fg=TEXT_DARK,
             font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", pady=8)
    gender_var   = tk.StringVar()
    gender_frame = tk.Frame(info_frame, bg=BG_MAIN)
    gender_frame.grid(row=2, column=1, sticky="w")
    for g in ["Male", "Female", "Other"]:
        tk.Radiobutton(gender_frame, text=g, variable=gender_var, value=g,
                       bg=BG_MAIN, fg=TEXT_DARK, selectcolor="white").pack(side="left", padx=(0, 8))

    phone_entry     = form_row(info_frame, 3, "Phone Number")
    address_entry   = form_row(info_frame, 4, "Address")
    emergency_entry = form_row(info_frame, 5, "Emergency Contact")

    triage_frame = tk.LabelFrame(body, text="Today's Visit", bg=BG_MAIN, fg=TEXT_DARK,
                                 font=("Arial", 10, "bold"), padx=15, pady=10)
    triage_frame.pack(fill="x", pady=(15, 0))
    symptoms_entry = form_row(triage_frame, 0, "Symptoms")

    tk.Button(footer, text="Cancel", command=win.destroy, bg="white", fg=TEXT_DARK,
              relief="flat", highlightbackground=BORDER, highlightthickness=1,
              padx=15, pady=6).pack(side="right", padx=(8, 0))
    tk.Button(footer, text="Submit", bg=ACCENT, fg="white", relief="flat", padx=15, pady=6,
              command=lambda: add_patient_to_queue(
                  name_entry.get(), dob_entry.get(), gender_var.get(),
                  phone_entry.get(), address_entry.get(), emergency_entry.get(),
                  symptoms_entry.get(), win)).pack(side="right")

# ================================================================
#  MAIN DASHBOARD  (stubs for refresh + notification banner)
# ================================================================
window              = None
notification_banner = None
session_label       = None
content_frame       = None

def refresh_notification_banner():
    if notification_banner is None:
        return
    upcoming = run_query(
        """SELECT COUNT(*) AS cnt FROM appointment
           WHERE Appointment_Date BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL %s MINUTE)""",
        (REMINDER_WINDOW_MINUTES,), fetch=True
    ) or []
    cnt = upcoming[0]["cnt"] if upcoming else 0
    if cnt > 0:
        notification_banner.config(
            text=f"🔔  {cnt} appointment(s) coming up in the next {REMINDER_WINDOW_MINUTES} minutes",
            bg="#fef9c3", fg="#92400e"
        )
        notification_banner.pack(fill="x")
    else:
        notification_banner.pack_forget()

def refresh_dashboard():
    pass   # placeholder — queue panel calls this after mutations

def logout():
    if SESSION["logged_in"]:
        log_action("LOGOUT", f"User '{SESSION['username']}' logged out")
    SESSION.update({"user_id": None, "username": None, "role": None, "logged_in": False})
    window.destroy()
    main()   # restart → shows login again

def build_main_window():
    global window, notification_banner, session_label, content_frame

    window = tk.Tk()
    window.title(CLINIC_NAME)
    window.geometry("1100x680")
    window.configure(bg=BG_MAIN)
    window.bind_all("<Motion>",   reset_activity_timer)
    window.bind_all("<KeyPress>", reset_activity_timer)

    # ----------------------------------------------------------------
    #  TOP BAR
    # ----------------------------------------------------------------
    topbar = tk.Frame(window, bg=BG_DARK, height=56)
    topbar.pack(fill="x")
    topbar.pack_propagate(False)

    tk.Label(topbar, text=f"🏥  {CLINIC_NAME}", bg=BG_DARK, fg=TXT_LIGHT,
             font=("Arial", 13, "bold")).pack(side="left", padx=20)

    # Right side: role badge + username + logout
    right_bar = tk.Frame(topbar, bg=BG_DARK)
    right_bar.pack(side="right", padx=16)

    role_badge = tk.Label(right_bar,
                          text=SESSION["role"],
                          bg=ACCENT, fg="white",
                          font=("Arial", 8, "bold"),
                          padx=6, pady=2)
    role_badge.pack(side="left", padx=(0, 6))

    session_label = tk.Label(right_bar,
                             text=f"👤  {SESSION['username']}",
                             bg=BG_DARK, fg=TXT_LIGHT,
                             font=("Arial", 10))
    session_label.pack(side="left", padx=(0, 14))

    tk.Button(right_bar, text="Logout", bg=DANGER_RED, fg="white",
              relief="flat", padx=10, pady=4, cursor="hand2",
              font=("Arial", 9, "bold"), command=logout).pack(side="left")

    # ----------------------------------------------------------------
    #  NOTIFICATION BANNER  (hidden by default)
    # ----------------------------------------------------------------
    notification_banner = tk.Label(window, text="", font=("Arial", 9), pady=5)

    # ----------------------------------------------------------------
    #  SIDEBAR
    # ----------------------------------------------------------------
    sidebar = tk.Frame(window, bg=BG_DARK, width=200)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    content_frame = tk.Frame(window, bg=BG_MAIN)
    content_frame.pack(side="left", fill="both", expand=True)

    def nav_btn(text, icon, cmd):
        btn = tk.Button(sidebar, text=f"  {icon}  {text}", anchor="w",
                        bg=BG_DARK, fg=TXT_LIGHT, relief="flat",
                        font=("Arial", 10), padx=12, pady=10,
                        cursor="hand2", command=cmd,
                        activebackground=BG_DARK_HOVER, activeforeground="white")
        btn.pack(fill="x")
        btn.bind("<Enter>", lambda e: btn.config(bg=BG_DARK_HOVER))
        btn.bind("<Leave>", lambda e: btn.config(bg=BG_DARK))
        return btn

    tk.Label(sidebar, text="MENU", bg=BG_DARK, fg="#6366f1",
             font=("Arial", 8, "bold"), pady=12).pack(fill="x", padx=16)

    nav_btn("Register Patient",  "➕", open_add_patient_window)
    nav_btn("Patient History",   "📋", open_patient_history_window)
    nav_btn("Appointments",      "📅", lambda: show_section("appointments"))
    nav_btn("Waiting Queue",     "🏥", lambda: show_section("queue"))
    nav_btn("Audit Log",         "🔍", open_audit_log_window)
    nav_btn("User Management",   "👥", open_user_management_window)

    tk.Frame(sidebar, bg="#312e81", height=1).pack(fill="x", padx=12, pady=8)
    nav_btn("Export Queue",      "📤", export_queue)
    nav_btn("Serve Next Patient","✅", serve_patient)
    nav_btn("Clear Queue",       "🗑", clear_queue)

    # ----------------------------------------------------------------
    #  DEFAULT CONTENT  — queue dashboard
    # ----------------------------------------------------------------
    show_section("queue")

    # ----------------------------------------------------------------
    #  START BACKGROUND TASKS
    # ----------------------------------------------------------------
    load_health_workers()
    check_appointment_notifications()
    check_session_timeout()

    window.mainloop()

# ================================================================
#  SECTION VIEWS  (queue / appointments)
# ================================================================
_queue_search_var = None

def show_section(name):
    global _queue_search_var
    for widget in content_frame.winfo_children():
        widget.destroy()

    if name == "queue":
        _queue_search_var = tk.StringVar()
        _build_queue_panel(content_frame)
    elif name == "appointments":
        _build_appointments_panel(content_frame)

def _stat_card(parent, label, value, colors):
    bg, fg = colors
    card = tk.Frame(parent, bg=bg, padx=20, pady=14,
                    highlightbackground=fg, highlightthickness=1)
    tk.Label(card, text=str(value), bg=bg, fg=fg, font=("Arial", 22, "bold")).pack()
    tk.Label(card, text=label,      bg=bg, fg=fg, font=("Arial", 9)).pack()
    return card

def _build_queue_panel(parent):
    # Stats row
    stats_row = tk.Frame(parent, bg=BG_MAIN)
    stats_row.pack(fill="x", padx=20, pady=(18, 10))

    total, emergency, high, normal = get_stats()
    for label, val, colors in [
        ("Total",     total,     TINT_TOTAL),
        ("Emergency", emergency, TINT_EMERGENCY),
        ("High",      high,      TINT_HIGH),
        ("Normal",    normal,    TINT_NORMAL),
    ]:
        c = _stat_card(stats_row, label, val, colors)
        c.pack(side="left", padx=(0, 12), ipadx=10)

    # Search bar
    sf = tk.Frame(parent, bg=BG_MAIN)
    sf.pack(fill="x", padx=20, pady=(0, 8))
    tk.Label(sf, text="Filter Queue:", bg=BG_MAIN, fg=TEXT_DARK,
             font=("Arial", 10, "bold")).pack(side="left", padx=(0, 8))
    sv = tk.StringVar()
    se = tk.Entry(sf, textvariable=sv, font=("Arial", 10), relief="flat",
                  highlightbackground=BORDER, highlightthickness=1, bg="white", width=28)
    se.pack(side="left", ipady=4)

    # Queue table
    cols    = ("Queue #", "Patient ID", "Name", "Age", "Priority", "Diagnosis", "Specialty", "Assigned To")
    tree    = ttk.Treeview(parent, columns=cols, show="headings")
    widths  = [70, 80, 150, 45, 100, 140, 130, 140]
    for col, w in zip(cols, widths):
        tree.heading(col, text=col)
        tree.column(col, width=w, minwidth=50)

    tree.tag_configure("Emergency",    background="#fef2f2", foreground="#dc2626")
    tree.tag_configure("High Priority",background="#fffbeb", foreground="#d97706")
    tree.tag_configure("Normal",       background="#f0fdf4", foreground="#166534")

    vsb = ttk.Scrollbar(parent, orient="vertical",   command=tree.yview)
    hsb = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tree.pack(fill="both", expand=True, padx=20)
    vsb.pack(side="right",  fill="y",  padx=(0, 20))
    hsb.pack(side="bottom", fill="x",  padx=20, pady=(0, 6))

    def populate_tree(*args):
        tree.delete(*tree.get_children())
        for p in get_waiting(sv.get()):
            tree.insert("", "end", values=(
                p["queue_number"], p["patient_id"], p["name"],
                p["age"], p["priority"], p["diagnosis"],
                p["specialty"], p["worker_name"]
            ), tags=(p["priority"],))

    sv.trace_add("write", populate_tree)
    populate_tree()

    # Override refresh_dashboard to repopulate
    global refresh_dashboard
    def refresh_dashboard():
        populate_tree()
        _rebuild_stats()

    def _rebuild_stats():
        for w in stats_row.winfo_children():
            w.destroy()
        t2, e2, h2, n2 = get_stats()
        for label, val, colors in [
            ("Total",     t2, TINT_TOTAL),
            ("Emergency", e2, TINT_EMERGENCY),
            ("High",      h2, TINT_HIGH),
            ("Normal",    n2, TINT_NORMAL),
        ]:
            c = _stat_card(stats_row, label, val, colors)
            c.pack(side="left", padx=(0, 12), ipadx=10)

def _build_appointments_panel(parent):
    tk.Label(parent, text="Appointments", bg=BG_MAIN, fg=TEXT_DARK,
             font=("Arial", 14, "bold")).pack(pady=(18, 8), padx=20, anchor="w")

    sf = tk.Frame(parent, bg=BG_MAIN)
    sf.pack(fill="x", padx=20, pady=(0, 8))
    tk.Label(sf, text="Search:", bg=BG_MAIN, fg=TEXT_DARK,
             font=("Arial", 10, "bold")).pack(side="left", padx=(0, 8))
    sv = tk.StringVar()
    tk.Entry(sf, textvariable=sv, font=("Arial", 10), relief="flat",
             highlightbackground=BORDER, highlightthickness=1, bg="white",
             width=28).pack(side="left", ipady=4)

    cols   = ("ID", "Date", "Patient", "Doctor", "Specialty")
    tree   = ttk.Treeview(parent, columns=cols, show="headings")
    widths = [60, 160, 180, 180, 160]
    for col, w in zip(cols, widths):
        tree.heading(col, text=col)
        tree.column(col, width=w, minwidth=50)

    vsb = ttk.Scrollbar(parent, orient="vertical",   command=tree.yview)
    hsb = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tree.pack(fill="both", expand=True, padx=20)
    vsb.pack(side="right",  fill="y",  padx=(0, 20))
    hsb.pack(side="bottom", fill="x",  padx=20, pady=(0, 6))

    def populate(*args):
        tree.delete(*tree.get_children())
        for a in get_appointments(sv.get()):
            tree.insert("", "end", values=(
                a["Appointment_ID"],
                a["Appointment_Date"],
                a["Full_Name"],
                a.get("Worker_Name", "—"),
                a.get("Worker_Specialty", "—"),
            ))

    sv.trace_add("write", populate)
    populate()

# ================================================================
#  SQL SETUP HELPERS  (printed to console — run once in MySQL)
# ================================================================
SETUP_SQL = """
-- Run these once in your MySQL database:

CREATE TABLE IF NOT EXISTS users (
    User_ID  INT AUTO_INCREMENT PRIMARY KEY,
    Username VARCHAR(100) NOT NULL UNIQUE,
    Password VARCHAR(100) NOT NULL,
    Role     ENUM('Admin','Doctor','Receptionist') NOT NULL
);

-- Default admin account  (change the password!)
INSERT IGNORE INTO users (Username, Password, Role) VALUES ('admin', 'admin123', 'Admin');

CREATE TABLE IF NOT EXISTS audit_log (
    Log_ID    INT AUTO_INCREMENT PRIMARY KEY,
    User_ID   INT,
    Username  VARCHAR(100),
    Role      VARCHAR(50),
    Action    VARCHAR(100),
    Details   TEXT,
    Timestamp DATETIME
);
"""

# ================================================================
#  ENTRY POINT
# ================================================================
def main():
    print("=" * 60)
    print("DB SETUP SQL (run once if tables don't exist):")
    print(SETUP_SQL)
    print("=" * 60)

    show_login_window()

    if not SESSION["logged_in"]:
        # User closed the login window without logging in
        return

    build_main_window()

if __name__ == "__main__":
    main()