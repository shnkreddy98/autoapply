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
  MenuItem
} from '@mui/material';
import axios from 'axios';
import type { Contact } from '../types';

function Login() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
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
    if (!formData.name.trim()) {
      setError('Name is required');
      return false;
    }
    if (!formData.email.trim()) {
      setError('Email is required');
      return false;
    }
    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
      setError('Please enter a valid email address');
      return false;
    }
    if (!formData.phone.trim()) {
      setError('Phone number is required');
      return false;
    }
    if (!formData.location.trim()) {
      setError('Location is required');
      return false;
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
      await axios.post('/api/save-user', formData);
      // Store all contact data in sessionStorage for the onboarding form
      sessionStorage.setItem('userEmail', formData.email);
      sessionStorage.setItem('userName', formData.name);
      sessionStorage.setItem('userPhone', formData.phone);
      sessionStorage.setItem('userCountryCode', formData.country_code);
      sessionStorage.setItem('userLocation', formData.location);
      navigate('/onboarding');
    } catch (err: any) {
      console.error('Error saving user:', err);
      setError(err.response?.data?.detail || 'Failed to save user information. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8, mb: 4 }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom align="center">
            Welcome to AutoApply
          </Typography>
          <Typography variant="body1" color="text.secondary" gutterBottom align="center" sx={{ mb: 3 }}>
            Let's get started by collecting your contact information
          </Typography>

          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Full Name"
              value={formData.name}
              onChange={handleChange('name')}
              margin="normal"
              required
              disabled={loading}
            />

            <TextField
              fullWidth
              label="Email Address"
              type="email"
              value={formData.email}
              onChange={handleChange('email')}
              margin="normal"
              required
              disabled={loading}
            />

            <Box sx={{ display: 'flex', gap: 2 }}>
              <FormControl sx={{ minWidth: 120 }} margin="normal">
                <InputLabel>Country</InputLabel>
                <Select
                  value={formData.country_code}
                  onChange={(e) => setFormData({ ...formData, country_code: e.target.value })}
                  label="Country"
                  disabled={loading}
                >
                  <MenuItem value="+1">🇺🇸 +1 (US)</MenuItem>
                  <MenuItem value="+44">🇬🇧 +44 (UK)</MenuItem>
                  <MenuItem value="+91">🇮🇳 +91 (India)</MenuItem>
                  <MenuItem value="+86">🇨🇳 +86 (China)</MenuItem>
                  <MenuItem value="+49">🇩🇪 +49 (Germany)</MenuItem>
                  <MenuItem value="+33">🇫🇷 +33 (France)</MenuItem>
                  <MenuItem value="+61">🇦🇺 +61 (Australia)</MenuItem>
                  <MenuItem value="+81">🇯🇵 +81 (Japan)</MenuItem>
                </Select>
              </FormControl>
              <TextField
                fullWidth
                label="Phone Number"
                value={formData.phone}
                onChange={handleChange('phone')}
                margin="normal"
                required
                disabled={loading}
                helperText="Enter without country code"
              />
            </Box>

            <TextField
              fullWidth
              label="Location"
              value={formData.location}
              onChange={handleChange('location')}
              margin="normal"
              required
              disabled={loading}
              helperText="e.g., San Francisco, CA"
            />

            <TextField
              fullWidth
              label="LinkedIn URL"
              value={formData.linkedin}
              onChange={handleChange('linkedin')}
              margin="normal"
              disabled={loading}
              helperText="Optional"
            />

            <TextField
              fullWidth
              label="GitHub URL"
              value={formData.github}
              onChange={handleChange('github')}
              margin="normal"
              disabled={loading}
              helperText="Optional"
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              size="large"
              disabled={loading}
              sx={{ mt: 3 }}
            >
              {loading ? <CircularProgress size={24} /> : 'Continue to Onboarding'}
            </Button>
          </form>
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
