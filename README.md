# DBMS Normalization Tool

A full-stack web application for computing **attribute closure**, **candidate keys**, and **relational normalization** (2NF, 3NF, BCNF) — step by step, with a clean interactive UI.

Built as a DBMS academic project using **Python / Flask** (backend) and **Vanilla HTML/CSS/JS** (frontend).

---

## Project Structure

```
DBMS assignment/
│
├── backend/
│   ├── app.py               ← Flask REST API (3 endpoints + CORS + logging)
│   ├── closure.py           ← Attribute closure computation (fixed-point algorithm)
│   ├── candidate_keys.py    ← Candidate key discovery (optimised power-set search)
│   ├── normalization.py     ← 1NF check; 2NF, 3NF, BCNF decomposition algorithms
│   ├── parser.py            ← Schema + FD string parsing and validation
│   ├── utils.py             ← Helpers: power-set, superkey check, FD projection, JSON serialisation
│   └── config.py            ← Default demo input (schema + FD strings)
│
├── frontend/
│   ├── index.html           ← Semantic HTML5 page (pre-populated, no inline styles/JS)
│   ├── style.css            ← Full design system: variables, typography, all components, responsive
│   └── script.js            ← Fetch API calls, rendering, validation, tab switching
│
└── README.md                ← This file
```

---

## Prerequisites

- **Python 3.10** or higher
- **pip** (comes with Python)
- A modern web browser (Chrome, Firefox, or Edge recommended)

---

## Installation & Setup

### Step 1 — Install Python dependencies

```bash
pip install flask flask-cors
```

### Step 2 — Start the Flask backend

```bash
cd backend
python app.py
```

The backend will start at: **http://127.0.0.1:5000**

You should see:
```
INFO  Starting DBMS Normalization API on http://127.0.0.1:5000
 * Running on http://127.0.0.1:5000
```

### Step 3 — Open the frontend

**Option A — Open directly** (simplest):
```
Double-click frontend/index.html  (or drag it into your browser)
```

