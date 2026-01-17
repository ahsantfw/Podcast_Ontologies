import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { WorkspaceProvider } from './context/WorkspaceContext'
import Chat from './pages/Chat'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import Scripts from './pages/Scripts'
import Explore from './pages/Explore'
import Account from './pages/Account'

function App() {
  return (
    <WorkspaceProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/scripts" element={<Scripts />} />
          <Route path="/explore" element={<Explore />} />
          <Route path="/account" element={<Account />} />
        </Routes>
      </Router>
    </WorkspaceProvider>
  )
}

export default App

