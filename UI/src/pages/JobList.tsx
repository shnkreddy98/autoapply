import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Container, 
  Typography, 
  Box, 
  LinearProgress, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Paper, 
  CircularProgress,
  Alert,
  Link,
  TextField
} from '@mui/material';
import axios from 'axios';
import type { Job } from '../types';
import { formatLocalDateTime, toLocalISODate } from '../utils/dateUtils';

const JobList = () => {
  const navigate = useNavigate();
  // Initialize with local date string YYYY-MM-DD
  const [selectedDate, setSelectedDate] = useState(() => toLocalISODate(new Date()));

  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchJobs = async () => {
      setLoading(true);
      setError(null);
      try {
        // Fetch all jobs to handle local timezone filtering in the frontend
        const response = await axios.get('/api/jobs', {
          headers: {
            'accept': 'application/json'
          }
        });
        setJobs(response.data);
      } catch (err) {
        console.error("Error fetching jobs:", err);
        setError("Failed to load jobs. Please check if the backend is running.");
      } finally {
        setLoading(false);
      }
    };

    fetchJobs();

    // Set up polling interval (every 30 seconds)
    const intervalId = setInterval(() => {
        axios.get('/api/jobs', {
          headers: { 'accept': 'application/json' }
        })
        .then(response => setJobs(response.data))
        .catch(err => console.error("Poll error:", err));
    }, 30000);

    return () => clearInterval(intervalId);
  }, []); // Only fetch once on mount, then poll

  const filteredJobs = jobs.filter(job => toLocalISODate(job.date_applied) === selectedDate);

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" gutterBottom sx={{ mb: 0 }}>
          Application History
        </Typography>
        <Box>
           <TextField
            label="Filter by Date"
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            slotProps={{
                inputLabel: {
                shrink: true,
                }
            }}
            size="small"
          />
        </Box>
      </Box>
      
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
            <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error">{error}</Alert>
      ) : filteredJobs.length === 0 ? (
        <Alert severity="info">No applications found for {selectedDate}.</Alert>
      ) : (
        <TableContainer component={Paper} elevation={3}>
          <Table>
            <TableHead sx={{ bgcolor: 'primary.main' }}>
              <TableRow>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Company</TableCell>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Role</TableCell>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Resume Match</TableCell>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Date Applied</TableCell>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Links</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredJobs.map((job, index) => (
                <TableRow 
                  key={index} 
                  hover 
                  onClick={() => navigate('/jobs/chat', { state: { job } })}
                  sx={{ cursor: 'pointer' }}
                >
                  <TableCell sx={{ fontWeight: 'medium' }}>{job.company_name}</TableCell>
                  <TableCell>{job.role}</TableCell>
                  <TableCell sx={{ minWidth: 150 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Box sx={{ width: '100%', mr: 1 }}>
                        <LinearProgress 
                          variant="determinate" 
                          value={job.resume_score} 
                          color={job.resume_score > 80 ? "success" : "primary"}
                          sx={{ height: 8, borderRadius: 5 }}
                        />
                      </Box>
                      <Box sx={{ minWidth: 35 }}>
                        <Typography variant="body2" color="text.secondary">
                          {Math.round(job.resume_score)}%
                        </Typography>
                      </Box>
                    </Box>
                  </TableCell>
                  <TableCell>
                    {formatLocalDateTime(job.date_applied)}
                  </TableCell>
                  <TableCell>
                    <Link 
                      href={job.url} 
                      target="_blank" 
                      rel="noopener" 
                      sx={{ mr: 2 }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      Job Post
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Container>
  );
};

export default JobList;