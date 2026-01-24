import { useState } from 'react';
import { Container, Typography, TextField, Button, Box, Paper, Alert, CircularProgress } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const Home = () => {
  const [urls, setUrls] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const urlList = urls.split('\n').map(u => u.trim()).filter(u => u.length > 0);
      
      if (urlList.length === 0) {
        setError("Please enter at least one URL.");
        setLoading(false);
        return;
      }

      await axios.post('http://localhost:8000/applytojobs', {
        urls: urlList,
        resume_id: "4"
      }, {
        headers: {
          'accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
      
      // Navigate to jobs list on success
      navigate('/jobs');
    } catch (err) {
      console.error("Error submitting applications:", err);
      setError("Failed to submit applications. Please ensure the backend is running and try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="md" sx={{ mt: 8 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          AutoApply Setup
        </Typography>
        <Typography variant="body1" color="text.secondary" paragraph>
          Paste your job application URLs below (one per line).
        </Typography>
        
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box component="form" noValidate autoComplete="off">
          <TextField
            fullWidth
            multiline
            rows={10}
            variant="outlined"
            placeholder="https://example.com/job1&#10;https://example.com/job2"
            value={urls}
            onChange={(e) => setUrls(e.target.value)}
            disabled={loading}
            sx={{ mb: 2 }}
          />
          <Button 
            variant="contained" 
            size="large" 
            onClick={handleSubmit}
            disabled={!urls.trim() || loading}
            startIcon={loading ? <CircularProgress size={20} color="inherit" /> : null}
          >
            {loading ? 'Submitting...' : 'Submit Applications'}
          </Button>
        </Box>
      </Paper>
    </Container>
  );
};

export default Home;
