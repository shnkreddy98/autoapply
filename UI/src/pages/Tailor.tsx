import { useState, useEffect } from 'react';
import { Container, Typography, TextField, Button, Box, Paper, Alert, CircularProgress, MenuItem, Select, FormControl, InputLabel } from '@mui/material';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import axios from 'axios';
import { getApiUrl } from '../utils/api';

const Tailor = () => {
  const [urls, setUrls] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resumes, setResumes] = useState<number[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<string>('');
  const [fetchingResumes, setFetchingResumes] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchResumes = async () => {
      try {
        const response = await axios.get(getApiUrl('/list-resumes'));
        if (Array.isArray(response.data)) {
            setResumes(response.data);
            if (response.data.length > 0) {
                // Default to the first available ID
                setSelectedResumeId(String(response.data[0]));
            }
        }
      } catch (err) {
        console.error("Error fetching resumes:", err);
        setError("Could not load resumes. Please check backend.");
      } finally {
        setFetchingResumes(false);
      }
    };
    fetchResumes();
  }, []);

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

      if (!selectedResumeId) {
          setError("Please select a resume.");
          setLoading(false);
          return;
      }

      // Fire and forget - don't await the response
      axios.post(getApiUrl('/tailortojobs'), {
        urls: urlList,
        resume_id: selectedResumeId // sending as string as requested
      }, {
        headers: {
          'accept': 'application/json',
          'Content-Type': 'application/json'
        }
      }).catch(err => {
        console.error("Background application process error:", err);
      });
      
      // Navigate immediately
      navigate('/jobs');
    } catch (err) {
      console.error("Error initiating applications:", err);
      setError("Failed to initiate applications.");
      setLoading(false);
    }
  };

  if (fetchingResumes) {
      return (
        <Container maxWidth="md" sx={{ mt: 8, display: 'flex', justifyContent: 'center' }}>
            <CircularProgress />
        </Container>
      );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 8 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Tailor Resume
        </Typography>
        <Typography variant="body1" color="text.secondary" paragraph>
          Paste job URLs below to tailor your resume for each position (one per line).
        </Typography>
        
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {resumes.length === 0 ? (
             <Alert severity="warning" sx={{ mb: 2 }}>
                No resumes found. Please <Button color="inherit" component={RouterLink} to="/profile" size="small">upload a resume</Button> first.
             </Alert>
        ) : (
            <Box component="form" noValidate autoComplete="off">
            <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel id="resume-select-label">Select Resume ID</InputLabel>
                <Select
                    labelId="resume-select-label"
                    value={selectedResumeId}
                    label="Select Resume ID"
                    onChange={(e) => setSelectedResumeId(e.target.value)}
                >
                    {resumes.map((id) => (
                        <MenuItem key={id} value={String(id)}>
                            Resume #{id}
                        </MenuItem>
                    ))}
                </Select>
            </FormControl>

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
                disabled={!urls.trim() || loading || !selectedResumeId}
                startIcon={loading ? <CircularProgress size={20} color="inherit" /> : null}
            >
                {loading ? 'Tailoring...' : 'Tailor Resumes'}
            </Button>
            </Box>
        )}
      </Paper>
    </Container>
  );
};

export default Tailor;
