from flask import Flask, request, render_template, redirect, url_for, session, flash
import requests

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
        if response.status_code != 201:
           # flash('Registration failed. Please try again.')
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
            user_id = data.get('user_id')
            session['token'] = token
            session['email'] = email
            session['user_id'] = user_id
#            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'error')
    
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
        response_message = booking_response.json()

        if booking_response.status_code == 201:
           
            return redirect(url_for('viewBookings'))
        else:
            flash(response_message.get("error"))
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

    return render_template(
        'viewBookings.html',
        bookings=bookings_paginated,
        user_id=user_id,
        page=page,
        total=total,
        per_page=per_page
    )
@app.route('/updateBooking/<booking_id>', methods=['GET', 'POST'])
def updateBooking(booking_id):
    token = session.get('token')
    user_id = session.get('user_id')
    if not token or not user_id:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    headers = {'Authorization': f'Bearer {token}'}

    # Fetch all user bookings and find the matching one
    booking_response = requests.get(f"{API_URL}/api/bookings/{user_id}", headers=headers)
    if booking_response.status_code == 201:
     
        return redirect(url_for('updateBooking', booking_id=booking_id))

    booking = None
    for b in booking_response.json():
        if b.get('booking_id') == booking_id:
            booking = b
            break

    if not booking:
        flash('Booking not found.', 'error')
        return redirect(url_for('viewBookings'))

    # Ensure the booking belongs to the logged-in user
    if booking.get('user_id') != user_id:
        flash('You are not authorized to update this booking.', 'error')
        return redirect(url_for('viewBookings'))

    # Handle form submission
    if request.method == 'POST':
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

        update_response = requests.put(
            f"{API_URL}/api/bookings/{booking_id}",
            json=updated_data,
            headers=headers
        )

        if update_response.status_code == 201:
            message = update_response.json().get("message", "Booking updated successfully.")
            flash(message, 'success')
            return redirect(url_for('updateBooking', booking_id=booking_id))
        else:
            error = update_response.json().get("error", "Failed to update booking.")
            flash(error, 'error')

    return render_template('updateBooking.html', booking=booking)


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
       return redirect(url_for('viewBookings'))
    else:
        flash('Failed to delete booking. Please try again.')
    return redirect(url_for('viewBookings'))

#if __name__ == '__main__':
 #   app.run(debug=True)