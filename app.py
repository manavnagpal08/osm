# ----------------------------------------
# ADMIN SIDEBAR RENDERING (SAFE VERSION)
# ----------------------------------------
if role == "admin":

    st.sidebar.markdown(
        "<div class='sidebar-title'>🧭 Navigation</div>",
        unsafe_allow_html=True
    )

    # Fix: if active_menu not set OR invalid, reset default
    if "active_menu" not in st.session_state or st.session_state.active_menu not in admin_menu:
        st.session_state.active_menu = "Create Order"

    # Handle URL param click
    menu_param = st.query_params.get("menu", [None])[0]

    if menu_param:
        menu_param = menu_param.replace("%20", " ")  # decode spaces

        # Fix: ensure URL value is valid
        if menu_param in admin_menu:
            st.session_state.active_menu = menu_param

    # Render menu items
    for label, (icon, file) in admin_menu.items():

        active_class = (
            "menu-button-active"
            if st.session_state.active_menu == label
            else "menu-button"
        )

        html_button = f"""
            <button class="{active_class}" onclick="window.location.href='?menu={label}'">
                {icon} &nbsp; {label}
            </button>
        """

        st.sidebar.markdown(html_button, unsafe_allow_html=True)

    # FIX: guaranteed safe
    selected_label = st.session_state.active_menu
    selected_file = admin_menu[selected_label][1]

    load_page(selected_file)
