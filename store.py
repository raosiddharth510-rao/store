# app.py
# Requirements (put these in requirements.txt):
# streamlit
# pandas
# numpy
# Pillow
# pyzbar
# python-dateutil
# On Debian/Ubuntu: sudo apt-get install libzbar0

import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta

# Optional QR decode libs
try:
    from pyzbar.pyzbar import decode as qr_decode
    from PIL import Image
    QR_LIBS_AVAILABLE = True
except Exception:
    try:
        from PIL import Image
    except Exception:
        pass
    QR_LIBS_AVAILABLE = False

# -------------------------
# Page + Theme
# -------------------------
st.set_page_config(page_title="Retail Store App", layout="wide")

dark_css = """
<style>
body { background-color:#111 !important; color:#eee !important; }
[data-testid="stSidebar"] { background-color:#1a1a1a !important; }
.stButton>button { background:#333 !important; color:#fff !important; border-radius:8px; }
input, textarea, select { background:#222 !important; color:#fff !important; }
</style>
"""
st.markdown(dark_css, unsafe_allow_html=True)

# -------------------------
# Config & Files
# -------------------------
DATA_FOLDER = "data"
PRODUCT_FILE = f"{DATA_FOLDER}/products.csv"
BILL_FILE = f"{DATA_FOLDER}/bills.csv"
FEEDBACK_FILE = f"{DATA_FOLDER}/feedback.csv"
PRODUCT_FEEDBACK_FILE = f"{DATA_FOLDER}/product_feedback.csv"
ADMIN_FILE = f"{DATA_FOLDER}/admin.json"

# default admin accounts (only created if admin.json missing)
DEFAULT_ADMINS = {"siddharth": "84331800", "priyanshu": "84331800"}

# -------------------------
# Ensure data folder + init csvs + admin json
# -------------------------
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)


def init_csv(path, columns):
    if not os.path.exists(path):
        df = pd.DataFrame(columns=columns)
        df.to_csv(path, index=False)
    return pd.read_csv(path)


products = init_csv(PRODUCT_FILE, ["product_id", "name", "price", "cost_price", "quantity", "expiry"])
bills = init_csv(BILL_FILE, ["bill_id", "product_name", "price", "quantity", "total", "date", "payment_method"])
feedback = init_csv(FEEDBACK_FILE, ["customer_name", "rating", "message", "date"])
product_feedback = init_csv(PRODUCT_FEEDBACK_FILE, ["product_id", "bill_id", "customer_name", "rating", "message", "date"])


def load_admins():
    if not os.path.exists(ADMIN_FILE):
        with open(ADMIN_FILE, "w") as f:
            json.dump({"users": DEFAULT_ADMINS}, f)
        return DEFAULT_ADMINS.copy()
    try:
        with open(ADMIN_FILE, "r") as f:
            data = json.load(f)
            users = data.get("users", {})
            # ensure defaults exist
            for u, p in DEFAULT_ADMINS.items():
                if u not in users:
                    users[u] = p
            return users
    except Exception:
        return DEFAULT_ADMINS.copy()


def save_admins(users: dict):
    with open(ADMIN_FILE, "w") as f:
        json.dump({"users": users}, f)


admin_users = load_admins()

# -------------------------
# Data load/save helpers
# -------------------------
def load_all():
    p = pd.read_csv(PRODUCT_FILE)
    b = pd.read_csv(BILL_FILE)
    f = pd.read_csv(FEEDBACK_FILE)
    pf = pd.read_csv(PRODUCT_FEEDBACK_FILE)

    # migrate columns if missing
    if "cost_price" not in p.columns:
        p["cost_price"] = 0.0

    # safe types
    p["price"] = pd.to_numeric(p["price"], errors="coerce").fillna(0.0)
    p["cost_price"] = pd.to_numeric(p["cost_price"], errors="coerce").fillna(0.0)
    p["quantity"] = pd.to_numeric(p["quantity"], errors="coerce").fillna(0).astype(int)
    p["expiry"] = pd.to_datetime(p["expiry"], errors="coerce")

    if not b.empty:
        if "bill_id" in b.columns:
            b["bill_id"] = pd.to_numeric(b["bill_id"], errors="coerce").fillna(0).astype(int)
        b["price"] = pd.to_numeric(b["price"], errors="coerce").fillna(0.0)
        b["quantity"] = pd.to_numeric(b["quantity"], errors="coerce").fillna(0).astype(int)
        b["total"] = pd.to_numeric(b["total"], errors="coerce").fillna(0.0)

    return p, b, f, pf


