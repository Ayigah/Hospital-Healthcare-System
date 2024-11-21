import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('hcms.db')

# Create a cursor object to interact with the database
cursor = conn.cursor()

# Add the 'is_completed' and 'prescription' columns to the 'appointments' table
cursor.execute('''
    ALTER TABLE appointments ADD COLUMN is_completed INTEGER DEFAULT 0;
''')
cursor.execute('''
    ALTER TABLE appointments ADD COLUMN prescription TEXT;
''')

# Commit the changes to the database
conn.commit()

# Close the connection to the database
conn.close()

print("Columns 'is_completed' and 'prescription' added successfully.")
