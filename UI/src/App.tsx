import { BrowserRouter as Router, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Button, Box, CssBaseline } from '@mui/material';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { PrivateRoute } from './components/PrivateRoute';
import Tailor from './pages/Tailor';
import Apply from './pages/Apply';
import JobList from './pages/JobList';
import JobDetails from './pages/JobDetails';
import JobChat from './pages/JobChat';
import JobMonitor from './pages/JobMonitor';
import Profile from './pages/Profile';
import Login from './pages/Login';
import Onboarding from './pages/Onboarding';

function AppContent() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const hideNavRoutes = ['/login', '/onboarding'];
  const shouldShowNav = !hideNavRoutes.includes(location.pathname) && user;

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      {shouldShowNav && (
        <AppBar position="static">
          <Toolbar>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              AutoApply
            </Typography>
            <Button color="inherit" component={Link} to="/tailor">Tailor</Button>
            <Button color="inherit" component={Link} to="/apply">Apply</Button>
            <Button color="inherit" component={Link} to="/jobs">Jobs</Button>
            <Button color="inherit" component={Link} to="/profile">Profile</Button>
            <Button color="inherit" onClick={handleLogout}>Logout</Button>
          </Toolbar>
        </AppBar>
      )}

      <Routes>
        <Route path="/" element={user ? <Navigate to={user.onboarding_complete ? '/tailor' : '/onboarding'} /> : <Login />} />
        <Route path="/login" element={<Login />} />
        <Route path="/onboarding" element={
          user && !user.onboarding_complete
            ? <Onboarding />
            : user
              ? <Navigate to="/tailor" />
              : <Navigate to="/login" />
        } />
        <Route path="/tailor" element={<PrivateRoute><Tailor /></PrivateRoute>} />
        <Route path="/apply" element={<PrivateRoute><Apply /></PrivateRoute>} />
        <Route path="/monitor" element={<PrivateRoute><JobMonitor /></PrivateRoute>} />
        <Route path="/jobs" element={<PrivateRoute><JobList /></PrivateRoute>} />
        <Route path="/jobs/chat" element={<PrivateRoute><JobChat /></PrivateRoute>} />
        <Route path="/jobs/:id" element={<PrivateRoute><JobDetails /></PrivateRoute>} />
        <Route path="/profile" element={<PrivateRoute><Profile /></PrivateRoute>} />
      </Routes>
    </Box>
  );
}

function App() {
  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

  if (!googleClientId) {
    console.error('VITE_GOOGLE_CLIENT_ID is not set');
  }

  return (
    <GoogleOAuthProvider clientId={googleClientId || ''}>
      <AuthProvider>
        <Router>
          <CssBaseline />
          <AppContent />
        </Router>
      </AuthProvider>
    </GoogleOAuthProvider>
  );
}

export default App;