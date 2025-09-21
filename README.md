# 🚆 Railway Reservation System (Streamlit + SQLite)
<div align="center">
  
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![SQLite](https://img.shields.io/badge/DB-SQLite-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Pandas](https://img.shields.io/badge/Pandas-DataFrame-150458?logo=pandas)](https://pandas.pydata.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>


A lightweight, single-file Streamlit app for managing trains, seats, and ticket bookings with SQLite persistence.

- ✨ Add, view, search, and delete trains
- 🎟️ Book and cancel tickets
- 💺 Live seat availability and summary (Window / Aisle / Middle)
- 🧮 Smart seat auto-allocation
- 🗄️ Durable local storage using SQLite
- 🧰 Single cached DB connection for efficient Streamlit reruns

---

## 🔗 Live App

My app is already deployed!
- Live URL: https://railway-reservation-system-saif-063.streamlit.app/  ← replace with your URL if you want it visible here

---

## 👀 Preview

![image](https://github.com/MdSaifAli063/Railway-Reservation-System/blob/39e008478084a8f1c9e230c583564561e66d09e9/Screenshot%202025-09-22%20005406.png)

---

## 🏆 Certificates

Here are some of the certifications I've earned that showcase my skills and learning journey:

![image](https://github.com/MdSaifAli063/Railway-Reservation-System/blob/88cf9c63af81c420b544f6983bf99a3d237f7598/Screenshot%202025-09-22%20012829.png)

---


## 🧭 Features Overview

- ➕ Add Train: create a train and auto-seed its seats
- 📋 View Trains: list all trains
- 🔎 Search Train:
  - by Train Number
  - by Source & Destination
- 🗑️ Delete Train: removes the train and its seat table
- 🎫 Book Ticket: auto-assigns the next available seat of chosen type
- ❌ Cancel Ticket: frees a booked seat
- 🪑 View Seats:
  - per-train seat table with status
  - summary by seat type (Available / Booked)

---

## 📂 Project Structure

- main.py — Streamlit app (UI + DB + seat logic)
- railway_system.db — SQLite database auto-created at first run (same folder as app)

No other files are required to run the app.

---

## 🚀 Run Locally

Prerequisites:
- Python 3.9+
- pip

1) Clone and enter the project
- Place main.py at project root (as in this repo)

2) Create a virtual environment (recommended)
- python -m venv .venv
- source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3) Install dependencies
- pip install streamlit pandas

4) Start the app
- streamlit run main.py

The app will open at http://localhost:8501

Note: The SQLite DB file railway_system.db will be created on first run.

---

## 🧠 How It Works

- Database
  - SQLite with the following entities:
    - users(username, password) — placeholder table
    - employees(employee_id, password, designation) — placeholder table
    - trains(train_number, train_name, departure_date, starting_destination, ending_destination)
      - train_number is uniquely indexed
    - seats per train in a dedicated table: seats_{train_number}
      - fields: seat_number, seat_type, booked, passenger_name, passenger_age, passenger_gender

- Seat Seeding
  - When a new train is added, the app creates seats_{train_number} with 50 seats by default
  - Seat types are assigned by seat number modulo 10:
    - Window: 0, 4, 5, 9
    - Aisle: 2, 3, 6, 7
    - Middle: 1, 8

- Seat Allocation
  - The app picks the lowest-numbered available seat of the selected seat type

- Streamlit Caching
  - Uses st.cache_resource for a single SQLite connection across reruns

---

## 🛠️ Usage Tips

- Adding Trains
  - Train number must be alphanumeric with underscores only (A–Z, a–z, 0–9, _)
  - Departure date stored as ISO (YYYY-MM-DD)

- Booking Tickets
  - Choose seat type to let the system pick the next available seat of that type

- Cancel Tickets
  - Provide train number and seat number to clear the seat

- Viewing Seats
  - See both summary by seat type and the full seat table

---

## ⚙️ Configuration & Customization

- Change the default seat count per train:
  - In main.py, function ensure_seat_table(train_number, total_seats=50)
  - Update total_seats to your desired default (e.g., 72)

- Train Number Sanitization
  - Only letters, digits, and underscores are permitted to prevent unsafe table names

---

## 🧹 Maintenance

- Reset the database (destructive)
  - Stop the app
  - Delete railway_system.db
  - Start the app to recreate fresh tables

- Backups
  - Copy railway_system.db while the app is stopped

- Handling Duplicates
  - If you had prior data without unique train numbers, the index creation may warn you
  - Clean duplicates by removing conflicting rows

---

## 🔒 Security Notes

- No authentication UI is currently wired (users/employees tables are placeholders)
- Passwords are stored in plaintext — do not use this as-is in production
- For a production system:
  - Add user authentication
  - Hash passwords (e.g., bcrypt/argon2)
  - Validate all user inputs thoroughly
  - Implement roles (admin vs. operator)
  - Add proper logging and error handling

---

## 🧪 Testing Ideas

- Add train and verify seats_{train_number} table is created with seeded rows
- Book a Window seat until none remain, verify failure message
- Cancel a seat and rebook to see reallocation at the lowest seat number
- Delete a train and confirm both train record and seats table are removed

---

## ❗ Known Limitations

- Each train creates its own seats_{train_number} table (simple, but not ideal for very large scale)
- No concurrency control beyond SQLite defaults
- No pagination for large datasets
- No authentication flows included

---

## 🔮 Future Enhancements

- Proper auth (login, roles)
- Centralized seats table with foreign keys instead of dynamic per-train tables
- Support for multiple classes/compartments
- Coach/berth layout visualization
- Export reports (CSV)
- CI/CD with tests and pre-commit hooks

---

## 👤 Author

- You! Maintain and customize as needed for your deployment

---

## 📜 License

This project is licensed under the MIT License — see the LICENSE file for details.
