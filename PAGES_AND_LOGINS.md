# HaulConnect - Complete Page List & Test Logins

**Base URL:** `http://localhost:5001`

---

## 🔐 TEST LOGIN CREDENTIALS

### Admin Account

- **Email:** `admin@test.com`
- **Password:** `password123`
- **Role:** Admin
- **Access:** Full admin panel + simulation tools

### Driver Account

- **Email:** `driver@test.com`
- **Password:** `password123`
- **Role:** Driver
- **MC Number:** MC123456
- **Equipment:** dry_van
- **Access:** Load board, driver dashboard, simulation tools

### Shipper Account

- **Email:** `willis.jeremyr@gmail.com` (existing) or create via `/simulate/create-test-users`
- **Password:** (set during registration)
- **Role:** Shipper
- **Access:** Post loads, manage shipments, get quotes

---

## 📄 PUBLIC PAGES (No Login Required)

### Homepage

- **URL:** `/`
- **Template:** `templates/index.html`
- **Description:** Landing page with features and stats

### Load Board (Public View)

- **URL:** `/loads/`
- **Template:** `templates/loads/board.html`
- **Description:** Browse available loads (public view)

### Load Detail (Public)

- **URL:** `/loads/<load_id>`
- **Template:** `templates/loads/detail.html`
- **Description:** View load details

---

## 🔑 AUTHENTICATION PAGES

### Login

- **URL:** `/auth/login`
- **Template:** `templates/auth/login.html`
- **Methods:** GET, POST
- **Description:** User login (password required)

### Register

- **URL:** `/auth/register`
- **Template:** `templates/auth/register.html`
- **Methods:** GET, POST
- **Description:** Create new account (password required)

### Logout

- **URL:** `/auth/logout`
- **Description:** Log out current user

### Forgot Password

- **URL:** `/auth/forgot-password`
- **Template:** `templates/auth/forgot_password.html`
- **Methods:** GET, POST
- **Description:** Password reset request (TODO: not implemented)

---

## 👤 USER DASHBOARD PAGES (Login Required)

### Main Dashboard

- **URL:** `/dashboard/`
- **Template:** `templates/dashboard/index.html`
- **Description:** User-specific dashboard with stats
- **Role-based:** Shows different content for drivers vs shippers

### Profile

- **URL:** `/dashboard/profile`
- **Template:** `templates/dashboard/profile.html`
- **Description:** User profile management

### Settings

- **URL:** `/dashboard/settings`
- **Template:** `templates/dashboard/settings.html`
- **Description:** Account settings

### Payments

- **URL:** `/dashboard/payments`
- **Template:** `templates/dashboard/payments.html`
- **Description:** User payment history

---

## 📦 LOAD MANAGEMENT PAGES

### Load Board (Driver View)

- **URL:** `/loads/driver/load-board`
- **Template:** `templates/loads/driver_board.html`
- **Access:** Driver role required
- **Description:** Driver-specific load board

### Driver Load Detail

- **URL:** `/loads/driver/loads/<load_id>`
- **Template:** `templates/loads/driver_detail.html`
- **Access:** Driver role required
- **Description:** View and manage assigned load

### Post Load (Shipper)

- **URL:** `/loads/post`
- **Template:** `templates/loads/post.html`
- **Methods:** GET, POST
- **Access:** Shipper/Broker role required
- **Description:** Create new load posting

### Shipper Load List

- **URL:** `/loads/shipper/loads` (GET)
- **Template:** `templates/loads/shipper_list.html`
- **Access:** Shipper/Broker role required
- **Description:** List all loads posted by shipper

### Shipper Load Detail

- **URL:** `/loads/shipper/loads/<load_id>`
- **Template:** `templates/loads/shipper_detail.html`
- **Access:** Shipper/Broker role required
- **Description:** View and manage posted load

### Shipper Create Load Form

- **URL:** `/loads/shipper/loads/new`
- **Template:** `templates/loads/shipper_form.html`
- **Access:** Shipper/Broker role required
- **Description:** Form to create new load

### Get Quote Form

- **URL:** `/loads/shipper/quote` (GET)
- **Template:** `templates/loads/quote_form.html`
- **Access:** Shipper/Broker role required
- **Description:** Get freight quote

### Quote Result

- **URL:** `/loads/shipper/quote` (POST)
- **Template:** `templates/loads/quote_result.html`
- **Access:** Shipper/Broker role required
- **Description:** Display calculated quote

### My Loads

- **URL:** `/loads/my-loads`
- **Template:** `templates/loads/my_loads.html`
- **Description:** User's loads (role-based view)

---

## 👨‍💼 ADMIN PAGES (Admin Login Required)

### Admin Dashboard

- **URL:** `/admin/` or `/admin/dashboard`
- **Template:** `templates/admin/dashboard.html`
- **Access:** Admin only
- **Description:** Admin overview with statistics

### Admin Index

- **URL:** `/admin/` (redirects to dashboard)
- **Template:** `templates/admin/index.html`

### User Management

- **URL:** `/admin/users`
- **Template:** `templates/admin/users.html`
- **Access:** Admin only
- **Description:** List and manage all users

### User Detail

