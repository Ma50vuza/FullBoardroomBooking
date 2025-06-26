from flask import Flask, request, render_template, redirect, url_for, session, flash, jsonify
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key in production
API_URL = "https://bb-api-lmgy.onrender.com"

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        department = request.form['department']
        company = request.form['company']

        response = requests.post(f"{API_URL}/api/register/user", json={
            "username": username,
            "email": email,
            "password": password,
            "department": department,
            "company": company
        })
        if response.status_code != 200:
            flash('Registration failed. Please try again.')
            return redirect(url_for('register'))
        else:
            flash('Registration successful. Please log in.')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        response = requests.post(f"{API_URL}/api/login", json={"email": email, "password": password})
        if response.status_code == 200:
            data = response.json()
            token = data.get('jwt_token')
            user_id = data.get('user_id')  # Make sure your API returns this!
            session['token'] = token
            session['email'] = email
            session['user_id'] = user_id   # Store user_id in session
            flash('Login successful!')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password. Please try again.')
    return render_template('login.html')

@app.route('/addBooking', methods=['GET', 'POST'])
def addBooking():
    token = session.get('token')
    if not token:
        flash('Please log in first.')
        return redirect(url_for('login'))

    headers = {'Authorization': f'Bearer {token}'}

    # Fetch available rooms for the dropdown
    rooms_response = requests.get(f"{API_URL}/api/rooms", headers=headers)
    rooms = rooms_response.json() if rooms_response.status_code == 200 else []

    if request.method == 'POST':
        room_name = request.form.get('room_name')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        purpose = request.form.get('purpose')
        attendees_raw = request.form.get('attendees')
        attendees = [email.strip() for email in attendees_raw.split(',')] if attendees_raw else []

        # Find the room_id based on room_name
        room_id = None
        for room in rooms:
            if room.get('name') == room_name:
                room_id = room.get('room_id')
                break

        if not room_id:
            flash('Invalid room selected.')
            return render_template('addBooking.html', rooms=rooms)

        booking = {
            "room_id": room_id,
            "user_id": session["user_id"],
            "start_time": start_time,
            "end_time": end_time,
            "purpose": purpose,
            "attendees": attendees
        }
        booking_response = requests.post(f"{API_URL}/api/bookings", json=booking, headers=headers)
        if booking_response.status_code == 200:
            flash('Booking successful.')
            return redirect(url_for('dashboard'))
        else:
            flash('Booking failed. Please try again.')

    return render_template('addBooking.html', rooms=rooms)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    email = session.get('email')
    token = session.get('token')
    if not token:
        flash('Please log in first.')
        return redirect(url_for('login'))

    headers = {'Authorization': f'Bearer {token}'}

    # Fetch user profile
    response = requests.get(f"{API_URL}/api/profile", headers=headers)
    if response.status_code != 200:
        flash('Failed to load profile.')
        return redirect(url_for('login'))
    profile = response.json()
    company = profile.get('company')
    department = profile.get('department')
    username = profile.get('username')

    # Fetch available rooms
    rooms_response = requests.get(f"{API_URL}/api/rooms", headers=headers)
    rooms = rooms_response.json() if rooms_response.status_code == 200 else []
    for room in rooms: 
        room_id = room.get('room_id')
    

    # Handle booking form submission
    if request.method == 'POST':
        room_name = request.form.get('room_name')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        purpose = request.form.get('purpose')
        attendees_raw = request.form.get('attendees')
        attendees = [email.strip() for email in attendees_raw.split(',')] if attendees_raw else []

        booking = {
            "room_id": room_id,
            "start_time": start_time,
            "end_time": end_time,
            "purpose": purpose,
            "attendees": attendees
        }
        booking_response = requests.post(f"{API_URL}/api/bookings", json=booking, headers=headers)
        if booking_response.status_code == 200:
            flash('Booking successful.')
        else:
            flash('Booking failed. Please try again.')

    # Fetch all bookings
    bookings_response = requests.get(f"{API_URL}/api/bookings", headers=headers)
    bookings = bookings_response.json() if bookings_response.status_code == 200 else []

    return render_template('dashboard.html',email=email,company=company,department=department,username=username,rooms=rooms,bookings=bookings
    )
