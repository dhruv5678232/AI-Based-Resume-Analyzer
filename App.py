import streamlit as st
import nltk
import spacy
from nltk.corpus import stopwords
import pandas as pd
import base64
import time
import datetime
import re
import pdfplumber
from streamlit_tags import st_tags
from PIL import Image
import pymysql
import random
import plotly.express as px

# ────────────────────────────────────────────────
#   CACHE HEAVY OBJECTS
# ────────────────────────────────────────────────

@st.cache_resource
def load_spacy():
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        st.error("spaCy model failed to load. This should not happen if requirements are correct.")
        st.stop()

nlp = load_spacy()

nltk.download('stopwords', quiet=True)
stop_words = set(stopwords.words('english'))

# ────────────────────────────────────────────────
#   DB SETUP
# ────────────────────────────────────────────────

connection = pymysql.connect(host='localhost', user='root', password='')
cursor = connection.cursor()

cursor.execute("CREATE DATABASE IF NOT EXISTS SRA;")
connection.select_db("sra")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_data (
        ID INT AUTO_INCREMENT PRIMARY KEY,
        Name VARCHAR(100) NOT NULL,
        Email_ID VARCHAR(50) NOT NULL,
        resume_score VARCHAR(8) NOT NULL,
        Timestamp VARCHAR(50) NOT NULL,
        Page_no VARCHAR(5) NOT NULL,
        Predicted_Field VARCHAR(25) NOT NULL,
        User_level VARCHAR(30) NOT NULL,
        Actual_skills VARCHAR(300) NOT NULL,
        Recommended_skills VARCHAR(300) NOT NULL,
        Recommended_courses VARCHAR(600) NOT NULL
    );
""")
connection.commit()

# ────────────────────────────────────────────────
#   HELPERS
# ────────────────────────────────────────────────

def get_table_download_link(df, filename, text):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

def extract_text_with_pdfplumber(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text.strip()

def simple_extract_skills(text):
    # Very basic keyword-based skill extraction (expand this list!)
    skill_keywords = [
        'python', 'java', 'javascript', 'react', 'node', 'sql', 'aws', 'docker',
        'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'data science',
        'html', 'css', 'flutter', 'kotlin', 'swift', 'figma', 'ux', 'ui'
    ]
    found = set()
    text_lower = text.lower()
    for skill in skill_keywords:
        if skill in text_lower:
            found.add(skill.title())
    return sorted(list(found))

def course_recommender(course_list, max_reco=4):
    st.subheader("**Courses & Certificates Recommendations**")
    rec_course = []
    random.shuffle(course_list)
    for i, (name, link) in enumerate(course_list, 1):
        if i > max_reco: break
        st.markdown(f"{i}) [{name}]({link})")
        rec_course.append(name)
    return rec_course

# Dummy course lists (replace with your real ones from Courses.py)
ds_course = [("Coursera ML", "https://coursera.org/..."), ("Fast.ai", "https://fast.ai")]
web_course = [("React Official", "https://react.dev"), ("freeCodeCamp", "https://freecodecamp.org")]
android_course = [("Android Basics", "https://developer.android.com/courses")]
ios_course = [("SwiftUI", "https://developer.apple.com/tutorials/swiftui")]
uiux_course = [("Google UX", "https://grow.google/certificates/ux-design")]

resume_videos = []      # ← comment out or fill later
interview_videos = []   # ← comment out or fill later

# ────────────────────────────────────────────────
#   MAIN APP
# ────────────────────────────────────────────────

def main():
    st.set_page_config(page_title="Smart Resume Analyzer", page_icon="📄")

    st.title("Smart Resume Analyzer")

    choice = st.sidebar.selectbox("Mode", ["Normal User", "Admin"])

    img = Image.open('./Logo/SRA_Logo.jpg')  # adjust path if needed
    img = img.resize((180, 180))
    st.sidebar.image(img)

    if choice == "Normal User":
        pdf_file = st.file_uploader("Upload your Resume (PDF)", type=["pdf"])

        if pdf_file:
            save_path = f"./Uploaded_Resumes/{pdf_file.name}"
            with open(save_path, "wb") as f:
                f.write(pdf_file.getbuffer())

            # Show PDF preview
            with open(save_path, "rb") as f:
                base64_pdf = base64.b64encode(f.read()).decode('utf-8')
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)

            # Extract text
            resume_text = extract_text_with_pdfplumber(save_path)

            # Very basic name/email guess (expand later)
            name = "User"
            email = re.search(r'[\w\.-]+@[\w\.-]+', resume_text)
            if email: email = email.group(0)

            st.header("Resume Analysis")
            st.success(f"Hello {name}!")

            pages = len(resume_text) // 2500 + 1  # rough estimate
            if pages <= 1:
                level = "Fresher"
                color = "#d73b5c"
            elif pages == 2:
                level = "Intermediate"
                color = "#1ed760"
            else:
                level = "Experienced"
                color = "#fba171"

            st.markdown(f"<h4 style='color:{color};'>You appear to be at **{level}** level.</h4>", unsafe_allow_html=True)

            # Skills
            skills = simple_extract_skills(resume_text)

            st.subheader("Detected Skills")
            st_tags(value=skills, label='', text='')

            # Field detection (very simple – improve later)
            reco_field = "General"
            recommended_skills = []
            courses = []

            if any(k in resume_text.lower() for k in ["machine learning", "data", "tensorflow", "python"]):
                reco_field = "Data Science"
                recommended_skills = ["Pandas", "Scikit-learn", "SQL", "Power BI"]
                courses = course_recommender(ds_course)

            elif any(k in resume_text.lower() for k in ["react", "javascript", "node", "frontend"]):
                reco_field = "Web Development"
                recommended_skills = ["TypeScript", "Next.js", "Tailwind CSS"]
                courses = course_recommender(web_course)

            # Resume score (dummy version)
            score = 40 + len(skills) * 8
            score = min(score, 100)

            st.subheader("Resume Score")
            st.progress(int(score))
            st.success(f"Score: **{score}/100**")

            # Save to DB (adapt fields)
            ts = datetime.datetime.now()
            timestamp = ts.strftime('%Y-%m-%d_%H:%M:%S')
            cursor.execute("""
                INSERT INTO user_data 
                (Name, Email_ID, resume_score, Timestamp, Page_no, Predicted_Field, User_level, Actual_skills, Recommended_skills, Recommended_courses)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, email or "N/A", str(score), timestamp, str(pages), reco_field, level, ", ".join(skills), ", ".join(recommended_skills), ", ".join(courses)))
            connection.commit()

    else:  # Admin
        st.success("Admin Panel")
        ad_user = st.text_input("Username")
        ad_password = st.text_input("Password", type="password")

        if st.button("Login"):
            if ad_user == "admin" and ad_password == "admin123":  # ← change this!
                st.success("Logged in")
                cursor.execute("SELECT * FROM user_data")
                data = cursor.fetchall()
                if data:
                    df = pd.DataFrame(data, columns=['ID','Name','Email','Resume Score','Timestamp','Pages','Field','Level','Skills','Rec Skills','Rec Courses'])
                    st.dataframe(df)
                    st.markdown(get_table_download_link(df, "user_data.csv", "Download Data"), unsafe_allow_html=True)

                    # Charts
                    if not df.empty:
                        fig1 = px.pie(df, names='Field', title="Predicted Fields")
                        st.plotly_chart(fig1)

                        fig2 = px.pie(df, names='Level', title="Experience Levels")
                        st.plotly_chart(fig2)
            else:
                st.error("Wrong credentials")

if __name__ == "__main__":
    main()