- **URL:** `/admin/users/<user_id>`
- **Template:** `templates/admin/user_detail.html`
- **Access:** Admin only
- **Description:** View user details and manage

### Loads Management

- **URL:** `/admin/loads`
- **Template:** `templates/admin/loads.html`
- **Access:** Admin only
- **Description:** Manage all loads in system

### Shipments

- **URL:** `/admin/shipments`
- **Template:** `templates/admin/shipments.html`
- **Access:** Admin only
- **Description:** Track all active shipments

### Idle Alerts

- **URL:** `/admin/idle-alerts`
- **Template:** `templates/admin/idle_alerts.html`
- **Access:** Admin only
- **Description:** View loads that are idle/stuck

### Payments

- **URL:** `/admin/payments`
- **Template:** `templates/admin/payments.html`
- **Access:** Admin only
- **Description:** Manage all payments

---

## 🧪 SIMULATION/DEBUG PAGES (DEBUG Mode Only)

### Developer Dashboard (Driver)

- **URL:** `/simulate/dev-dashboard`
- **Template:** `templates/simulate/dev_dashboard.html`
- **Access:** Driver login + DEBUG mode
- **Description:** Simulate load dispatch flow

### Map View (Admin)

- **URL:** `/simulate/map-view`
- **Template:** `templates/simulate/map_view.html`
- **Access:** Admin login + DEBUG mode
- **Description:** Visualize all simulated shipments on map

### Simulation Report (Latest)

- **URL:** `/simulate/report/latest`
- **Template:** `templates/simulate/report.html`
- **Access:** Admin login + DEBUG mode
- **Description:** View latest simulation report

### Simulation Report (Specific)

- **URL:** `/simulate/report/<run_id>`
- **Template:** `templates/simulate/report.html`
- **Access:** Admin login + DEBUG mode
- **Description:** View specific simulation report

### Download Report

- **URL:** `/simulate/report/<run_id>/download`
- **Access:** Admin login + DEBUG mode
- **Description:** Download report as JSON

---

## 🔌 API ENDPOINTS

### Loads API

- **GET** `/api/loads` - List loads (with filters)
- **GET** `/api/loads/<load_id>` - Get load details
- **POST** `/api/loads/<load_id>/tracking` - Update load tracking

### User API

- **GET** `/api/user/profile` - Get current user profile

### Quote API

- **POST** `/api/quote` - Calculate freight quote

### Messages API

- **GET** `/api/messages/<load_id>` - Get messages for load
- **POST** `/api/messages/<load_id>` - Send message

---

## 🛠️ SIMULATION API ENDPOINTS (DEBUG Mode Only)

### Create Test Users

- **POST** `/simulate/create-test-users`
- **Description:** Creates <driver@test.com>, <shipper@test.com>, <admin@test.com>
- **Password:** `password123` for all

### Create Test Loads

- **POST** `/simulate/create-test-loads`
- **Description:** Creates 10 random test loads

### Simulate Delivery

- **POST** `/simulate/simulate-delivery/<load_id>`
- **Description:** Simulate load delivery lifecycle

### Advance Load Status

- **POST** `/simulate/advance/<load_id>`
- **Access:** Driver login + DEBUG mode
- **Description:** Advance load to next status

### Create Bulk Shipments

- **POST** `/simulate/create-bulk/<count>` (1-50)
- **Access:** Admin login + DEBUG mode
- **Description:** Create bulk simulated shipments

### Map Data API

- **GET** `/simulate/api/map-data`
- **Access:** Admin login + DEBUG mode
- **Description:** Get current map data (JSON)

### Reset Database

- **POST** `/simulate/reset-database`
- **Body:** `{"confirm": "RESET"}`
- **Access:** DEBUG mode
- **Warning:** ⚠️ Deletes ALL data!

---

## ❌ ERROR PAGES

### 403 Forbidden

- **Template:** `templates/errors/403.html`
- **Description:** Access denied

### 404 Not Found

- **Template:** `templates/errors/404.html`
- **Description:** Page not found

### 500 Internal Server Error

- **Template:** `templates/errors/500.html`
- **Description:** Server error

---

## 🔍 DEBUG ENDPOINTS

### Debug Check

- **URL:** `/debug-check`
- **Description:** Check DEBUG mode status (JSON)
- **Returns:** `{"DEBUG": true/false, "FLASK_ENV": "...", "simulate_routes_registered": true/false}`

---

## 📝 NOTES

- **Password Required:** All authentication now requires passwords (AUTH_PASSWORD_REQUIRED=true)
- **DEBUG Mode:** Currently enabled - simulation routes are active
- **Base URL:** `http://localhost:5001`
- **All test users use password:** `password123`

---

## 🚀 QUICK START

1. **Login as Admin:**
   - Go to: `http://localhost:5001/auth/login`
   - Email: `admin@test.com`
   - Password: `password123`
   - Access: Admin dashboard, simulation tools

2. **Login as Driver:**
   - Go to: `http://localhost:5001/auth/login`
   - Email: `driver@test.com`
   - Password: `password123`
   - Access: Load board, driver dashboard, dev dashboard

3. **Create Shipper Account:**
   - Go to: `http://localhost:5001/auth/register`
   - Or use: POST to `/simulate/create-test-users` (creates <shipper@test.com>)
