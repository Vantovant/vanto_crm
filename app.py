
import streamlit as st
import pandas as pd
from urllib.parse import quote_plus
from db import init_db, insert_contact, update_contact, delete_contact, fetch_contacts, insert_order, fetch_orders, insert_campaign, fetch_campaigns, insert_activity, fetch_activities, kpis

st.set_page_config(page_title="Vanto CRM", page_icon="📇", layout="wide")

# --- INIT DB ---
init_db()

# --- SIDEBAR NAV ---
st.sidebar.title("📇 Vanto CRM")
page = st.sidebar.radio("Navigate", ["Dashboard","Contacts","Orders","Campaigns","WhatsApp Tools","Import / Export","Help"])

# --- HELPERS ---
def wa_link(phone: str, text: str):
    p = "".join([c for c in phone if c.isdigit()])
    if p.startswith("0"):
        p = "27" + p[1:]
    encoded = quote_plus(text)
    return f"https://wa.me/{p}?text={encoded}"

STATUSES = ["New","Warm","Hot","Customer","Inactive"]

# --- DASHBOARD ---
if page == "Dashboard":
    st.header("📊 Dashboard")
    m = kpis()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Contacts", m["total_contacts"])
    c2.metric("Customers", m["customers"])
    c3.metric("🔥 Hot Leads", m["hot"])
    c4.metric("Orders", m["orders"])
    c5.metric("Revenue (Paid/Shipped/Delivered)", f"R{m['revenue']:.2f}")
    st.info("Tip: Import your Excel/CSV via **Import / Export** to populate this dashboard.")

# --- CONTACTS ---
elif page == "Contacts":
    st.header("👥 Contacts")
    with st.expander("➕ Add / Edit Contact", expanded=True):
        mode = st.radio("Mode", ["Add","Edit","Delete"], horizontal=True)
        if mode == "Add":
            with st.form("add_contact"):
                name = st.text_input("Name *")
                phone = st.text_input("Phone")
                email = st.text_input("Email")
                c1, c2, c3 = st.columns(3)
                with c1:
                    source = st.text_input("Source (e.g., GRW, NRM, Referral)")
                with c2:
                    interest = st.text_input("Interest (e.g., Luna, GRW, STP, NRM)")
                with c3:
                    status = st.selectbox("Status", STATUSES, index=0)
                c4, c5 = st.columns(2)
                with c4:
                    tags = st.text_input("Tags (comma-separated)")
                    username = st.text_input("Username (APLGO ID)")
                    password = st.text_input("Password")
                with c5:
                    assigned = st.text_input("Assigned (rep/owner)", value="Vanto")
                    action_needed = st.text_area("Action Needed", height=80)
                    action_taken = st.text_area("Action Taken", height=80)
                notes = st.text_area("Notes", height=80)
                submitted = st.form_submit_button("Save Contact")
                if submitted and name:
                    contact_id = insert_contact(dict(
                        name=name, phone=phone, email=email, source=source, interest=interest, status=status,
                        tags=tags, assigned=assigned, notes=notes, action_needed=action_needed, action_taken=action_taken,
                        username=username, password=password
                    ))
                    st.success(f"Saved contact #{contact_id}: {name}")
        elif mode == "Edit":
            rows = fetch_contacts()
            options = {f"#{r[0]} {r[1]} • {r[2] or ''}": r for r in rows}
            sel = st.selectbox("Select contact", list(options.keys())) if options else None
            if sel:
                r = options[sel]
                with st.form("edit_contact"):
                    name = st.text_input("Name *", r[1])
                    phone = st.text_input("Phone", r[2] or "")
                    email = st.text_input("Email", r[3] or "")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        source = st.text_input("Source", r[4] or "")
                    with c2:
                        interest = st.text_input("Interest", r[5] or "")
                    with c3:
                        status = st.selectbox("Status", STATUSES, index=STATUSES.index(r[6] or "New"))
                    c4, c5 = st.columns(2)
                    with c4:
                        tags = st.text_input("Tags", r[7] or "")
                        username = st.text_input("Username", r[12] or "")
                        password = st.text_input("Password", r[13] or "")
                    with c5:
                        assigned = st.text_input("Assigned", r[8] or "")
                        action_needed = st.text_area("Action Needed", r[10] or "", height=80)
                        action_taken = st.text_area("Action Taken", r[11] or "", height=80)
                    notes = st.text_area("Notes", r[9] or "", height=80)
                    submitted = st.form_submit_button("Update Contact")
                    if submitted and name:
                        update_contact(r[0], dict(
                            name=name, phone=phone, email=email, source=source, interest=interest, status=status,
                            tags=tags, assigned=assigned, notes=notes, action_needed=action_needed, action_taken=action_taken,
                            username=username, password=password
                        ))
                        st.success("Contact updated.")
        else:  # Delete
            rows = fetch_contacts()
            options = {f"#{r[0]} {r[1]} • {r[2] or ''}": r for r in rows}
            sel = st.selectbox("Select contact to delete", list(options.keys())) if options else None
            if sel and st.button("Delete Contact", type="primary"):
                r = options[sel]
                delete_contact(r[0])
                st.warning(f"Deleted contact #{r[0]} {r[1]}")

    st.subheader("Search & Filter")
    col1, col2, col3 = st.columns(3)
    with col1:
        search = st.text_input("Search", placeholder="Name, phone, email, interest, notes, action...")
    with col2:
        status_f = st.selectbox("Status filter", [""] + STATUSES)
    with col3:
        tag_f = st.text_input("Tag filter")
    rows = fetch_contacts(search=search, status=status_f, tag=tag_f)
    if rows:
        df = pd.DataFrame(rows, columns=["ID","Name","Phone","Email","Source","Interest","Status","Tags","Assigned","Notes","ActionNeeded","ActionTaken","Username","Password","Created"])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No contacts found.")

