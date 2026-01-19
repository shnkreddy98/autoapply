import { useState } from 'react';
import { Container, Typography, TextField, Button, Box, Paper } from '@mui/material';
import { useNavigate } from 'react-router-dom';

const Home = () => {
  const [urls, setUrls] = useState('');
  const navigate = useNavigate();

  const handleSubmit = () => {
    // In a real app, you would send this to the backend here.
    // For now, we'll just navigate to the list view.
    console.log('Submitting URLs:', urls.split('\n'));
    navigate('/jobs');
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
        <Box component="form" noValidate autoComplete="off">
          <TextField
            fullWidth
            multiline
            rows={10}
            variant="outlined"
            placeholder="https://example.com/job1&#10;https://example.com/job2"
            value={urls}
            onChange={(e) => setUrls(e.target.value)}
            sx={{ mb: 2 }}
          />
          <Button 
            variant="contained" 
            size="large" 
            onClick={handleSubmit}
            disabled={!urls.trim()}
          >
            Submit Applications
          </Button>
        </Box>
      </Paper>
    </Container>
  );
};

export default Home;
