import re
from datetime import date
import sqlite3
import pandas as pd
import streamlit as st


# ---------------------------
# Database connection and setup
# ---------------------------

@st.cache_resource
def get_connection():
    """
    Create and cache a single SQLite connection for the Streamlit app lifecycle.
    Using check_same_thread=False to cooperate with Streamlit reruns.
    """
    conn = sqlite3.connect("railway_system.db", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """
    Initialize required tables and indexes.
    """
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            employee_id TEXT PRIMARY KEY,
            password TEXT,
            designation TEXT
        )
    """)

    # Keep trains schema compatible with existing DB; add a unique index on train_number
    c.execute("""
        CREATE TABLE IF NOT EXISTS trains (
            train_number TEXT,
            train_name TEXT,
            departure_date TEXT,
            starting_destination TEXT,
            ending_destination TEXT
        )
    """)

    # Try to enforce uniqueness of train_number even if table already existed.
    try:
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_trains_train_number ON trains(train_number)")
    except sqlite3.OperationalError as e:
        # If duplicates in existing data, index creation will fail.
        st.warning(f"Could not enforce unique train numbers due to existing duplicates: {e}")

    conn.commit()


# ---------------------------
# Helpers
# ---------------------------

def sanitize_train_number(train_number: str) -> str:
    """
    Ensure train_number is safe for use in dynamic table names.
    Allow only letters, digits, and underscores.
    """
    if not isinstance(train_number, str) or not re.fullmatch(r"[A-Za-z0-9_]+", train_number):
        raise ValueError("Train number must contain only letters, digits, or underscores.")
    return train_number


def seat_table_name(train_number: str) -> str:
    """
    Get the seat table name for a given train number.
    """
    tn = sanitize_train_number(train_number)
    return f"seats_{tn}"


def categorize_seat(seat_number: int) -> str:
    """
    Categorize seat number by type (Window, Aisle, Middle).
    """
    mod = seat_number % 10
    if mod in (0, 4, 5, 9):
        return "Window"
    elif mod in (2, 3, 6, 7):
        return "Aisle"
    else:
        return "Middle"


def ensure_seat_table(train_number: str, total_seats: int = 50):
    """
    Ensure the seats table exists and seed it only if empty.
    """
    conn = get_connection()
    c = conn.cursor()
    table = seat_table_name(train_number)

    c.execute(f"""
        CREATE TABLE IF NOT EXISTS {table} (
            seat_number INTEGER PRIMARY KEY,
            seat_type TEXT NOT NULL,
            booked INTEGER NOT NULL DEFAULT 0,
            passenger_name TEXT,
            passenger_age INTEGER,
            passenger_gender TEXT
        )
    """)

    # Seed seats only when table is empty
    count = c.execute(f"SELECT COUNT(1) FROM {table}").fetchone()[0]
    if count == 0:
        rows = []
        for i in range(1, total_seats + 1):
            rows.append((i, categorize_seat(i), 0, None, None, None))
        c.executemany(
            f"INSERT INTO {table}(seat_number, seat_type, booked, passenger_name, passenger_age, passenger_gender) "
            f"VALUES (?, ?, ?, ?, ?, ?)",
            rows
        )
        conn.commit()


# ---------------------------
# Data access functions
# ---------------------------

def add_train(train_number, train_name, departure_date, starting_destination, ending_destination):
    conn = get_connection()
    c = conn.cursor()

    # Basic validation
    if not train_number or not train_name or not starting_destination or not ending_destination:
        st.error("All fields are required.")
        return

    # Sanitize name used for seat table
    try:
        sanitize_train_number(train_number)
    except ValueError as ve:
        st.error(str(ve))
        return

    # Normalize date to ISO string
    if isinstance(departure_date, date):
        departure_date_str = departure_date.isoformat()
    else:
        departure_date_str = str(departure_date)

    # Prevent duplicate trains
    exists = c.execute("SELECT 1 FROM trains WHERE train_number = ?", (train_number,)).fetchone()
    if exists:
        st.error(f"Train with number {train_number} already exists.")
        return

    c.execute(
        "INSERT INTO trains (train_number, train_name, departure_date, starting_destination, ending_destination) "
        "VALUES (?, ?, ?, ?, ?)",
        (train_number, train_name, departure_date_str, starting_destination, ending_destination),
    )
    conn.commit()

    # Create and seed the seat table
    ensure_seat_table(train_number)
    st.success(f"Train {train_name} ({train_number}) added successfully.")


def delete_train(train_number, departure_date):
    conn = get_connection()
    c = conn.cursor()

    # Normalize date
    if isinstance(departure_date, date):
        departure_date_str = departure_date.isoformat()
    else:
        departure_date_str = str(departure_date)

    row = c.execute("SELECT train_number, departure_date FROM trains WHERE train_number = ?", (train_number,)).fetchone()
    if not row:
        st.error(f"No such train with number {train_number}.")
        return

    # Verify date matches
    if row[1] != departure_date_str:
        st.error("Departure date does not match the stored record for this train.")
        return

    # Drop seats table safely
    try:
        table = seat_table_name(train_number)
        c.execute(f"DROP TABLE IF EXISTS {table}")
    except ValueError as ve:
        st.error(str(ve))
        return

    c.execute("DELETE FROM trains WHERE train_number = ?", (train_number,))
    conn.commit()
    st.success(f"Train {train_number} has been deleted.")


def allocate_next_available_seat(train_number, seat_type):
    conn = get_connection()
    c = conn.cursor()

    ensure_seat_table(train_number)
    table = seat_table_name(train_number)

    row = c.execute(
        f"SELECT seat_number FROM {table} WHERE booked = 0 AND seat_type = ? ORDER BY seat_number ASC LIMIT 1",
        (seat_type,)
    ).fetchone()

    return int(row[0]) if row else None


def book_ticket(train_number, passenger_name, passenger_age, passenger_gender, seat_type):
    conn = get_connection()
    c = conn.cursor()

    train = c.execute("SELECT 1 FROM trains WHERE train_number = ?", (train_number,)).fetchone()
    if not train:
        st.error(f"No such train with number {train_number}.")
        return

    seat_number = allocate_next_available_seat(train_number, seat_type)
    if not seat_number:
        st.error(f"No available {seat_type} seats on this train.")
        return

    table = seat_table_name(train_number)
    c.execute(
        f"""
        UPDATE {table}
        SET booked = 1,
            passenger_name = ?,
            passenger_age = ?,
            passenger_gender = ?
        WHERE seat_number = ?
        """,
        (passenger_name.strip(), int(passenger_age), passenger_gender, int(seat_number)),
    )
    conn.commit()
    st.success(f"Successfully booked seat {seat_number} ({seat_type}) for {passenger_name}.")


def cancel_tickets(train_number, seat_number):
    conn = get_connection()
    c = conn.cursor()

    train = c.execute("SELECT 1 FROM trains WHERE train_number = ?", (train_number,)).fetchone()
    if not train:
        st.error(f"No such train with number {train_number}.")
        return

    table = seat_table_name(train_number)

    seat = c.execute(f"SELECT seat_number, booked FROM {table} WHERE seat_number = ?", (int(seat_number),)).fetchone()
    if not seat:
        st.error(f"Seat {seat_number} does not exist on train {train_number}.")
        return

    c.execute(
        f"""
        UPDATE {table}
        SET booked = 0,
            passenger_name = NULL,
            passenger_age = NULL,
            passenger_gender = NULL
        WHERE seat_number = ?
        """,
        (int(seat_number),),
    )
    conn.commit()
    st.success(f"Successfully cancelled seat {seat_number} on train {train_number}.")


def search_train_by_train_number(train_number):
    conn = get_connection()
    c = conn.cursor()
    return c.execute(
        "SELECT train_number, train_name, departure_date, starting_destination, ending_destination "
        "FROM trains WHERE train_number = ?",
        (train_number,),
    ).fetchone()


def search_trains_by_destinations(starting_destination, ending_destination):
    conn = get_connection()
    c = conn.cursor()
    return c.execute(
        "SELECT train_number, train_name, departure_date, starting_destination, ending_destination "
        "FROM trains WHERE starting_destination = ? AND ending_destination = ?",
        (starting_destination, ending_destination),
    ).fetchall()


def get_seats_df(train_number):
    conn = get_connection()
    c = conn.cursor()

    ensure_seat_table(train_number)
    table = seat_table_name(train_number)

    rows = c.execute(
        f"""
        SELECT seat_number, seat_type, booked, passenger_name, passenger_age, passenger_gender
        FROM {table}
        ORDER BY seat_number ASC
        """
    ).fetchall()

    df = pd.DataFrame(
        rows,
        columns=["Seat Number", "Seat Type", "Booked", "Passenger Name", "Passenger Age", "Passenger Gender"],
    )
    df["Status"] = df["Booked"].apply(lambda b: "Booked" if int(b) == 1 else "Available")
    return df


def get_seat_availability(train_number):
    conn = get_connection()
    c = conn.cursor()

    ensure_seat_table(train_number)
    table = seat_table_name(train_number)

    rows = c.execute(
        f"""
        SELECT seat_type,
               SUM(CASE WHEN booked = 0 THEN 1 ELSE 0 END) AS available,
               SUM(CASE WHEN booked = 1 THEN 1 ELSE 0 END) AS booked
        FROM {table}
        GROUP BY seat_type
        ORDER BY seat_type
        """
    ).fetchall()
    total = c.execute(f"SELECT COUNT(1) FROM {table}").fetchone()[0]
    return rows, total


# ---------------------------
# UI
# ---------------------------

def train_functions():
    st.title("Train Administrator")
    st.caption("Railway System (Streamlit + SQLite)")

    functions = st.sidebar.selectbox(
        "Select Train Functions",
        ["Add Train", "View Trains", "Search Train", "Delete Train", "Book Ticket", "Cancel Ticket", "View Seats"],
        index=0
    )

    if functions == "Add Train":
        st.header("Add New Train")
        with st.form(key="new_train_details"):
            train_number = st.text_input("Train Number (letters/digits/underscore only)")
            train_name = st.text_input("Train Name")
            departure_date = st.date_input("Date of Departure")
            starting_destination = st.text_input("Starting Destination")
            ending_destination = st.text_input("Ending Destination")
            submitted = st.form_submit_button("Add Train")

        if submitted:
            if train_number.strip() and train_name.strip() and starting_destination.strip() and ending_destination.strip():
                add_train(
                    train_number.strip(), train_name.strip(), departure_date,
                    starting_destination.strip(), ending_destination.strip()
                )
            else:
                st.error("Please fill in all required fields.")

    elif functions == "View Trains":
        st.header("All Trains")
        conn = get_connection()
        c = conn.cursor()
        trains = c.execute(
            "SELECT train_number, train_name, departure_date, starting_destination, ending_destination FROM trains"
        ).fetchall()
        if trains:
            df = pd.DataFrame(trains, columns=["Train Number", "Train Name", "Departure Date", "Start", "End"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No trains in the database.")

    elif functions == "Search Train":
        st.header("Train Details Search")

        st.subheader("Search by Train Number")
        train_number = st.text_input("Enter Train Number:")

        st.subheader("Search by Starting and Ending Destination")
        col1, col2 = st.columns(2)
        with col1:
            starting_destination = st.text_input("Starting Destination:")
        with col2:
            ending_destination = st.text_input("Ending Destination:")

        colA, colB = st.columns(2)
        with colA:
            if st.button("Search by Train Number"):
                if train_number.strip():
                    data = search_train_by_train_number(train_number.strip())
                    if data:
                        df = pd.DataFrame([data], columns=["Train Number", "Train Name", "Departure Date", "Start", "End"])
                        st.table(df)
                    else:
                        st.error(f"No train found with the train number: {train_number}")

        with colB:
            if st.button("Search by Destinations"):
                if starting_destination.strip() and ending_destination.strip():
                    data = search_trains_by_destinations(starting_destination.strip(), ending_destination.strip())
                    if data:
                        df = pd.DataFrame(data, columns=["Train Number", "Train Name", "Departure Date", "Start", "End"])
                        st.table(df)
                    else:
                        st.error("No trains found for the given source and destination.")

    elif functions == "Delete Train":
        st.header("Delete Train")
        train_number = st.text_input("Enter Train Number to delete:")
        departure_date = st.date_input("Enter Train Departure Date")
        if st.button("Delete Train"):
            if train_number.strip():
                delete_train(train_number.strip(), departure_date)
            else:
                st.error("Please enter a train number.")

    elif functions == "Book Ticket":
        st.header("Book Train Ticket")
        train_number = st.text_input("Enter Train Number:")
        seat_type = st.selectbox("Seat Type", ["Aisle", "Middle", "Window"], index=0)
        passenger_name = st.text_input("Passenger Name")
        passenger_age = st.number_input("Passenger Age", min_value=1, step=1)
        passenger_gender = st.selectbox("Passenger Gender", ["Male", "Female", "Other"], index=0)

        if st.button("Book Ticket"):
            if train_number.strip() and passenger_name.strip():
                book_ticket(train_number.strip(), passenger_name.strip(), passenger_age, passenger_gender, seat_type)
            else:
                st.error("Please enter both Train Number and Passenger Name.")

    elif functions == "Cancel Ticket":
        st.header("Cancel Ticket")
        train_number = st.text_input("Enter Train Number:")
        seat_number = st.number_input("Enter Seat Number", min_value=1, step=1)
        if st.button("Cancel Ticket"):
            if train_number.strip():
                cancel_tickets(train_number.strip(), int(seat_number))
            else:
                st.error("Please enter the Train Number.")

    elif functions == "View Seats":
        st.header("View Seats")
        train_number = st.text_input("Enter Train Number:")
        if st.button("Submit"):
            if train_number.strip():
                try:
                    df = get_seats_df(train_number.strip())
                    if df.empty:
                        st.info("No seats found. The seat table may not be initialized.")
                    else:
                        st.subheader("Seat Availability Summary")
                        summary_rows, total = get_seat_availability(train_number.strip())
                        if summary_rows:
                            summary_df = pd.DataFrame(summary_rows, columns=["Seat Type", "Available", "Booked"])
                            st.table(summary_df)
                            st.caption(f"Total seats: {total}")
                        st.subheader("Seats")
                        st.dataframe(df, use_container_width=True)
                except ValueError as ve:
                    st.error(str(ve))
            else:
                st.error("Please enter the Train Number.")


# ---------------------------
# App entry
# ---------------------------

def main():
    init_db()
    train_functions()
    # Do not close the cached connection manually; Streamlit manages the session.


if __name__ == "__main__":
    main()