# --- ORDERS ---
elif page == "Orders":
    st.header("🧾 Orders")
    rows = fetch_contacts()
    contact_map = {f"#{r[0]} {r[1]}": r[0] for r in rows}
    with st.form("add_order"):
        contact_sel = st.selectbox("Contact", list(contact_map.keys())) if contact_map else None
        product = st.text_input("Product (e.g., STP, NRM, Luna)")
        qty = st.number_input("Quantity", min_value=1, value=1, step=1)
        amount = st.number_input("Amount (ZAR)", min_value=0.0, step=1.0)
        status = st.selectbox("Status", ["Pending","Paid","Shipped","Delivered"], index=0)
        pop_url = st.text_input("POP URL (optional)")
        notes = st.text_area("Notes", height=80)
        submitted = st.form_submit_button("Add Order")
        if submitted and contact_sel:
            insert_order(dict(contact_id=contact_map[contact_sel], product=product, quantity=int(qty), amount=float(amount), status=status, pop_url=pop_url, notes=notes))
            st.success("Order added.")

    st.subheader("Recent Orders")
    o_rows = fetch_orders()
    if o_rows:
        o_df = pd.DataFrame(o_rows, columns=["ID","ContactID","Contact","Product","Qty","Amount","Status","POP","Notes","Created"])
        st.dataframe(o_df, use_container_width=True, hide_index=True)
    else:
        st.info("No orders yet.")

# --- CAMPAIGNS ---
elif page == "Campaigns":
    st.header("📣 Campaigns")
    with st.form("add_campaign"):
        channel = st.selectbox("Channel", ["WhatsApp","Facebook","TikTok","Email","YouTube","Other"])
        name = st.text_input("Campaign Name")
        audience = st.text_input("Audience/Segment")
        message = st.text_area("Message (template)")
        outcome = st.selectbox("Outcome", ["","Sent","Replied","Converted","Bounced","Seen"])
        notes = st.text_area("Notes", height=80)
        submitted = st.form_submit_button("Save Campaign")
        if submitted:
            insert_campaign(dict(date=None, channel=channel, name=name, audience=audience, message=message, outcome=outcome, notes=notes))
            st.success("Campaign saved.")

    st.subheader("Search")
    s = st.text_input("Search campaigns")
    c_rows = fetch_campaigns(s)
    if c_rows:
        c_df = pd.DataFrame(c_rows, columns=["ID","Date","Channel","Name","Audience","Message","Outcome","Notes"])
        st.dataframe(c_df, use_container_width=True, hide_index=True)
    else:
        st.info("No campaigns yet.")

