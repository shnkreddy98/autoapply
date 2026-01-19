import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Container, Typography, Paper, TextField, Button, Box } from '@mui/material';

const JobDetails = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [answer, setAnswer] = useState('');

  // In a real app, fetch job details by ID here.
  const companyName = id === '1' ? 'Google' : id === '2' ? 'Amazon' : 'Netflix';

  const handleSubmit = () => {
    alert(`Answer submitted for ${companyName}!`);
    navigate('/jobs');
  };

  return (
    <Container maxWidth="md" sx={{ mt: 8 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h5" gutterBottom>
          Additional Questions for {companyName}
        </Typography>
        <Typography variant="body1" paragraph>
          Please explain why you are a good fit for this role:
        </Typography>
        <TextField
          fullWidth
          multiline
          rows={6}
          variant="outlined"
          placeholder="Type your answer here..."
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          sx={{ mb: 3 }}
        />
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button variant="contained" onClick={handleSubmit}>
            Submit Answer
          </Button>
          <Button variant="outlined" onClick={() => navigate('/jobs')}>
            Cancel
          </Button>
        </Box>
      </Paper>
    </Container>
  );
};

export default JobDetails;
