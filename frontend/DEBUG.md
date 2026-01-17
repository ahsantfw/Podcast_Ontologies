# Debug: Blank Page Issue

## Quick Test

If you see a blank page, try this:

### Step 1: Test if React Works

Temporarily replace `src/App.jsx` with this simple version:

```jsx
function App() {
  return (
    <div style={{ padding: '20px', fontFamily: 'Arial' }}>
      <h1>✅ React is Working!</h1>
      <p>If you see this, React is rendering.</p>
    </div>
  )
}

export default App
```

**If this shows:**
- React is working ✅
- Issue is with component imports
- Check browser console for specific errors

**If still blank:**
- Issue with React setup
- Check terminal for errors
- Verify node_modules installed

### Step 2: Check Browser Console

1. Open http://localhost:3000
2. Press **F12** (or Right-click → Inspect)
3. Go to **Console** tab
4. Look for **RED error messages**
5. Share the errors you see

### Step 3: Check Network Tab

1. In DevTools, go to **Network** tab
2. Refresh page (F5)
3. Check if `main.jsx` loads (should be 200)
4. Check for any failed requests (RED)

### Step 4: Restart Server

```bash
# Kill existing
pkill -f vite

# Restart
cd frontend
npm run dev
```

### Common Errors:

1. **"Cannot find module"**
   - Run: `npm install`

2. **"Failed to fetch"**
   - Backend not running
   - Start backend on port 8000

3. **"useWorkspace must be used within WorkspaceProvider"**
   - Component structure issue
   - Check App.jsx structure

4. **CORS errors**
   - Backend CORS not configured
   - Check backend CORS settings

### What to Share:

1. Browser console errors (F12 → Console)
2. Network tab errors (F12 → Network)
3. Terminal output when running `npm run dev`
4. What you see (blank? error message? anything?)

