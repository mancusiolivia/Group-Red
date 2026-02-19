#!/usr/bin/env python3
"""Quick script to assign classes to students"""
import sqlite3

conn = sqlite3.connect('data/app.db')
cursor = conn.cursor()

# Get all students
cursor.execute('SELECT id, student_id, name FROM students')
students = cursor.fetchall()

# CS class names
classes = ['CS101', 'CS201', 'CS301', 'CS401', 'CS501', 'CS202', 'CS302', 'CS402', 'CS502', 'CS103']

print(f'Found {len(students)} students\n')

# Assign classes
for i, (student_id, student_campus_id, name) in enumerate(students):
    class_name = classes[i % len(classes)]
    cursor.execute('UPDATE students SET class_name = ? WHERE id = ?', (class_name, student_id))
    print(f'Assigned {class_name} to {name} ({student_campus_id})')

conn.commit()

# Verify
cursor.execute('SELECT COUNT(*) FROM students WHERE class_name IS NOT NULL')
count = cursor.fetchone()[0]
print(f'\n✓ Total students with classes: {count}/{len(students)}')

conn.close()
