import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Button, Box, CssBaseline } from '@mui/material';
import Tailor from './pages/Tailor';
import Apply from './pages/Apply';
import JobList from './pages/JobList';
import JobDetails from './pages/JobDetails';
import JobChat from './pages/JobChat';
import Profile from './pages/Profile';
import Login from './pages/Login';
import Onboarding from './pages/Onboarding';

function AppContent() {
  const location = useLocation();
  const hideNavRoutes = ['/login', '/onboarding'];
  const shouldShowNav = !hideNavRoutes.includes(location.pathname);

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
          </Toolbar>
        </AppBar>
      )}

      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/login" element={<Login />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/tailor" element={<Tailor />} />
        <Route path="/apply" element={<Apply />} />
        <Route path="/jobs" element={<JobList />} />
        <Route path="/jobs/chat" element={<JobChat />} />
        <Route path="/jobs/:id" element={<JobDetails />} />
        <Route path="/profile" element={<Profile />} />
      </Routes>
    </Box>
  );
}

function App() {
  return (
    <Router>
      <CssBaseline />
      <AppContent />
    </Router>
  );
}

export default App;