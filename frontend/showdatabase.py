import os
import streamlit as st
from backend.auth import is_user_logged_in
from utils.database import get_db_connection, DB_PATH


def _fetch_table_rows(table_name):
    """Return all rows for a table as a list of dicts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def _fetch_table_count(table_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def _format_bytes(num_bytes):
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.1f} MB"


def database_status_page():
    if not is_user_logged_in():
        st.error("You need to be logged in to access this page.")
        st.stop()

    st.title("Database Status")
    st.caption("Debug view: shows all records from each table.")

    db_exists = os.path.exists(DB_PATH)
    db_size = os.path.getsize(DB_PATH) if db_exists else 0

    status_col1, status_col2 = st.columns(2)
    with status_col1:
        st.metric("Database file", DB_PATH)
    with status_col2:
        st.metric("Size", _format_bytes(db_size))

    if st.button("Refresh data"):
        st.rerun()

    tables = [
        ("users", "User accounts"),
        ("resume_analysis", "Resume analysis results"),
        ("job_recommendations", "Job recommendations"),
    ]

    for table_name, description in tables:
        try:
            count = _fetch_table_count(table_name)
            rows = _fetch_table_rows(table_name)
        except Exception as exc:  # pragma: no cover - defensive
            st.error(f"Failed to read {table_name}: {exc}")
            continue

        with st.expander(f"{table_name} ({count})", expanded=False):
            st.caption(description)

            # Clear table button for debugging
            clear_col, spacer_col = st.columns([1, 3])
            with clear_col:
                if st.button("Clear", key=f"clear_{table_name}"):
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute(f"DELETE FROM {table_name}")
                        conn.commit()
                        conn.close()
                        st.success(f"Cleared {table_name}.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Failed to clear {table_name}: {exc}")

            if rows:
                st.dataframe(rows, use_container_width=True)
            else:
                st.info("No rows in this table.")


if __name__ == "__main__":
    database_status_page()
