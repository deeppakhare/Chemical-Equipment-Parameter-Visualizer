# Chemical Equipment Parameter Visualizer  
**(Web + Desktop + Django Backend)**

A full-stack system for uploading chemical-equipment CSV files, generating summary statistics, visualizing charts, tracking upload history, and downloading beautifully formatted PDF reports.

---

## 🚀 Features
### **Web Client (React)**
- Secure Login (Token-based)
- CSV Upload + Full Data Preview
- Auto-detected numeric parameters
- Interactive Line Charts (Chart.js)
- History view for last 5 uploads
- WeasyPrint PDF Report Download
- Modern clean UI (cards, spacing, KPIs)

### **Desktop Client (PyQt5)**
- Login Screen (token cache optional)
- CSV Preview (200-row sample)
- KPI cards (Dataset, Rows, Columns, Numeric)
- Line Chart Visualization (Matplotlib)
- Upload to backend
- History panel + summary loader
- Full PDF Report generation
- Web-style theme applied to Qt (CSS-like QSS)

### **Backend (Django + DRF)**
- Authentication (`/api-token-auth/`)
- CSV Upload → Auto summary generation
- Summary API  
- History API (last 5 uploads per user)
- WeasyPrint HTML-to-PDF Reports
- Handles large CSVs efficiently

---

## 📂 Project Structure
/backend → Django API + Report Generator

/web → React Frontend

/desktop → PyQt5 Desktop App

/samples → Sample CSV + JSON

---

## 🛠️ Installation & Setup

### **1. Backend Setup**
```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate     # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000

Create a superuser:
python manage.py createsuperuser
```

### **2. Web Client Setup**
```bash
cd web
npm install
npm run dev
Open: http://localhost:5173
```

### **3. Desktop App Setup**
```bash
cd desktop
pip install -r requirements.txt
python client.py
```
## 📊 Report Generation (WeasyPrint)
The backend converts an HTML template into a clean PDF containing:
- Dataset ID
- Rows / Columns
- Summary statistics (mean, min, max, std)
- Auto-generated line chart
- Timestamp & branding
Both Web and Desktop download the same backend-generated PDF.

## 📁 Sample Files
Inside ```/samples/```:
- sample_equipment_data.csv
- sample_summary_api_payload.json
- report_template.html
- styles.css

Used for demos, previews, and fallback testing.

## 🎬 Demo Flow (2-minute reviewer path)
1. Login

2. Upload CSV

3. Show client-side preview

4. View KPIs (Rows, Columns, Numeric)

5. Plot charts

6. Open History

7. Load past dataset

8. Generate PDF Report

9. Download & open report

## ✔️ Submission Ready
This project includes:
- Complete backend
- Fully styled Web UI
- Fully styled Desktop UI
- WeasyPrint PDF engine
- Thread-safe operations
- Sample files
- Clean README

## 📧 Author
Deep Pakhare <br/>
Chemical Equipment Parameter Visualizer (Web + Desktop)