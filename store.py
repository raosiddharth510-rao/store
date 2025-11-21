# Retail Store App - Cleaned & Optimized
# Save file as: app.py
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
# Config
# -------------------------
ADMIN_USERS = ["siddharth", "priyanshu"]
ADMIN_PASS = "1802254"

DATA_FOLDER = "data"
PRODUCT_FILE = f"{DATA_FOLDER}/products.csv"
BILL_FILE = f"{DATA_FOLDER}/bills.csv"
FEEDBACK_FILE = f"{DATA_FOLDER}/feedback.csv"
PRODUCT_FEEDBACK_FILE = f"{DATA_FOLDER}/product_feedback.csv"

# -------------------------
# Helpers: ensure data folder + init csvs
# -------------------------
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)


def init_csv(path, columns):
    if not os.path.exists(path):
        df = pd.DataFrame(columns=columns)
        df.to_csv(path, index=False)
    return pd.read_csv(path)

# initialize files with expected columns
products = init_csv(PRODUCT_FILE, ["product_id", "name", "price", "cost_price", "quantity", "expiry"])
bills = init_csv(BILL_FILE, ["bill_id", "product_name", "price", "quantity", "total", "date", "payment_method"])
feedback = init_csv(FEEDBACK_FILE, ["customer_name", "rating", "message", "date"])
product_feedback = init_csv(PRODUCT_FEEDBACK_FILE, ["product_id", "bill_id", "customer_name", "rating", "message", "date"])


def load_all():
    p = pd.read_csv(PRODUCT_FILE)
    b = pd.read_csv(BILL_FILE)
    f = pd.read_csv(FEEDBACK_FILE)
    pf = pd.read_csv(PRODUCT_FEEDBACK_FILE)

    # migrate
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

products, bills, feedback, product_feedback = load_all()


def save_products(df):
    df.to_csv(PRODUCT_FILE, index=False)


def save_bills(df):
    df.to_csv(BILL_FILE, index=False)


def save_feedback(df):
    df.to_csv(FEEDBACK_FILE, index=False)


def save_product_feedback(df):
    df.to_csv(PRODUCT_FEEDBACK_FILE, index=False)

# -------------------------
# Auth
# -------------------------

def login_page():
    st.title("🔐 Admin Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username.lower() in ADMIN_USERS and password == ADMIN_PASS:
            st.session_state.auth = True
            st.session_state.admin_user = username.lower()
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
        menu = st.sidebar.radio("Navigation", ["Dashboard", "Inventory", "QR Scanner", "Sales Report", "View Feedback", "Logout"])
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

# -------------------------
# Inventory page (Admin)
# -------------------------

def inventory_page():
    global products
    st.title("📦 Inventory Management (Admin)")
    st.subheader("➕ Add / Update Product")

    with st.form("add_product", clear_on_submit=False):
        pid = st.text_input("Product ID (unique)")
        name = st.text_input("Product Name")
        price = st.number_input("Selling Price", min_value=0.0, format="%.2f")
        cost_price = st.number_input("Cost Price", min_value=0.0, format="%.2f")
        qty = st.number_input("Quantity", min_value=0, step=1)
        exp = st.date_input("Expiry Date (optional)")
        submitted = st.form_submit_button("Add / Update Product")

    if submitted:
        if not pid or not name:
            st.error("Product ID and Name are required.")
        else:
            pid_str = str(pid)
            exists = products["product_id"].astype(str) == pid_str
            if exists.any():
                idx = products[exists].index[0]
                products.loc[idx, ["name","price","cost_price","quantity","expiry"]] = [name, float(price), float(cost_price), int(qty), str(exp)]
                save_products(products)
                st.success("Product updated.")
            else:
                new = {"product_id": pid_str, "name": name, "price": float(price), "cost_price": float(cost_price), "quantity": int(qty), "expiry": str(exp)}
                products = pd.concat([products, pd.DataFrame([new])], ignore_index=True)
                save_products(products)
                st.success("Product added.")
            st.experimental_rerun()

    st.markdown("### Current Inventory")
    st.dataframe(products)

    st.markdown("### Delete Product")
    del_id = st.text_input("Product ID to delete")
    if st.button("Delete Product"):
        if del_id:
            products = products[products["product_id"].astype(str) != str(del_id)]
            save_products(products)
            st.success("Deleted if existed.")
            st.experimental_rerun()
        else:
            st.error("Enter product id")

# -------------------------
# QR Scanner (Admin & Customer)
# -------------------------

def qr_scanner_view(admin_mode=False):
    st.title("🔍 QR Code Scanner")
    st.markdown("Point your camera to a product QR code (or upload a photo). QR should contain `product_id` or plain product_id text.")

    if not QR_LIBS_AVAILABLE:
        st.warning("QR decode libraries not available. To enable scanning with camera, install:\n`pip install pyzbar pillow` (and system zbar on Linux).")
        uploaded = st.file_uploader("Upload a photo of the QR code", type=["png","jpg","jpeg"])
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
    import json
    pid = None
    try:
        parsed = json.loads(qr_text)
        pid = parsed.get("product_id") or parsed.get("id")
    except Exception:
        pid = qr_text.strip()

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
# Shop (Customer): browse, add to cart
# -------------------------

def shop_page():
    st.title("🛒 Shop")
    if products.empty:
        st.info("No products available.")
        return

    for _, row in products.iterrows():
        pid = str(row["product_id"])
        cols = st.columns([1,3,1,1])
        cols[0].markdown(f"**{pid}**")
        cols[1].markdown(f"**{row['name']}**\n\nPrice: ₹{row['price']}\nQty: {row['quantity']}\nExpiry: {row['expiry']}")
        max_qty = int(max(row["quantity"], 1))
        qty = cols[2].number_input(f"qty_{pid}", min_value=1, max_value=max_qty, value=1, key=f"qty_{pid}")
        if cols[3].button("Add to cart", key=f"add_{pid}"):
            if row["quantity"] <= 0:
                st.warning("Out of stock.")
            else:
                add_to_cart(pid, qty)
                st.success(f"Added {qty} x {row['name']} to cart.")


def add_to_cart(pid, qty):
    if "cart" not in st.session_state:
        st.session_state.cart = {}
    pid = str(pid)
    if pid in st.session_state.cart:
        st.session_state.cart[pid]["qty"] += int(qty)
    else:
        match = products[products["product_id"].astype(str) == pid]
        if match.empty:
            st.error("Product no longer exists.")
            return
        prod = match.iloc[0]
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
        cols = st.columns([2,1,1])
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

    agg = bills.groupby("product_name").agg({"quantity":"sum","total":"sum"}).reset_index()
    st.markdown("### Sales by Product")
    st.dataframe(agg)

    merged = agg.merge(products[["name","cost_price"]].rename(columns={"name":"product_name"}), on="product_name", how="left")
    merged["cost_price"] = merged["cost_price"].fillna(0.0)
    merged["profit"] = merged["total"] - (merged["quantity"] * merged["cost_price"])
    st.markdown("### Profit by Product")
    st.dataframe(merged[["product_name","quantity","total","cost_price","profit"]])

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
# Main
# -------------------------

def main():
    if "auth" not in st.session_state:
        st.session_state.auth = False
    if "mode" not in st.session_state:
        st.session_state.mode = "Customer"

    menu = sidebar_menu()

    if st.session_state.mode == "Admin" and not st.session_state.auth:
        login_page()
        return

    global products, bills, feedback, product_feedback
    products, bills, feedback, product_feedback = load_all()

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
