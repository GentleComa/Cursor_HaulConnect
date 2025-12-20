# DEBUG Mode Troubleshooting Guide

## ✅ Current Status

- **DEBUG Mode:** `True` ✓
- **Simulate Routes Registered:** `True` ✓
- **Server Running:** Port 5001 ✓

## 🔍 How to Verify DEBUG Mode

### Method 1: Check Debug Endpoint

Visit: `http://localhost:5001/debug-check`

Should return:

```json
{
  "DEBUG": true,
  "FLASK_ENV": "development",
  "simulate_routes_registered": true
}
```

### Method 2: Check Server Logs

When you start the server, you should see:

```text
* Debug mode: on
```

## 🚨 Common Issues & Solutions

### Issue 1: "403 Forbidden" or "DEBUG mode required" Error

**Cause:** Server not running with DEBUG=True

**Solution:**

1. Stop the server (Ctrl+C or `pkill -f "python.*app.py"`)
2. Restart with: `FLASK_ENV=development python app.py`
3. Verify with: `curl http://localhost:5001/debug-check`

### Issue 2: Simulation Links Not Showing in Navigation

**Cause:** Browser cache or not logged in as admin/driver

**Solution:**

1. **Log out completely**
2. **Clear browser cache** (Cmd+Shift+Delete on Mac, Ctrl+Shift+Delete on Windows)
3. **Log back in** as admin: `admin@test.com` / `password123`
4. Check navigation menu - should see "Simulation" link

### Issue 3: Routes Redirect to Login

**Expected Behavior:** Simulation routes require login first

**Solution:**

1. Go to: `http://localhost:5001/auth/login`
2. Login with: `admin@test.com` / `password123`
3. Then access: `http://localhost:5001/simulate/map-view`

### Issue 4: Still Getting 403 After Login

**Possible Causes:**

- Session not refreshed
- Wrong user role (need admin for map-view, driver for dev-dashboard)
- Browser cache

**Solution:**

1. **Log out** completely
2. **Hard refresh** browser (Cmd+Shift+R on Mac)
3. **Log back in** as admin
4. Try accessing simulation route again

## 🧪 Test Access Step-by-Step

### For Admin (Map View)

1. Go to: `http://localhost:5001/auth/login`
2. Login: `admin@test.com` / `password123`
3. Should redirect to: `/admin/dashboard`
4. In navigation, click "Simulation" or go to: `http://localhost:5001/simulate/map-view`
5. Should see map view page

### For Driver (Dev Dashboard)

1. Go to: `http://localhost:5001/auth/login`
2. Login: `driver@test.com` / `password123`
3. Should redirect to: `/loads/driver/load-board`
4. In navigation, click "Simulation" or go to: `http://localhost:5001/simulate/dev-dashboard`
5. Should see developer dashboard

## 🔧 Manual Server Restart (Recommended)

If you're still having issues, do a clean restart:

```bash
# 1. Kill all Python app processes
pkill -f "python.*app.py"

# 2. Wait a moment
sleep 2

# 3. Navigate to project
cd "/Users/gentlecoma/Documents/Cursor Project Folder/Cursor_HaulConnect"

# 4. Activate virtual environment
source venv/bin/activate

# 5. Start server with explicit DEBUG mode
FLASK_ENV=development python app.py
```

## 📋 Verification Checklist

- [ ] Server shows "Debug mode: on" in startup logs
- [ ] `/debug-check` returns `{"DEBUG": true}`
- [ ] Logged in as admin or driver
- [ ] Browser cache cleared
- [ ] Hard refresh performed (Cmd+Shift+R)
- [ ] Session refreshed (logged out and back in)

## 🎯 Direct Test URLs

After logging in, try these URLs directly:

**Admin:**

- `http://localhost:5001/simulate/map-view`
- `http://localhost:5001/simulate/report/latest`

**Driver:**

- `http://localhost:5001/simulate/dev-dashboard`

**Both (if logged in):**

- `http://localhost:5001/debug-check` (should show DEBUG: true)

## 💡 Still Not Working?

If you're still having issues:

1. **Check browser console** (F12) for any JavaScript errors
2. **Check server terminal** for any error messages
3. **Try incognito/private window** to rule out cache issues
4. **Verify you're using the correct credentials:**
   - Admin: `admin@test.com` / `password123`
   - Driver: `driver@test.com` / `password123`

## 📞 Quick Diagnostic

Run this to see current status:

```bash
curl http://localhost:5001/debug-check
```

Should return: `{"DEBUG": true, ...}`

If it returns `{"DEBUG": false}`, the server needs to be restarted with DEBUG mode.
