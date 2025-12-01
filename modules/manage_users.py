import streamlit as st
import pandas as pd
# Assuming the firebase module provides read, update, and delete functions
# The 'delete' function is now imported and used since it's available in firebase.py
from firebase import read, update, delete 

# --- Constants ---
USER_ROLES = [
    "admin",
    "design",
    "printing",
    "lamination", # NEW DEPARTMENT ADDED
    "diecut",
    "assembly",
    "packaging",
]

# --- Helper Functions ---

def load_users():
    """Loads all users from the 'users' collection, handling the case where 'users' might not exist."""
    try:
        # Read all documents under the 'users' collection
        users_data = read("users") 
        if not users_data:
            # Check if there's any user data at all. We will rely on the main app logic to handle the default admin
            return pd.DataFrame() 

        # Convert the dictionary of users (keyed by username) into a list of dicts
        users_list = []
        for username, data in users_data.items():
            # Ensure the username is included in the dictionary for the DataFrame
            user_info = {"Username": username, "Role": data.get("role", "unknown")}
            # NOTE: We intentionally exclude the password from display
            users_list.append(user_info)
            
        return pd.DataFrame(users_list)
        
    except Exception as e:
        st.error(f"Error loading users: {e}")
        return pd.DataFrame()

# --- Callbacks for CRUD Operations ---

def create_user(username, password, role):
    """Creates a new user document."""
    if username.strip() == "" or password.strip() == "":
        st.error("Username and Password are required.")
        return False
        
    data = {
        "password": password,
        "role": role
    }
    # Use the username as the document ID
    update(f"users/{username}", data)
    st.success(f"User '{username}' created/updated successfully!")
    st.session_state["refresh_users"] = True # Trigger refresh
    return True

# Deletion functionality is now enabled
def delete_user_by_username(username):
    """Deletes a user document by username."""
    # Ensure the default admin cannot be deleted
    if username.lower() == "admin":
        st.error("The default 'admin' user cannot be deleted.")
        return

    try:
        delete(f"users/{username}")
        st.success(f"User '{username}' deleted successfully.")
        st.session_state["refresh_users"] = True # Trigger refresh
    except Exception as e:
        st.error(f"Failed to delete user {username}: {e}")

# --- Layout and UI Functions ---

def render_create_form():
    """Renders the form for creating new users."""
    st.subheader("➕ Create New User")
    
    with st.form("create_user_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            new_username = st.text_input("Username (Used as Login ID)", key="new_username")
        
        with col2:
            new_password = st.text_input("Password", type="password", key="new_password")
        
        new_role = st.selectbox("Assign Role", USER_ROLES, index=0, key="new_role")
        
        if st.form_submit_button("Create User"):
            # Call the creation logic
            create_user(new_username, new_password, new_role)
            # Re-run the app to update the list
            st.rerun()

def render_manage_table(df_users):
    """Renders the interactive table for managing existing users."""
    st.subheader("👥 Manage Existing Users")

    if df_users.empty:
        st.info("No users found in the database (apart from the default 'admin').")
        return

    # Set up the data editor for displaying and editing roles
    edited_df = st.data_editor(
        df_users,
        key="user_data_editor",
        column_config={
            "Username": st.column_config.TextColumn(
                "Username", help="User's login ID (Cannot be edited)"
            ),
            "Role": st.column_config.SelectboxColumn(
                "Role",
                help="User's access level and department",
                options=USER_ROLES,
                required=True,
            ),
        },
        hide_index=True,
        num_rows="dynamic", # Allow adding new rows (though we prefer the form for consistency)
        use_container_width=True
    )
    
    # Check for changes in the data editor
    if st.session_state["user_data_editor"]["edited_rows"]:
        st.warning("Changes detected! Remember to save your updates.")
        
        if st.button("Save Role Changes"):
            changes = st.session_state["user_data_editor"]["edited_rows"]
            
            for index, updates in changes.items():
                username = df_users.iloc[index]["Username"]
                new_role = updates.get("Role")
                
                # Check if only the role was updated
                if new_role is not None:
                    # In a real app, you'd fetch the password here to preserve it
                    st.info(f"Updating role for user: **{username}** to **{new_role}**...")
                    # NOTE: We assume 'read' gets the user data including the current password
                    
                    try:
                        current_user_data = read(f"users/{username}")
                        if current_user_data:
                            current_user_data["role"] = new_role
                            update(f"users/{username}", current_user_data)
                            st.success(f"Role for '{username}' updated successfully.")
                        else:
                            st.error(f"User data for {username} not found during update.")
                    except Exception as e:
                        st.error(f"Database error during role update for {username}: {e}")
                        
            st.rerun()

    st.markdown("---")
    st.subheader("❌ Delete Users")
    
    # User selection for deletion (Re-enabled)
    usernames = df_users['Username'].tolist()
    if usernames:
        # Filter out the 'admin' user from the deletion selection
        deletable_users = [u for u in usernames if u.lower() != "admin"]
        
        if deletable_users:
            user_to_delete = st.selectbox("Select User to Delete", deletable_users, key="delete_user_select")
            
            if user_to_delete:
                # Use a confirmation mechanism before deletion
                st.warning(f"Are you absolutely sure you want to delete user **{user_to_delete}**? This cannot be undone.", icon="⚠️")
                
                if st.button(f"Yes, Permanently Delete {user_to_delete}", type="primary"):
                    delete_user_by_username(user_to_delete)
                    st.rerun()
        else:
            st.info("The only user remaining is the protected 'admin' user.")

# --- Main Application Logic ---

# Check if refresh is needed (e.g., after a CRUD operation)
if "refresh_users" not in st.session_state:
    st.session_state["refresh_users"] = True

if st.session_state["refresh_users"]:
    # Load users only when explicitly asked to refresh
    df_users = load_users()
    st.session_state["current_users_df"] = df_users
    st.session_state["refresh_users"] = False # Reset flag

st.title("👤 User Management Portal")
st.markdown("Manage all system users, their access roles, and permissions within the OMS.")

st.markdown("---")

# 1. User Creation Section
with st.container(border=True):
    render_create_form()

st.markdown("---")

# 2. User Management Section
with st.container(border=True):
    # Pass the DataFrame loaded from the session state
    render_manage_table(st.session_state.get("current_users_df", pd.DataFrame()))
