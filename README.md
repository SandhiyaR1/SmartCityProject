# 🏙️ Smart City Hazard Reporting System (Flask + YOLO + SQLite)

A full-stack AI-powered web application that allows **citizens** to report hazards (potholes, garbage, road cracks, etc.) using **image uploads and GPS location**, and allows **mayors** to review and resolve them.

Built using:
- **Flask (Python)**
- **YOLO (Ultralytics)**
- **OpenCV**
- **SQLite Database**
- **Flask-Login (Authentication)**
- **Geopy (GPS → Address conversion)**

---

## 🚀 Features

### 👤 Citizen Features
- Create account / login
- Upload hazard images
- Provide GPS location (Latitude & Longitude)
- YOLO detects hazard type automatically
- Converts GPS → Address automatically
- View all past reports
- View annotated images with detection boxes
- Track status (Pending / Resolved)

### 🧑‍💼 Mayor Features
- Login as mayor
- Dashboard shows reports **only for their region**
- Review incoming hazard reports
- Mark issues as **Resolved**
- Track city-level reports

---

## 🧠 Technology Used

| Component | Technology |
|----------|------------|
| Backend | Flask |
| AI Model | YOLO (Ultralytics) |
| Image Processing | OpenCV |
| Database | SQLite |
| Location Services | Geopy (Nominatim API) |
| Authentication | Flask-Login |
| Deployment | Render |

---

