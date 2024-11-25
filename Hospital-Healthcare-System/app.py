from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask import redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hcms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database initialization
def init_db():
    conn = sqlite3.connect('hcms.db', timeout=10)
    cursor = conn.cursor()

    # Create the 'patients' table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            name TEXT,
            age INTEGER,
            contact TEXT,
            role TEXT DEFAULT 'patient'
        )
    ''')

    # Create the 'appointments' table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_date TEXT NOT NULL,
            status TEXT DEFAULT "Pending",
            is_completed INTEGER DEFAULT 0,
            prescription TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients (id),
            FOREIGN KEY (doctor_id) REFERENCES users (id)
        )
    ''')

    # Create the 'users' table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT NOT NULL,
            name TEXT
        )
    ''')

    # Add default users
    default_users = [
        ('John', '1234john', 'doctor', 'Dr. John Doe'),
        ('Jane', '1234jane', 'doctor', 'Dr. Jane Smith'),
        ('Receptionist', '1234r', 'receptionist', 'Receptionist')
    ]
    for user in default_users:
        cursor.execute('SELECT * FROM users WHERE username = ?', (user[0],))
        if not cursor.fetchone():
            cursor.execute('INSERT INTO users (username, password, role, name) VALUES (?, ?, ?, ?)', user)

    conn.commit()
    conn.close()

# Initialize the database at application startup
init_db()

# Routes
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('hcms.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # First, check if the user is a patient (patients table)
        cursor.execute("SELECT * FROM patients WHERE username = ? AND password = ?", (username, password))
        patient = cursor.fetchone()

        if patient:
            session['user_id'] = patient['id']
            session['role'] = 'patient'  # Set the role as 'patient'
            conn.close()
            return redirect(url_for('patient_dashboard'))

        # If not a patient, check if the user is a doctor or receptionist (users table)
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user['id']
            session['role'] = user['role']  # Set the role to doctor or receptionist
            conn.close()

            # Redirect based on the role
            if user['role'] == 'receptionist':
                return redirect(url_for('receptionist_dashboard'))
            elif user['role'] == 'doctor':
                return redirect(url_for('doctor_dashboard'))

        # If no user or patient is found
        conn.close()
        return render_template('login.html', error="Invalid credentials")

    return render_template('login.html')



@app.route('/patient_dashboard', methods=['GET', 'POST'])
def patient_dashboard():
    if 'user_id' not in session or session.get('role') != 'patient':
        return redirect(url_for('login'))

    patient_id = session['user_id']
    conn = sqlite3.connect('hcms.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch patient details
    cursor.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
    patient = cursor.fetchone()

    # Fetch the patient's appointments
    cursor.execute('''
        SELECT a.id, a.appointment_date, a.status, a.prescription, d.name AS doctor_name
        FROM appointments a
        JOIN users d ON a.doctor_id = d.id
        WHERE a.patient_id = ?
        ORDER BY a.appointment_date
    ''', (patient_id,))
    appointments = cursor.fetchall()

    # Fetch list of doctors
    cursor.execute('SELECT id, name FROM users WHERE role = "doctor"')
    doctors = cursor.fetchall()

    # Handle appointment cancellation
    if request.method == 'POST' and 'cancel_appointment' in request.form:
        appointment_id = request.form['appointment_id']
        cursor.execute('DELETE FROM appointments WHERE id = ?', (appointment_id,))
        conn.commit()
        return redirect(url_for('patient_dashboard'))

    # Handle removing completed appointments
    if request.method == 'POST' and 'remove_completed' in request.form:
        appointment_id = request.form['appointment_id']
        cursor.execute('DELETE FROM appointments WHERE id = ? AND status = "Completed"', (appointment_id,))
        conn.commit()
        return redirect(url_for('patient_dashboard'))

    conn.close()
    return render_template('patient_dashboard.html', patient=patient, appointments=appointments,doctors=doctors)


@app.route('/doctor_dashboard', methods=['GET', 'POST'])
def doctor_dashboard():
    if 'user_id' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))

    doctor_id = session['user_id']
    conn = sqlite3.connect('hcms.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch current confirmed appointments for the logged-in doctor
    cursor.execute('''
        SELECT a.id, a.appointment_date, a.status, a.prescription, p.name AS patient_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE a.doctor_id = ? AND a.status = "Confirmed"
        ORDER BY a.appointment_date
    ''', (doctor_id,))
    appointments = cursor.fetchall()

    # Handle marking an appointment as completed
    if request.method == 'POST' and 'mark_complete' in request.form:
        appointment_id = request.form['appointment_id']
        prescription = request.form['prescription']

    # Update the appointment with the status and prescription
        cursor.execute('''
            UPDATE appointments
            SET status = "Completed", prescription = ?, is_completed = 1
            WHERE id = ?
        ''', (prescription, appointment_id))
        conn.commit()

        return redirect(url_for('doctor_dashboard'))

    conn.close()
    return render_template('doctor_dashboard.html', appointments=appointments)


@app.route('/receptionist_dashboard', methods=['GET', 'POST'])
def receptionist_dashboard():
    if 'user_id' not in session or session.get('role') != 'receptionist':
        return redirect(url_for('login'))

    conn = sqlite3.connect('hcms.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    error_message = None  # Initialize error_message to None

    # Fetch doctors from the users table where role is "doctor"
    cursor.execute('SELECT id, name FROM users WHERE role = "doctor"')
    doctors = cursor.fetchall()

    # Fetch patients from the patients table
    cursor.execute('SELECT id, name FROM patients')
    patients = cursor.fetchall()

    # Handle patient registration
    if request.method == 'POST' and 'register_patient' in request.form:
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        age = request.form['age']
        contact = request.form['contact']
        role = request.form['role']

        # Check if the username already exists
        cursor.execute('SELECT * FROM patients WHERE username = ?', (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            error_message = f"Username '{username}' is already taken. Please choose a different username."
        else:
            # Insert the new patient into the patients table
            cursor.execute('INSERT INTO patients (username, password, name, age, contact, role) VALUES (?, ?, ?, ?, ?, ?)',
                           (username, password, name, age, contact, role))
            conn.commit()
            # After registering the patient, we redirect to the same page to refresh the patient list
            return redirect(url_for('receptionist_dashboard'))

    # Handle appointment assignment
    if request.method == 'POST' and 'assign_appointment' in request.form:
        try:
            patient_id = request.form['patient_id']
            doctor_id = request.form['doctor_id']
            appointment_date = request.form['appointment_date']

            # Insert the new appointment with 'Assigned' status
            cursor.execute('''
                INSERT INTO appointments (patient_id, doctor_id, appointment_date, status)
                VALUES (?, ?, ?, "Assigned")
            ''', (patient_id, doctor_id, appointment_date))
            conn.commit()

        except sqlite3.Error as e:
            error_message = f"An error occurred: {e}"
        finally:
            return redirect(url_for('receptionist_dashboard'))

    # Fetch pending appointments (status = "Pending")
    cursor.execute('''
        SELECT a.id, a.appointment_date, p.name AS patient_name, d.name AS doctor_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN users d ON a.doctor_id = d.id
        WHERE a.status = "Pending"
    ''')
    pending_appointments = cursor.fetchall()

    # Handle confirming a pending appointment
    if request.method == 'POST' and 'confirm_appointment' in request.form:
        appointment_id = request.form['appointment_id']
        cursor.execute('UPDATE appointments SET status = "Confirmed" WHERE id = ?', (appointment_id,))
        conn.commit()
        return redirect(url_for('receptionist_dashboard'))

    # Fetch assigned appointments (status = "Assigned")
    cursor.execute('''
        SELECT a.id, a.appointment_date, p.name AS patient_name, d.name AS doctor_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN users d ON a.doctor_id = d.id
        WHERE a.status = "Assigned"
    ''')
    assigned_appointments = cursor.fetchall()

    # Fetch confirmed appointments (status = "Confirmed")
    cursor.execute('''
        SELECT a.id, a.appointment_date, p.name AS patient_name, d.name AS doctor_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN users d ON a.doctor_id = d.id
        WHERE a.status = "Confirmed"
    ''')
    confirmed_appointments = cursor.fetchall()

    conn.close()
    return render_template(
        'receptionist_dashboard.html',
        doctors=doctors,
        patients=patients,
        pending_appointments=pending_appointments,
        assigned_appointments=assigned_appointments,
        confirmed_appointments=confirmed_appointments,
        error_message=error_message
    )


@app.route('/confirm_assigned/<int:appointment_id>', methods=['POST'])
def confirm_assigned(appointment_id):
    if 'user_id' not in session or session.get('role') != 'receptionist':
        return redirect(url_for('login'))

    conn = sqlite3.connect('hcms.db')
    cursor = conn.cursor()

    try:
        # Fetch the updated appointment to confirm the status
        cursor.execute('SELECT id, status FROM appointments WHERE id = ?', (appointment_id,))
        updated_appointment = cursor.fetchone()

        # Access the values by index (0 for id, 1 for status)
        appointment_id_from_db = updated_appointment[0]  # The appointment ID
        status_from_db = updated_appointment[1]  # The status of the appointment

        # Optional: Log or print for debugging
        print(f"Appointment ID: {appointment_id_from_db} confirmed with status: {status_from_db}")

        # Update the status of the appointment to "Confirmed"
        cursor.execute('UPDATE appointments SET status = "Confirmed" WHERE id = ?', (appointment_id,))
        conn.commit()

    except sqlite3.Error as e:
        # Handle any errors
        print(f"Error confirming appointment: {e}")
        conn.rollback()
    finally:
        conn.close()

    return redirect(url_for('receptionist_dashboard'))


@app.route('/cancel_appointment/<int:appointment_id>', methods=['POST'])
def cancel_appointment(appointment_id):
    if 'user_id' not in session or session.get('role') != 'receptionist':
        return redirect(url_for('login'))

    conn = sqlite3.connect('hcms.db')
    cursor = conn.cursor()

    # Update the status of the appointment to "Cancelled"
    cursor.execute('UPDATE appointments SET status = "Cancelled" WHERE id = ?', (appointment_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('receptionist_dashboard'))

@app.route('/request_appointment', methods=['POST'])
def request_appointment():
    if 'user_id' not in session or session.get('role') != 'patient':
        return redirect(url_for('login'))

    patient_id = session['user_id']
    doctor_id = request.form['doctor_id']
    appointment_date = request.form['appointment_date']

    conn = sqlite3.connect('hcms.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Insert new appointment request into the database with status "Pending"
    cursor.execute('''
        INSERT INTO appointments (patient_id, doctor_id, appointment_date, status)
        VALUES (?, ?, ?, "Pending")
    ''', (patient_id, doctor_id, appointment_date))

    conn.commit()
    conn.close()

    return redirect(url_for('patient_dashboard'))


@app.route('/deregister_patient/<int:patient_id>', methods=['POST'])
def deregister_patient(patient_id):
    if 'user_id' not in session or session.get('role') != 'receptionist':
        return redirect(url_for('login'))

    conn = sqlite3.connect('hcms.db')
    cursor = conn.cursor()

    # Delete the patient from the 'patients' table
    cursor.execute('DELETE FROM patients WHERE id = ?', (patient_id,))

    # Optionally, you can delete appointments related to the patient
    cursor.execute('DELETE FROM appointments WHERE patient_id = ?', (patient_id,))

    conn.commit()
    conn.close()

    return redirect(url_for('receptionist_dashboard'))

@app.route('/mark_appointment_complete/<int:appointment_id>', methods=['POST'])
def mark_appointment_complete(appointment_id):
    if 'user_id' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))

    prescription = request.form.get('prescription')

    conn = sqlite3.connect('hcms.db')
    cursor = conn.cursor()

    try:
        # Update the appointment status to 'Completed' and add the prescription
        cursor.execute('''
            UPDATE appointments
            SET status = "Completed", prescription = ?
            WHERE id = ?
        ''', (prescription, appointment_id))

        conn.commit()

        # Optionally, you can also update the patient's dashboard with the new status and prescription.
        # You can either redirect them to a different route or rely on the data refreshing via AJAX.

    except sqlite3.Error as e:
        print(f"Error updating appointment: {e}")
        conn.rollback()
    finally:
        conn.close()

    return redirect(url_for('doctor_dashboard'))

@app.route('/register_patient', methods=['POST'])
def register_patient():
    if 'user_id' not in session or session.get('role') != 'receptionist':
        return redirect(url_for('login'))

    # Handle patient registration here...
    return redirect(url_for('receptionist_dashboard'))


@app.route('/logout')
def logout():
    session.clear()  # Clears the session, logging the user out
    return redirect(url_for('home'))  # Redirects to the home page  # Redirecting to home page after logout



if __name__ == '__main__':
    app.run(debug=True)