def save_products(df):
    df.to_csv(PRODUCT_FILE, index=False)


def save_bills(df):
    df.to_csv(BILL_FILE, index=False)


def save_feedback(df):
    df.to_csv(FEEDBACK_FILE, index=False)


def save_product_feedback(df):
    df.to_csv(PRODUCT_FEEDBACK_FILE, index=False)


# load current data
products, bills, feedback, product_feedback = load_all()

# -------------------------
# Auth
# -------------------------
def login_page():
    st.title("🔐 Admin Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        uname = username.strip().lower()
        if uname and uname in admin_users and password == admin_users[uname]:
            st.session_state.auth = True
            st.session_state.admin_user = uname
            st.success("Login successful!")
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")


# -------------------------
# Sidebar: Mode & Menu
# -------------------------
def sidebar_menu():
    mode = st.sidebar.selectbox("Mode", ["Customer", "Admin"])
    st.session_state.mode = mode
    if "auth" not in st.session_state:
        st.session_state.auth = False

    if mode == "Admin":
        menu = st.sidebar.radio("Navigation", ["Dashboard", "Inventory", "QR Scanner", "Sales Report", "View Feedback", "Admin Settings", "Logout"])
    else:
        menu = st.sidebar.radio("Navigation", ["Shop", "Cart", "My Feedback", "Scan QR (Customer)"])
    return menu


# -------------------------
# Inventory alerts
# -------------------------
def inventory_alerts(df):
    st.subheader("🚨 Inventory Alerts")
    if df.empty:
        st.info("No products available.")
        return
    df2 = df.copy()
    df2["expiry"] = pd.to_datetime(df2["expiry"], errors="coerce")
    today = datetime.today()
    expired = df2[df2["expiry"].notna() & (df2["expiry"] < today)]
    expiring_soon = df2[df2["expiry"].notna() & (df2["expiry"] >= today) & (df2["expiry"] <= today + timedelta(days=7))]
    low_stock = df2[df2["quantity"] <= 5]
    out_of_stock = df2[df2["quantity"] == 0]

    if not expired.empty:
        st.error("❌ EXPIRED PRODUCTS")
        st.dataframe(expired)
    if not out_of_stock.empty:
        st.error("⛔ OUT OF STOCK")
        st.dataframe(out_of_stock)
    if not low_stock.empty:
        st.warning("⚠️ LOW STOCK (≤5)")
        st.dataframe(low_stock)
    if not expiring_soon.empty:
        st.warning("⌛ EXPIRING SOON (within 7 days)")
        st.dataframe(expiring_soon)


# -------------------------
# Admin dashboard
# -------------------------
def admin_dashboard():
    st.title("📊 Admin Dashboard")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Products", len(products))
    col2.metric("Total Bills", len(bills))
    col3.metric("Total Product Feedback", len(product_feedback))
    st.markdown("---")
    inventory_alerts(products)

    st.markdown("---")
    st.markdown("### Quick Admin Actions")
    c1, c2, c3 = st.columns(3)
    if c1.button("Open Inventory"):
        st.session_state.sidebar_nav = "Inventory"
        st.experimental_rerun()
    if c2.button("Open Sales Report"):
        st.session_state.sidebar_nav = "Sales Report"
        st.experimental_rerun()
    if c3.button("Admin Settings"):
        st.session_state.sidebar_nav = "Admin Settings"
        st.experimental_rerun()


# -------------------------
# Inventory page (Admin)
# -------------------------
def inventory_page():
    global products
    st.title("📦 Inventory Management (Admin)")

    st.markdown("### Choose action")
    action = st.selectbox("Action", ["Add Product", "Edit Product", "Delete Product", "View Inventory"])

    if action == "Add Product":
        st.subheader("➕ Add Product")
        with st.form("add_product", clear_on_submit=True):
            pid = st.text_input("Product ID (unique)", key="add_pid")
            name = st.text_input("Product Name", key="add_name")
            price = st.number_input("Selling Price", min_value=0.0, format="%.2f", key="add_price")
            cost_price = st.number_input("Cost Price", min_value=0.0, format="%.2f", key="add_cost")
            qty = st.number_input("Quantity", min_value=0, step=1, key="add_qty")
            exp = st.date_input("Expiry Date (optional)", key="add_exp")
            submitted = st.form_submit_button("Add Product")
        if submitted:
            if not pid or not name:
                st.error("Product ID and Name are required.")
            else:
                pid_str = str(pid).strip()
                exists = products["product_id"].astype(str) == pid_str
                if exists.any():
                    st.error("Product with this ID already exists. Use Edit Product action to modify it.")
                else:
                    new = {"product_id": pid_str, "name": name.strip(), "price": float(price), "cost_price": float(cost_price), "quantity": int(qty), "expiry": str(exp)}
                    products = pd.concat([products, pd.DataFrame([new])], ignore_index=True)
                    save_products(products)
                    st.success("Product added and saved persistently.")
                    products, _, _, _ = load_all()

    elif action == "Edit Product":
        st.subheader("✏️ Edit Existing Product")
        if products.empty:
            st.info("No products to edit.")
        else:
            prod_ids = products["product_id"].astype(str).tolist()
            sel = st.selectbox("Select product to edit", prod_ids)
            if sel:
                item = products[products["product_id"].astype(str) == str(sel)].iloc[0]
                with st.form("edit_product"):
                    edit_name = st.text_input("Product Name", value=item["name"])
                    edit_price = st.number_input("Selling Price", min_value=0.0, format="%.2f", value=float(item["price"]))
                    edit_cost = st.number_input("Cost Price", min_value=0.0, format="%.2f", value=float(item.get("cost_price", 0.0)))
                    edit_qty = st.number_input("Quantity", min_value=0, step=1, value=int(item["quantity"]))
                    try:
                        exp_val = pd.to_datetime(item["expiry"]).date()
                    except Exception:
                        exp_val = None
                    edit_exp = st.date_input("Expiry Date (optional)", value=exp_val)
                    submitted = st.form_submit_button("Save Changes")
                if submitted:
                    idx = products[products["product_id"].astype(str) == str(sel)].index[0]
                    products.loc[idx, ["name", "price", "cost_price", "quantity", "expiry"]] = [
                        edit_name.strip(),
                        float(edit_price),
                        float(edit_cost),
                        int(edit_qty),
                        str(edit_exp),
                    ]
                    save_products(products)
                    st.success("Product updated and saved persistently.")
                    products, _, _, _ = load_all()

    elif action == "Delete Product":
        st.subheader("🗑️ Delete Product (requires confirmation)")
        if products.empty:
            st.info("No products to delete.")
        else:
            prod_ids = products["product_id"].astype(str).tolist()
            sel = st.selectbox("Select product to delete", prod_ids)
            confirm = st.checkbox("I confirm I want to permanently delete this product")
            if st.button("Delete Product"):
                if not sel:
                    st.error("Choose a product id")
                elif not confirm:
                    st.error("Please check the confirmation box to delete.")
                else:
                    products = products[products["product_id"].astype(str) != str(sel)]
                    save_products(products)
                    st.success("Deleted if it existed.")
                    products, _, _, _ = load_all()

    else:
        st.subheader("📋 Current Inventory")
        st.dataframe(products)


# -------------------------
# QR Scanner (Admin & Customer)
# -------------------------
def qr_scanner_view(admin_mode=False):
    st.title("🔍 QR Code Scanner")
    st.markdown("Point your camera to a product QR code (or upload a photo). QR should contain `product_id` or plain product_id text.")

    if not QR_LIBS_AVAILABLE:
        st.warning("QR decode libraries not available. To enable scanning with camera, install:\n`pip install pyzbar pillow` (and system zbar on Linux).")
        uploaded = st.file_uploader("Upload a photo of the QR code", type=["png", "jpg", "jpeg"])
        if uploaded:
            try:
                img = Image.open(uploaded)
                if QR_LIBS_AVAILABLE:
                    decoded = qr_decode(img)
                else:
                    decoded = []
                if decoded:
                    data = decoded[0].data.decode("utf-8")
                    st.success(f"QR data: {data}")
                    show_product_from_qr(data, admin_mode)
                else:
                    st.error("Could not decode QR from that image (pyzbar not available or image doesn't contain QR).")
            except Exception as e:
                st.error(f"Error decoding image: {e}")
        return

    img_file = st.camera_input("Scan QR with camera")
    if img_file:
        try:
            img = Image.open(img_file)
            decoded = qr_decode(img)
            if not decoded:
                st.error("No QR detected.")
                return
            data = decoded[0].data.decode("utf-8")
            st.success(f"QR data: {data}")
            show_product_from_qr(data, admin_mode)
        except Exception as e:
            st.error(f"Error decoding camera image: {e}")


def show_product_from_qr(qr_text, admin_mode=False):
    pid = None
    try:
        parsed = json.loads(qr_text)
        pid = parsed.get("product_id") or parsed.get("id")
    except Exception:
        pid = str(qr_text).strip()

    if not pid:
        st.error("QR did not contain a product id.")
        return

    match = products[products["product_id"].astype(str) == str(pid)]
    if match.empty:
        st.info("Product not found in inventory.")
        st.write("Scanned product id:", pid)
        return
    prod = match.iloc[0]
    st.markdown(f"### {prod['name']} (ID: {prod['product_id']})")
    st.write("Price:", prod["price"])
    st.write("Cost Price:", prod["cost_price"])
    st.write("Quantity:", prod["quantity"])
    st.write("Expiry:", prod["expiry"])
    if admin_mode:
        if st.button("Open Product Sales Report"):
            st.session_state.open_product_report = str(pid)
            st.experimental_rerun()


# -------------------------
# Shop (Customer) - confirmation before showing Add to cart
# -------------------------
def shop_page():
    st.title("🛒 Shop")
    if products.empty:
        st.info("No products available.")
        return

    for _, row in products.iterrows():
        pid = str(row["product_id"])
        cols = st.columns([1, 3, 1, 1])
        cols[0].markdown(f"**{pid}**")
        cols[1].markdown(f"**{row['name']}**\n\nPrice: ₹{row['price']}\nQty: {row['quantity']}\nExpiry: {row['expiry']}")
        want_key = f"wantbuy_{pid}"
        if "cart" not in st.session_state:
            st.session_state.cart = {}
        want = cols[2].checkbox("I want to buy this", key=want_key)
        if want:
            max_qty = int(max(row["quantity"], 1))
            qty_key = f"qty_{pid}"
            qty = cols[2].number_input(f"Qty to buy (max {max_qty})", min_value=1, max_value=max_qty, value=1, key=qty_key)
            if cols[3].button("Add to cart", key=f"add_{pid}"):
                if row["quantity"] <= 0:
                    st.warning("Out of stock.")
                else:
                    add_to_cart(pid, qty)
                    st.success(f"Added {qty} x {row['name']} to cart.")
        else:
            cols[2].write("")  # placeholder to keep layout tidy


def add_to_cart(pid, qty):
    if "cart" not in st.session_state:
        st.session_state.cart = {}
    pid = str(pid)
    # refresh products to be safe
    global products
    products, _, _, _ = load_all()
    match = products[products["product_id"].astype(str) == pid]
    if match.empty:
        st.error("Product no longer exists.")
        return
    prod = match.iloc[0]

    available = int(prod["quantity"])
    if int(qty) > available:
        st.error(f"Requested {qty} but only {available} available.")
        return

    if pid in st.session_state.cart:
        st.session_state.cart[pid]["qty"] += int(qty)
    else:
        st.session_state.cart[pid] = {"product_id": pid, "name": prod["name"], "price": float(prod["price"]), "qty": int(qty)}
    st.session_state.cart = st.session_state.cart


# -------------------------
# Cart & Checkout
# -------------------------
def cart_page():
    global bills, products
    st.title("🧾 Your Cart")
    cart = st.session_state.get("cart", {})
    if not cart:
        st.info("Cart is empty.")
        return

    rows = []
    for pid, item in cart.items():
        rows.append({
            "product_id": pid,
            "name": item["name"],
            "price": item["price"],
            "qty": item["qty"],
            "line_total": item["price"] * item["qty"]
        })
    df = pd.DataFrame(rows)
    st.dataframe(df)

    st.markdown("### Update quantities / remove items")
    for pid, item in list(cart.items()):
        cols = st.columns([2, 1, 1])
        cols[0].write(f"**{item['name']}** (ID: {pid})")
        new_qty = cols[1].number_input(f"update_{pid}", min_value=0, value=item["qty"], key=f"update_{pid}")
        if cols[2].button("Apply", key=f"apply_{pid}"):
            if new_qty <= 0:
                del st.session_state.cart[pid]
            else:
                st.session_state.cart[pid]["qty"] = int(new_qty)
            st.experimental_rerun()

    total = df["line_total"].sum()
    st.markdown(f"**Total: ₹{total:.2f}**")

    payment_method = st.radio("Payment Method", ["Cash on Delivery", "Online Payment"])
    if st.button("Checkout"):
        # validate stock
        products, bills, feedback, product_feedback = load_all()
        for pid, item in st.session_state.get("cart", {}).items():
            match = products[products["product_id"].astype(str) == pid]
            if match.empty:
                st.error(f"Product {item['name']} not available.")
                return
            available = int(match.iloc[0]["quantity"])
            if item["qty"] > available:
                st.error(f"Not enough stock for {item['name']}. Available: {available}")
                return

        if payment_method == "Online Payment":
            st.info("Simulating online payment... (demo only)")

        existing_ids = bills["bill_id"].tolist() if "bill_id" in bills.columns and not bills.empty else []
        next_bill_id = (max(existing_ids) + 1) if existing_ids else 1

        for pid, item in st.session_state.get("cart", {}).items():
            new_bill = {
                "bill_id": next_bill_id,
                "product_name": item["name"],
                "price": item["price"],
                "quantity": item["qty"],
                "total": item["price"] * item["qty"],
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "payment_method": payment_method
            }
            bills = pd.concat([bills, pd.DataFrame([new_bill])], ignore_index=True)
            next_bill_id += 1

            idx = products[products["product_id"].astype(str) == pid].index[0]
            products.loc[idx, "quantity"] = int(products.loc[idx, "quantity"]) - int(item["qty"])

        save_bills(bills)
        save_products(products)
        st.success("Purchase completed! Thank you.")
        st.session_state.cart = {}
        st.experimental_rerun()


# -------------------------
# Product-level feedback
# -------------------------
def my_feedback_page():
    global product_feedback
    st.title("✍️ Give Feedback on Products")
    st.markdown("Submit feedback for a product (optionally include bill id).")
    pid = st.text_input("Product ID")
    bill_id = st.text_input("Optional Bill ID")
    cname = st.text_input("Your Name")
    rating = st.slider("Rating (1-5)", 1, 5)
    msg = st.text_area("Message")
    if st.button("Submit Product Feedback"):
        if not pid or not cname:
            st.error("Product ID and your name required.")
        else:
            new = {
                "product_id": str(pid),
                "bill_id": bill_id,
                "customer_name": cname,
                "rating": rating,
                "message": msg,
                "date": datetime.now().strftime("%Y-%m-%d")
            }
            product_feedback = pd.concat([product_feedback, pd.DataFrame([new])], ignore_index=True)
            save_product_feedback(product_feedback)
            st.success("Thank you — feedback saved!")

    st.markdown("### Recent product feedback")
    st.dataframe(product_feedback.tail(50))


# -------------------------
# View feedback (admin)
# -------------------------
def view_feedback_admin():
    st.title("📑 All Product Feedback (Admin)")
    st.dataframe(product_feedback)


# -------------------------
# Sales & Profit (Admin)
# -------------------------
def sales_report():
    st.title("💰 Sales & Profit Report (Admin)")
    if bills.empty:
        st.info("No sales yet.")
        return

    st.markdown("### All Bills")
    st.dataframe(bills)

    agg = bills.groupby("product_name").agg({"quantity": "sum", "total": "sum"}).reset_index()
    st.markdown("### Sales by Product")
    st.dataframe(agg)

    merged = agg.merge(products[["name", "cost_price"]].rename(columns={"name": "product_name"}), on="product_name", how="left")
    merged["cost_price"] = merged["cost_price"].fillna(0.0)
    merged["profit"] = merged["total"] - (merged["quantity"] * merged["cost_price"])
    st.markdown("### Profit by Product")
    st.dataframe(merged[["product_name", "quantity", "total", "cost_price", "profit"]])

    st.markdown("---")
    pid = st.text_input("Enter Product ID (for detail)")
    if st.button("Show Product Detail"):
        if not pid:
            st.error("Enter a product id")
        else:
            m = products[products["product_id"].astype(str) == str(pid)]
            if m.empty:
                st.info("No such product.")
            else:
                p = m.iloc[0]
                st.write("Product:", p["name"])
                st.write("Current quantity:", p["quantity"])
                pb = bills[bills["product_name"] == p["name"]]
                st.write(f"Sales count: {len(pb)}")
                st.dataframe(pb)
                pf = product_feedback[product_feedback["product_id"].astype(str) == str(pid)]
                st.write("Feedback for this product:")
                st.dataframe(pf)


# -------------------------
# Admin Settings (password updates, manage admins)
# -------------------------
def admin_settings():
    st.title("🔧 Admin Settings")
    st.write(f"Logged in as: **{st.session_state.get('admin_user', 'unknown')}**")
    st.markdown("### Choose admin operation")
    op = st.selectbox("Operation", ["Change Password", "Manage Admin Users", "View Admins"])
    global admin_users

    if op == "Change Password":
        st.subheader("Change your password")
        user = st.session_state.get("admin_user", "")
        curr = st.text_input("Current password", type="password")
        new = st.text_input("New password", type="password")
        new2 = st.text_input("Confirm new password", type="password")
        if st.button("Update Password"):
            if not user:
                st.error("No admin user in session.")
            elif admin_users.get(user) != curr:
                st.error("Current password is incorrect.")
            elif not new or new != new2:
                st.error("New passwords do not match or are empty.")
            else:
                admin_users[user] = new
                save_admins(admin_users)
                st.success("Password updated successfully.")
    elif op == "Manage Admin Users":
        st.subheader("Add or Remove admin accounts")
        col1, col2 = st.columns(2)
        add_user = col1.text_input("New admin username")
        add_pass = col1.text_input("New admin password", type="password")
        if col1.button("Add admin"):
            if not add_user or not add_pass:
                st.error("Provide username and password.")
            else:
                uname = add_user.strip().lower()
                if uname in admin_users:
                    st.error("User already exists.")
                else:
                    admin_users[uname] = add_pass
                    save_admins(admin_users)
                    st.success(f"Added admin {uname}.")

        rem_user = col2.selectbox("Remove admin user", [u for u in admin_users.keys()])
        if col2.button("Remove admin"):
            if rem_user:
                if rem_user == st.session_state.get("admin_user"):
                    st.error("You cannot remove the account you are currently logged in with.")
                else:
                    admin_users.pop(rem_user, None)
                    save_admins(admin_users)
                    st.success(f"Removed admin {rem_user}.")

    else:
        st.subheader("Configured admin users")
        df = pd.DataFrame([{"username": u, "password_set": bool(p)} for u, p in admin_users.items()])
        st.dataframe(df)


# -------------------------
# Main
# -------------------------
def main():
    global products, bills, feedback, product_feedback, admin_users

    if "auth" not in st.session_state:
        st.session_state.auth = False
    if "mode" not in st.session_state:
        st.session_state.mode = "Customer"

    # reload persisted data & admins
    admin_users = load_admins()
    products, bills, feedback, product_feedback = load_all()

    menu = sidebar_menu()

    # allow quick nav from dashboard buttons
    if "sidebar_nav" in st.session_state:
        menu = st.session_state.pop("sidebar_nav")

    if st.session_state.mode == "Admin" and not st.session_state.auth:
        login_page()
        return

    if st.session_state.mode == "Admin":
        if menu == "Dashboard":
            admin_dashboard()
        elif menu == "Inventory":
            inventory_page()
        elif menu == "QR Scanner":
            qr_scanner_view(admin_mode=True)
        elif menu == "Sales Report":
            sales_report()
        elif menu == "View Feedback":
            view_feedback_admin()
        elif menu == "Admin Settings":
            admin_settings()
        elif menu == "Logout":
            st.session_state.auth = False
            st.success("Logged out")
            st.experimental_rerun()
    else:
        if menu == "Shop":
            shop_page()
        elif menu == "Cart":
            cart_page()
        elif menu == "My Feedback":
            my_feedback_page()
        elif menu == "Scan QR (Customer)":
            qr_scanner_view(admin_mode=False)


if __name__ == "__main__":
    main()
