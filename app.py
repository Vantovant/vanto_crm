import streamlit as st
import pandas as pd
from dateutil import parser
import db

st.set_page_config(page_title="Vanto CRM v3", page_icon="📇", layout="wide")

# Init DB / auto-migrate
db.init_db()

FIELDS = [
    ("name","Name"),
    ("phone","Phone"),
    ("email","Email"),
    ("source","Source"),
    ("interest","Interest"),
    ("status","Status"),
    ("tags","Tags"),
    ("assigned","Assigned"),
    ("notes","Notes"),
    ("action_needed","ActionNeeded"),
    ("action_taken","ActionTaken"),
    ("username","Username"),
    ("password","Password"),
    ("date","Date"),
    ("country","Country"),
    ("province","Province"),
    ("city","City"),
]

FIELD_KEYS = [k for k,_ in FIELDS]

st.sidebar.title("Vanto CRM v3")
page = st.sidebar.radio("Menu", ["Dashboard","Contacts","Import / Export","WhatsApp Tools","Help"])

def normalize_date(value):
    if not value or str(value).strip()=="" or str(value).lower()=="nan":
        return ""
    try:
        d = parser.parse(str(value), dayfirst=True, yearfirst=False)
        return d.strftime("%Y-%m-%d")
    except Exception:
        return str(value)

if page=="Dashboard":
    st.title("📊 Dashboard")
    contacts = db.get_contacts()
    total = len(contacts)
    hot = sum(1 for c in contacts if str(c.get("status","")).lower()=="hot")
    warm = sum(1 for c in contacts if str(c.get("status","")).lower()=="warm")
    customers = sum(1 for c in contacts if str(c.get("status","")).lower()=="customer")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Contacts", total)
    col2.metric("Hot", hot)
    col3.metric("Warm", warm)
    col4.metric("Customers", customers)

    st.divider()
    st.subheader("Recent Contacts")
    if contacts:
        df = pd.DataFrame(contacts).tail(50)
        st.dataframe(df[["name","phone","status","country","province","city","date"]], use_container_width=True, hide_index=True)
    else:
        st.info("No contacts yet. Import some in **Import / Export**.")

elif page=="Contacts":
    st.title("📇 Contacts")
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        q = st.text_input("Search name/phone/interest", "")
    with c2:
        f_country = st.text_input("Filter Country", "")
    with c3:
        f_province = st.text_input("Filter Province", "")
    with c4:
        f_city = st.text_input("Filter City", "")

    if q:
        all_rows = db.get_contacts()
        filtered = [r for r in all_rows if any(q.lower() in str(r.get(col,"")).lower() for col in ["name","phone","interest","tags","notes"])]
    else:
        filtered = db.get_contacts()

    def keep(row):
        if f_country and f_country.lower() not in str(row.get("country","")).lower(): return False
        if f_province and f_province.lower() not in str(row.get("province","")).lower(): return False
        if f_city and f_city.lower() not in str(row.get("city","")).lower(): return False
        return True
    filtered = [r for r in filtered if keep(r)]

    if filtered:
        df = pd.DataFrame(filtered)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Export contacts (CSV)", data=df.to_csv(index=False), file_name="contacts_export.csv", mime="text/csv")
    else:
        st.info("No contacts match your filters.")

elif page=="Import / Export":
    st.title("📥 Import / Export")
    st.subheader("Import Contacts")
    uploaded = st.file_uploader("Upload CSV or Excel", type=["csv","xlsx"])
    if uploaded:
        if uploaded.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded)
        else:
            df = pd.read_csv(uploaded)
        st.write("Preview:", df.head(3))

        st.markdown("### Map Columns")
        mapping = {}
        columns = ["-- skip --"] + list(df.columns)
        cols = st.columns(3)
        for i,(key,label) in enumerate(FIELDS):
            with cols[i%3]:
                mapping[key] = st.selectbox(f"{label}", columns, index=columns.index(label) if label in columns else 0, key=f"map_{key}")

        if st.button("Import Now"):
            items = []
            for _, row in df.iterrows():
                item = {}
                for key,_ in FIELDS:
                    src = mapping.get(key, "-- skip --")
                    val = "" if src=="-- skip --" else row.get(src, "")
                    if key=="date":
                        val = normalize_date(val)
                    if pd.isna(val):
                        val = ""
                    item[key] = str(val)
                items.append(item)
            count = db.upsert_contacts(items)
            st.success(f"Imported {count} contacts successfully.")
    st.divider()
    st.subheader("Export Contacts")
    allc = db.export_contacts()
    if allc:
        out_df = pd.DataFrame(allc)
        st.download_button("⬇️ Download all contacts (CSV)", data=out_df.to_csv(index=False), file_name="contacts_export.csv", mime="text/csv")
    else:
        st.info("No contacts to export yet.")

elif page=="WhatsApp Tools":
    st.title("💬 WhatsApp Tools")
    st.caption("Use placeholders: {name} {interest} {status} {action_needed} {action_taken} {username} {password} {date} {country} {province} {city}")
    contacts = db.get_contacts()
    if not contacts:
        st.info("Import contacts first.")
    else:
        names = [f"{c.get('name','(no name)')} — {c.get('phone','')}" for c in contacts]
        idx = st.selectbox("Select contact", list(range(len(contacts))), format_func=lambda i: names[i])
        tmpl = st.text_area("Message template", value="Hi {name}, just checking in from APLGO SA. I see you're in {city}, {province}. Ready for your next step?")
        if st.button("Generate Message"):
            c = contacts[idx]
            context = {k:(c.get(k,"") or "") for k in db.CONTACT_FIELDS}
            try:
                msg = tmpl.format(**context)
            except Exception as e:
                st.error(f"Template error: {e}")
                msg = None
            if msg:
                st.code(msg)
                phone = str(c.get("phone","")).replace(" ","")
                if phone:
                    url = f"https://wa.me/{phone}?text=" + st.experimental_uri.encode_component(msg)
                    st.markdown(f"[Open WhatsApp chat]({url})")

elif page=="Help":
    st.title("❓ Help")
    st.markdown("""
**Vanto CRM v3** adds **Date, Country, Province, City** to your contacts and supports them in import/export, filters, and WhatsApp templates.

**Import tips**
- Use the provided CSV template.
- Dates are stored as `YYYY-MM-DD`.
- Phone numbers: use international format (e.g., 27721234567).

**Avoid duplicates**
- Let one person do the initial import for the team.
- If you need a reset, delete `crm.sqlite3` locally and restart; on Streamlit Cloud redeploy creates a fresh DB.
""")