@app.route('/viewBookings')
def viewBookings():
    token = session.get('token')
    user_id = session.get('user_id')
    if not token or not user_id:
        flash('Please log in first.')
        return redirect(url_for('login'))

    # Pagination logic
    page = int(request.args.get('page', 1))
    per_page = 3 # Number of bookings per page

    headers = {'Authorization': f'Bearer {token}'}
    bookings_response = requests.get(f"{API_URL}/api/bookings", headers=headers)
    bookings = bookings_response.json() if bookings_response.status_code == 200 else []
    total = len(bookings)
    bookings_paginated = bookings[(page-1)*per_page:page*per_page]
    print(bookings_paginated)

    return render_template(
        'viewBookings.html',
        bookings=bookings_paginated,
        user_id=user_id,
        page=page,
        total=total,
        per_page=per_page
    )

@app.route('/updateBooking/<booking_id>', methods=['PUT', 'GET', 'POST'])
def updateBooking(booking_id):
    token = session.get('token')
    user_id = session.get('user_id')
    if not token or not user_id:
        flash('Please log in first.')
        return redirect(url_for('login'))

    headers = {'Authorization': f'Bearer {token}'}

    # Fetch the booking details
    booking_response = requests.get(f"{API_URL}/api/bookings/{user_id}", headers=headers)
    if booking_response.status_code != 200:
       flash('Booking not found.')
       return redirect(url_for('viewBookings'))
    for b in booking_response.json():
        booking = b
    print(booking)
     #Only allow the owner to update
    if booking.get('user_id') != user_id:
        flash('You are not authorized to update this booking.')
        return redirect(url_for('viewBookings'))

    if request.method == 'POST':
        # Get updated data from form
        purpose = request.form.get('purpose')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        attendees_raw = request.form.get('attendees')
        attendees = [email.strip() for email in attendees_raw.split(',')] if attendees_raw else []

        updated_data = {
            "user_id": user_id,
            "purpose": purpose,
            "start_time": start_time,
            "end_time": end_time,
            "attendees": attendees
        }
        print(updated_data)

        # Send update to API
        update_response = requests.put(
            f"{API_URL}/api/bookings/{booking_id}",
            json=updated_data,
            headers=headers
        )
        if update_response.status_code == 200:
            flash('Booking updated successfully.')
            return redirect(url_for('viewBookings'))
        else:
            flash('Failed to update booking. Please try again.')

    return render_template('updateBooking.html',booking=booking)

@app.route('/deleteBooking/<booking_id>', methods=['POST'])
def deleteBooking(booking_id):
    token = session.get('token')
    user_id = session.get('user_id')
    if not token or not user_id:
        flash('Please log in first.')
        return redirect(url_for('login'))

    headers = {'Authorization': f'Bearer {token}'}
    # Fetch the booking to check ownership
    booking_response = requests.get(f"{API_URL}/api/bookings/{user_id}", headers=headers)
    if booking_response.status_code != 200:
        flash('Booking not found.')
        return redirect(url_for('viewBookings'))
    for b in booking_response.json():
        booking = b
    if booking.get('user_id') != user_id:
        flash('You are not authorized to delete this booking.')
        return redirect(url_for('viewBookings'))

    # Delete the booking
    delete_data = {"user_id": user_id}
    delete_response = requests.delete(f"{API_URL}/api/bookings/{booking_id}", json=delete_data,headers=headers)
    if delete_response.status_code == 200:
        flash('Booking deleted successfully.')
    else:
        flash('Failed to delete booking. Please try again.')
    return redirect(url_for('viewBookings'))

if __name__ == '__main__':
    app.run(debug=True)