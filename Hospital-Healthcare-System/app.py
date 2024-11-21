from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

# Database initialization
def init_db():
    conn = sqlite3.connect('hcms.db')
    cursor = conn.cursor()

    # Create the 'patients' table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            contact TEXT
        )
    ''')

    # Create the 'appointments' table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            doctor_name TEXT,
            appointment_date TEXT,
            is_completed INTEGER DEFAULT 0,
            prescription TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients (id)
        )
    ''')

    # Commit the changes to the database
    conn.commit()
    conn.close()

# Initialize the database
init_db()

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register_patient():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        contact = request.form['contact']
        conn = sqlite3.connect('hcms.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO patients (name, age, contact) VALUES (?, ?, ?)', (name, age, contact))
        conn.commit()
        conn.close()
        return redirect(url_for('register_patient'))
    
    conn = sqlite3.connect('hcms.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM patients')
    patients = cursor.fetchall()
    conn.close()
    return render_template('register.html', patients=patients)

@app.route('/deregister/<int:patient_id>', methods=['POST'])
def deregister_patient(patient_id):
    conn = sqlite3.connect('hcms.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM patients WHERE id = ?', (patient_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('register_patient'))

@app.route('/appointments', methods=['GET', 'POST'])
def schedule_appointment():
    conn = sqlite3.connect('hcms.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM patients')
    patients = cursor.fetchall()
    conn.close()

    if request.method == 'POST':
        patient_id = request.form['patient_id']
        doctor_name = request.form['doctor_name']
        appointment_date = request.form['appointment_date']
        conn = sqlite3.connect('hcms.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO appointments (patient_id, doctor_name, appointment_date) VALUES (?, ?, ?)',
                       (patient_id, doctor_name, appointment_date))
        conn.commit()
        conn.close()
        return redirect(url_for('home'))
    return render_template('appointments.html', patients=patients)

@app.route('/doctor_dashboard')
def doctor_dashboard():
    conn = sqlite3.connect('hcms.db')
    cursor = conn.cursor()

    # Fetch appointments for the logged-in doctor
    cursor.execute('''
        SELECT appointments.id, patients.name, appointments.doctor_name, appointments.appointment_date, appointments.is_completed, appointments.prescription
        FROM appointments
        JOIN patients ON appointments.patient_id = patients.id
    ''')
    appointments = cursor.fetchall()
    conn.close()

    return render_template('doctor_dashboard.html', appointments=appointments)

@app.route('/mark_complete/<int:appointment_id>', methods=['GET', 'POST'])
def mark_appointment_complete(appointment_id):
    if request.method == 'POST':
        # Get the prescription entered by the doctor
        prescription = request.form.get('prescription', '')  # Optional field

        # Update the appointment: mark it as complete and store the prescription (if any)
        conn = sqlite3.connect('hcms.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE appointments
            SET is_completed = 1, prescription = ?
            WHERE id = ?
        ''', (prescription, appointment_id))
        conn.commit()
        conn.close()

        # Redirect to the doctor dashboard after the update
        return redirect(url_for('doctor_dashboard'))

    # If GET request, show the form to mark the appointment complete and provide a prescription
    conn = sqlite3.connect('hcms.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM appointments WHERE id = ?', (appointment_id,))
    appointment = cursor.fetchone()
    conn.close()

    return render_template('mark_complete.html', appointment=appointment)

if __name__ == '__main__':
    app.run(debug=True)
