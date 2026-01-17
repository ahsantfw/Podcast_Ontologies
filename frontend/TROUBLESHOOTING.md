# Troubleshooting - Frontend Not Showing

## Issue: Blank Page on http://localhost:3000

### Quick Fix Steps:

1. **Check Browser Console**
   - Open browser DevTools (F12)
   - Check Console tab for errors
   - Check Network tab for failed requests

2. **Restart Dev Server**
   ```bash
   # Kill existing process
   pkill -f vite
   
   # Restart
   cd frontend
   npm run dev
   ```

3. **Check for Import Errors**
   - Make sure all files exist
   - Check for missing dependencies

4. **Clear Browser Cache**
   - Hard refresh: Ctrl+Shift+R (Linux/Windows) or Cmd+Shift+R (Mac)
   - Or clear browser cache

### Common Issues:

#### Issue 1: JavaScript Errors in Console
**Solution:** Check browser console for specific error messages

#### Issue 2: Module Not Found
**Solution:** 
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

#### Issue 3: Port Already in Use
**Solution:**
```bash
# Use different port
npm run dev -- --port 3001
```

#### Issue 4: React Not Rendering
**Check:**
- Is `src/main.jsx` correct?
- Is `src/App.jsx` correct?
- Are all imports working?

### Debug Steps:

1. **Check if server is running:**
   ```bash
   curl http://localhost:3000
   ```
   Should return HTML

2. **Check if main.jsx loads:**
   ```bash
   curl http://localhost:3000/src/main.jsx
   ```
   Should return JavaScript

3. **Check browser console:**
   - Open http://localhost:3000
   - Press F12
   - Check Console tab
   - Look for red error messages

4. **Check Network tab:**
   - Open DevTools → Network
   - Refresh page
   - Check for failed requests (red)

### Manual Test:

Create a simple test file to verify React works:

```bash
# Create test file
cat > frontend/src/App.jsx << 'EOF'
function App() {
  return <div><h1>Hello World - React is Working!</h1></div>
}
export default App
EOF

# Restart server
npm run dev
```

If this shows "Hello World", then React is working and the issue is with the components.

### Still Not Working?

1. **Check terminal output** for errors
2. **Check browser console** for JavaScript errors
3. **Verify all files exist** in `src/` directory
4. **Try accessing** http://localhost:3000/src/main.jsx directly

### Get Help:

Share:
- Browser console errors
- Terminal output
- Network tab errors
- What you see (blank page? error message?)

