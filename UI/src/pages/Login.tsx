import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  Snackbar,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  Divider,
  Link,
  Avatar
} from '@mui/material';
import axios from 'axios';
import type { Contact } from '../types';
import { getApiUrl } from '../utils/api';
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch';

function Login() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isLogin, setIsLogin] = useState(true); // Toggle between Login and Sign Up
  const [formData, setFormData] = useState<Contact>({
    name: '',
    email: '',
    phone: '',
    country_code: '+1',
    linkedin: '',
    github: '',
    location: ''
  });

  const handleChange = (field: keyof Contact) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [field]: e.target.value });
  };

  const validateForm = (): boolean => {
    if (!isLogin && !formData.name.trim()) {
      setError('Name is required');
      return false;
    }
    if (!formData.email.trim()) {
      setError('Email is required');
      return false;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
      setError('Please enter a valid email address');
      return false;
    }
    if (!isLogin) {
        if (!formData.phone.trim()) {
          setError('Phone number is required');
          return false;
        }
        if (!formData.location.trim()) {
          setError('Location is required');
          return false;
        }
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setLoading(true);
    setError('');

    try {
      if (!isLogin) {
          await axios.post(getApiUrl('/save-user'), formData);
      } else {
          // You might have a login check endpoint in future. For now assume valid user if backend works?
          // Since the API only has /save-user and /user-form, we just check if it fails or assume email exists for demo purposes.
          // In a real app we'd verify the user here. Let's just save to localStorage for now as it's the only identifier.
      }
      
      // Store all contact data in sessionStorage for the onboarding form
      sessionStorage.setItem('userEmail', formData.email);
      if (!isLogin) {
          sessionStorage.setItem('userName', formData.name);
          sessionStorage.setItem('userPhone', formData.phone);
          sessionStorage.setItem('userCountryCode', formData.country_code);
          sessionStorage.setItem('userLocation', formData.location);
          navigate('/onboarding');
      } else {
          // If login, set email and navigate
          localStorage.setItem('userEmail', formData.email);
          navigate('/jobs');
      }
    } catch (err: any) {
      console.error('Error saving user:', err);
      setError(err.response?.data?.detail || 'Authentication failed. Please check backend connection.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box 
      sx={{ 
        minHeight: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #1976d2 0%, #115293 100%)',
        py: 4
      }}
    >
      <Container maxWidth="sm">
        <Paper 
          elevation={10} 
          sx={{ 
            p: { xs: 4, md: 6 }, 
            borderRadius: 4,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center'
          }}
        >
          <Box sx={{ mb: 4, textAlign: 'center' }}>
            <Avatar 
              sx={{ 
                bgcolor: 'primary.main', 
                width: 64, 
                height: 64, 
                margin: '0 auto 16px',
                boxShadow: 3
              }}
            >
              <RocketLaunchIcon fontSize="large" />
            </Avatar>
            <Typography variant="h3" fontWeight="bold" color="primary" gutterBottom>
              AutoApply
            </Typography>
            <Typography variant="body1" color="text.secondary">
              {isLogin ? 'Welcome back! Sign in to continue.' : 'Create an account to automate your job search.'}
            </Typography>
          </Box>

          <form onSubmit={handleSubmit} style={{ width: '100%' }}>
            <Stack spacing={2}>
              {!isLogin && (
                <TextField
                  fullWidth
                  label="Full Name"
                  placeholder="John Doe"
                  value={formData.name}
                  onChange={handleChange('name')}
                  required
                  disabled={loading}
                  variant="outlined"
                />
              )}

              <TextField
                fullWidth
                label="Email Address"
                type="email"
                placeholder="john@example.com"
                value={formData.email}
                onChange={handleChange('email')}
                required
                disabled={loading}
                variant="outlined"
              />

              {!isLogin && (
                <>
                  <Stack direction="row" spacing={2}>
                    <FormControl sx={{ minWidth: 120 }}>
                      <InputLabel>Country</InputLabel>
                      <Select
                        value={formData.country_code}
                        onChange={(e) => setFormData({ ...formData, country_code: e.target.value })}
                        label="Country"
                        disabled={loading}
                      >
                        <MenuItem value="+1">🇺🇸 +1</MenuItem>
                        <MenuItem value="+44">🇬🇧 +44</MenuItem>
                        <MenuItem value="+91">🇮🇳 +91</MenuItem>
                        <MenuItem value="+86">🇨🇳 +86</MenuItem>
                        <MenuItem value="+49">🇩🇪 +49</MenuItem>
                        <MenuItem value="+33">🇫🇷 +33</MenuItem>
                        <MenuItem value="+61">🇦🇺 +61</MenuItem>
                        <MenuItem value="+81">🇯🇵 +81</MenuItem>
                      </Select>
                    </FormControl>
                    <TextField
                      fullWidth
                      label="Phone Number"
                      value={formData.phone}
                      onChange={handleChange('phone')}
                      required
                      disabled={loading}
                    />
                  </Stack>

                  <TextField
                    fullWidth
                    label="Location"
                    placeholder="San Francisco, CA"
                    value={formData.location}
                    onChange={handleChange('location')}
                    required
                    disabled={loading}
                  />
                </>
              )}

              <Button
                type="submit"
                fullWidth
                variant="contained"
                size="large"
                disabled={loading}
                sx={{ 
                    py: 1.5, 
                    fontSize: '1.1rem', 
                    fontWeight: 'bold', 
                    borderRadius: 2,
                    mt: 2
                }}
              >
                {loading ? <CircularProgress size={24} color="inherit" /> : (isLogin ? 'Sign In' : 'Sign Up')}
              </Button>
            </Stack>
          </form>

          <Divider sx={{ width: '100%', my: 4 }}>
            <Typography variant="body2" color="text.secondary">OR</Typography>
          </Divider>

          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="body2">
              {isLogin ? "Don't have an account?" : "Already have an account?"}
              {' '}
              <Link 
                component="button" 
                variant="body2" 
                fontWeight="bold"
                onClick={() => setIsLogin(!isLogin)}
                sx={{ cursor: 'pointer', textDecoration: 'none' }}
              >
                {isLogin ? 'Sign Up' : 'Sign In'}
              </Link>
            </Typography>
          </Box>
        </Paper>
      </Container>

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
    </Box>
  );
}

export default Login;