# --- WHATSAPP TOOLS ---
elif page == "WhatsApp Tools":
    st.header("💬 WhatsApp Tools")
    st.write("Create one-click WhatsApp messages with your templates.")
    template = st.text_area("Template", value=("Hi 👋 {name}, it’s Vanto from APLGO SA.\n"
                                               "Your R375 membership expired, but exciting news — MyAPL World is here 🌍, plus our new product Luna 🌙, multicurrency payouts 💱, and the same powerful lozenges you love 🍃.\n"
                                               "Life has seasons — your door to APLGO is open again! 🔑\n"
                                               "Rejoin here 👉 https://myaplworld.com/pages.cfm?p=CC1809B8\n"
                                               "We’ve kept your seat warm 🔥"))
    rows = fetch_contacts()
    if rows:
        st.subheader("Pick a contact")
        lookup = {f"#{r[0]} {r[1]}": r for r in rows}
        sel = st.selectbox("Contact", list(lookup.keys()))
        r = lookup[sel]
        filled = template.format(
            name=r[1], phone=r[2] or "", interest=r[5] or "", status=r[6] or "", tags=r[7] or "", assigned=r[8] or "",
            action_needed=r[10] or "", action_taken=r[11] or "", username=r[12] or "", password=r[13] or ""
        )
        link = wa_link(r[2] or "", filled)
        st.markdown(f"[Open WhatsApp message ↗]({link})")
        st.code(filled)
        if st.button("Log as Activity (WhatsApp)"):
            insert_activity(dict(contact_id=r[0], activity_date=None, type="whatsapp", summary="Sent template", details=filled))
            st.success("Activity logged.")
    else:
        st.info("Add contacts first.")

# --- IMPORT / EXPORT ---
elif page == "Import / Export":
    st.header("📥 Import / Export")
    st.write("Import contacts from CSV/Excel. Map fields below. New fields supported: ActionNeeded, ActionTaken, Username, Password")
    upl = st.file_uploader("Upload CSV or Excel", type=["csv","xlsx"])
    if upl is not None:
        if upl.name.endswith(".csv"):
            df = pd.read_csv(upl)
        else:
            df = pd.read_excel(upl)
        st.write("Preview:")
        st.dataframe(df.head(), use_container_width=True)
        # Map columns
        default_map = {
            "name":"name","phone":"phone","email":"email","source":"source","interest":"interest",
            "status":"status","tags":"tags","assigned":"assigned","notes":"notes",
            "action_needed":"action_needed","action_taken":"action_taken","username":"username","password":"password"
        }
        st.write("Map your columns to CRM fields:")
        crm_fields = list(default_map.keys())
        col_map = {}
        for f in crm_fields:
            options = ["--"] + list(df.columns)
            # auto-guess
            guess = next((c for c in df.columns if c.lower().strip().replace(" ","") == f.replace("_","")), None)
            col_map[f] = st.selectbox(f"{f}", options, index=(options.index(guess) if guess in options else 0), key=f"map_{f}")
        if st.button("Import Now", type="primary"):
            cnt = 0
            for _, row in df.iterrows():
                data = {}
                for f, col in col_map.items():
                    if col != "--":
                        val = row[col]
                        if pd.isna(val):
                            val = ""
                        data[f] = str(val)
                    else:
                        data[f] = ""
                if data.get("name") or data.get("phone"):
                    insert_contact(data)
                    cnt += 1
            st.success(f"Imported {cnt} contacts.")
    st.divider()
    st.subheader("Export")
    exp_rows = fetch_contacts()
    if exp_rows:
        cols = ["ID","Name","Phone","Email","Source","Interest","Status","Tags","Assigned","Notes","ActionNeeded","ActionTaken","Username","Password","Created"]
        exp_df = pd.DataFrame(exp_rows, columns=cols)
        st.download_button("Download Contacts CSV", exp_df.to_csv(index=False).encode("utf-8"), "contacts_export.csv", "text/csv")

# --- HELP ---
elif page == "Help":
    st.header("🚀 How to run this CRM")
    st.markdown("""
**Start:**  
```
python -m streamlit run app.py
```

**Tips**
- Use **Import / Export** to bring in your Excel lists.
- Use **WhatsApp Tools** with placeholders like `{name}`, `{interest}`, `{action_needed}`, `{username}` in your templates.
""")
