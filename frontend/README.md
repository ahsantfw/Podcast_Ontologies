# Knowledge Graph Frontend - React + Vite

Complete React frontend for the Knowledge Graph System.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
# or
yarn install
# or
pnpm install
```

### 2. Run Development Server

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

The frontend will run on **http://localhost:3000**

### 3. Build for Production

```bash
npm run build
# or
yarn build
# or
pnpm build
```

## 📋 Prerequisites

1. **Backend API running** on http://localhost:8000
2. **Node.js** (v18 or higher)
3. **npm/yarn/pnpm**

## 🏗️ Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── Layout.jsx          # Main layout with navbar
│   ├── pages/
│   │   ├── Dashboard.jsx       # Dashboard page
│   │   ├── Query.jsx           # Query interface
│   │   ├── Upload.jsx          # Upload & process
│   │   ├── Scripts.jsx         # Script generation
│   │   └── Explore.jsx         # Graph explorer
│   ├── context/
│   │   └── WorkspaceContext.jsx # Workspace state management
│   ├── services/
│   │   └── api.js              # API service layer
│   ├── App.jsx                 # Main app component
│   ├── main.jsx                # Entry point
│   └── index.css               # Global styles (Tailwind)
├── package.json
├── vite.config.js              # Vite configuration
├── tailwind.config.js          # Tailwind CSS config
└── postcss.config.js           # PostCSS config
```

## 🎨 Features

- ✅ **React 18** with Hooks
- ✅ **React Router** for navigation
- ✅ **Tailwind CSS** for styling
- ✅ **Axios** for API calls
- ✅ **Context API** for state management
- ✅ **Responsive Design** (mobile-friendly)
- ✅ **All Pages**: Dashboard, Query, Upload, Scripts, Explore
- ✅ **Show/Hide Toggles** (Sources, Graph)
- ✅ **Progress Tracking** (persists on refresh)
- ✅ **Session Management** (localStorage)
- ✅ **Workspace Management**

## 🔧 Configuration

### API Proxy

The Vite config proxies `/api` requests to the backend:

```js
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
}
```

If your backend runs on a different port, update `vite.config.js`.

## 📱 Pages

1. **Dashboard** (`/`)
   - Graph statistics
   - Quick actions
   - Node/relationship breakdowns

2. **Query** (`/query`)
   - Natural language querying
   - Show/hide sources
   - Show/hide graph
   - Conversation history

3. **Upload** (`/upload`)
   - File upload (multiple files)
   - Background processing
   - Progress tracking (persists)

4. **Scripts** (`/scripts`)
   - Theme-based script generation
   - Runtime, style, format options
   - Preview & download

5. **Explore** (`/explore`)
   - Concept search
   - Concept details
   - Relationship visualization
   - Graph exploration

## 🔌 API Integration

All API calls are handled through `src/services/api.js`:

- `queryAPI` - Query endpoints
- `scriptsAPI` - Script generation
- `ingestionAPI` - Upload & processing
- `graphAPI` - Graph exploration
- `workspaceAPI` - Workspace management
- `sessionsAPI` - Session management

## 🎯 State Management

- **Workspace Context**: Manages current workspace_id
- **LocalStorage**: Persists workspace_id and session_id
- **Component State**: Each page manages its own state

## 🐛 Troubleshooting

### Port already in use
```bash
# Change port in vite.config.js or use:
npm run dev -- --port 3001
```

### API connection errors
- Make sure backend is running on http://localhost:8000
- Check CORS settings in backend
- Verify proxy configuration in vite.config.js

### Build errors
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

## ✅ Production Build

```bash
npm run build
```

Build output will be in `dist/` directory.

To serve the built files:
```bash
npm run preview
```

## 📄 License

Same as main project.