**Option B — Serve via Python HTTP server** (avoids any potential CORS issues with file://):
```bash
cd frontend
python -m http.server 8080
```
Then open: **http://localhost:8080**

> **Note:** You need the Flask backend running (Step 2) before clicking any button in the UI.

---

## API Reference

All endpoints accept and return **JSON**. CORS is enabled globally.

---

### `POST /closure`

Compute the attribute closure of a given set under the provided FDs, with a step-by-step trace.

**Request:**
```json
{
  "schema": "R(BookingID, CustomerID, Name, Phone, BikeID, Model, CategoryID, CategoryName, StartDate, EndDate, PaymentID, Amount)",
  "fds": [
    "BookingID -> CustomerID, BikeID, StartDate, EndDate",
    "CustomerID -> Name, Phone",
    "BikeID -> Model, CategoryID",
    "CategoryID -> CategoryName",
    "PaymentID -> BookingID, Amount"
  ],
  "attributes": ["BookingID"]
}
```

**Response (success):**
```json
{
  "success": true,
  "input_attributes": ["BookingID"],
  "closure": ["BikeID", "BookingID", "CategoryID", "CategoryName", "CustomerID", "EndDate", "Model", "Name", "Phone", "StartDate"],
  "steps": [
    "Start: {BookingID}",
    "Applied [BookingID → CustomerID, BikeID, StartDate, EndDate] → Added: BikeID, CustomerID, EndDate, StartDate",
    "Applied [CustomerID → Name, Phone] → Added: Name, Phone",
    "Applied [BikeID → Model, CategoryID] → Added: CategoryID, Model",
    "Applied [CategoryID → CategoryName] → Added: CategoryName",
    "No more FDs applicable. Closure complete."
  ],
  "determines_all": true
}
```

**Response (error):**
```json
{
  "success": false,
  "error": "Attribute 'XYZ' not found in schema."
}
```

---

### `POST /candidate-keys`

Find all candidate keys, prime attributes, and non-prime attributes of the relation.

**Request:**
```json
{
  "schema": "R(BookingID, CustomerID, Name, Phone, BikeID, Model, CategoryID, CategoryName, StartDate, EndDate, PaymentID, Amount)",
  "fds": [
    "BookingID -> CustomerID, BikeID, StartDate, EndDate",
    "CustomerID -> Name, Phone",
    "BikeID -> Model, CategoryID",
    "CategoryID -> CategoryName",
    "PaymentID -> BookingID, Amount"
  ]
}
```

**Response (success):**
```json
{
  "success": true,
  "candidate_keys": [["BookingID"], ["PaymentID"]],
  "prime_attributes": ["BookingID", "PaymentID"],
  "non_prime_attributes": ["Amount", "BikeID", "CategoryID", "CategoryName", "CustomerID", "EndDate", "Model", "Name", "Phone", "StartDate"]
}
```

---

### `POST /normalize`

Decompose the relation into 2NF, 3NF, and/or BCNF.

**Request:**
```json
{
  "schema": "R(BookingID, CustomerID, Name, Phone, ...)",
  "fds": ["BookingID -> CustomerID, BikeID, StartDate, EndDate", "..."],
  "target": "ALL"
}
```

- `target` can be `"2NF"`, `"3NF"`, `"BCNF"`, or `"ALL"` (default).

**Response (success — abbreviated):**
```json
{
  "success": true,
  "target": "ALL",
  "results": {
    "2NF": {
      "already_satisfied": true,
      "violations": [],
      "relations": [{ "name": "R", "attributes": [...], "primary_key": [...], "fds": [...] }]
    },
    "3NF": {
      "already_satisfied": false,
      "violations": [
        "CustomerID → Name, Phone (transitive: CustomerID is non-prime / not a superkey)",
        "BikeID → CategoryID, Model (transitive: BikeID is non-prime / not a superkey)",
        "CategoryID → CategoryName (transitive: CategoryID is non-prime / not a superkey)"
      ],
      "relations": [
        { "name": "R1", "attributes": ["BikeID", "BookingID", "CustomerID", "EndDate", "StartDate"], "primary_key": ["BookingID"], "fds": [...] },
        { "name": "R2", "attributes": ["CustomerID", "Name", "Phone"], "primary_key": ["CustomerID"], "fds": [...] },
        "..."
      ]
    },
    "BCNF": {
      "already_satisfied": false,
      "violations": [...],
      "fd_preservation_warning": "...",
      "relations": [...]
    }
  }
}
```

---

### `GET /health`

Simple liveness check.

**Response:**
```json
{ "status": "ok", "message": "DBMS Normalization API is running." }
```

---

## Usage Guide

1. **The input fields are pre-filled** with a sample Bike Rental schema and 5 functional dependencies — you can use them directly or replace them with your own.

2. **Compute Closure** — Enter one or more comma-separated attribute names in the "Attributes for Closure" field, then click **Compute Closure**. The result card shows each step of the fixed-point algorithm and whether the set determines the entire schema.

3. **Find Candidate Keys** — Click **Find Candidate Keys** to identify all candidate keys of the relation, along with a colour-coded breakdown of prime and non-prime attributes.

4. **Normalize** — Click **Normalize** to run all three decompositions. The result appears in a tabbed panel:
   - **2NF tab** — checks for and removes partial dependencies
   - **3NF tab** — synthesis algorithm; guarantees lossless-join AND dependency preservation
   - **BCNF tab** — lossless-join decomposition; may lose some FDs (warned in amber)

5. **Switch tabs** by clicking **2NF**, **3NF**, or **BCNF** in the tab bar.

6. **Clear Results** resets all result cards without clearing your input.

---

## Normalization Theory — Quick Reference

| Normal Form | Requirement | Algorithm used |
|-------------|-------------|----------------|
| **1NF** | All attributes atomic | Assumption (verified by convention) |
| **2NF** | No partial dependencies (non-prime attr ← proper subset of any CK) | Remove partial FDs; group by LHS |
| **3NF** | No transitive dependencies (non-prime ← non-superkey) | Synthesis via minimal cover |
| **BCNF** | Every non-trivial FD X→Y has X as a superkey | Recursive lossless-join decomposition |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| *"Cannot connect to backend"* in the UI | Make sure `python app.py` is running inside the `backend/` folder and listening on port 5000 |
| CORS error in browser console | Ensure `flask-cors` is installed (`pip install flask-cors`) and `CORS(app)` is present in `app.py` |
| Empty result cards after clicking | Open browser DevTools → Console tab and check for red errors; also check the Flask terminal for stack traces |
| HTTP 400 Bad Request | Verify that every attribute name in your FDs also exists in the schema string |
| FDs not detected | Ensure each FD in the textarea uses `->` (not `→` or `=>`); one FD per line |
| Port 5000 already in use | Change the port in `app.py` (`port=5001`) and update `API_BASE` in `script.js` accordingly |
| Slow response for large schemas | The candidate-key algorithm uses optimised search but still scales with schema size; schemas up to ~15 attributes are handled quickly |
