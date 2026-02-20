import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import {
  Container,
  Paper,
  Typography,
  Box,
  Snackbar,
  Alert,
  CircularProgress,
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';

function Login() {
  const navigate = useNavigate();
  const { user, login, loading: authLoading } = useAuth();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Redirect if already logged in
  useEffect(() => {
    if (user) {
      navigate(user.onboarding_complete ? '/tailor' : '/onboarding');
    }
  }, [user, navigate]);

  const handleGoogleSuccess = async (credentialResponse: any) => {
    setLoading(true);
    setError('');

    try {
      const userData = await login(credentialResponse.credential);
      // The redirect will happen via the useEffect hook above
      navigate(userData.onboarding_complete ? '/tailor' : '/onboarding');
    } catch (err: any) {
      console.error('Login failed:', err);
      setError(err.response?.data?.detail || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleError = () => {
    setError('Google login failed. Please try again.');
  };

  if (authLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 12, mb: 4 }}>
        <Paper elevation={3} sx={{ p: 4, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <Typography variant="h4" component="h1" gutterBottom align="center" sx={{ mb: 2 }}>
            Welcome to AutoApply
          </Typography>
          <Typography variant="body1" color="text.secondary" gutterBottom align="center" sx={{ mb: 4 }}>
            Sign in with your Google account to get started
          </Typography>

          <Box sx={{ mb: 4 }}>
            {loading ? (
              <CircularProgress />
            ) : (
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={handleGoogleError}
                text="signin_with"
              />
            )}
          </Box>

          <Typography variant="caption" color="text.secondary" align="center">
            We use Google Sign-In to keep your data secure
          </Typography>
        </Paper>
      </Box>

      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={() => setError('')}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setError('')} severity="error" sx={{ width: '100%' }}>
          {error}
        </Alert>
      </Snackbar>
    </Container>
  );
}

export default Login;
