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
  Alert,
  Link,
  TextField,
  IconButton,
  Tooltip,
  Chip,
  Avatar
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import SearchIcon from '@mui/icons-material/Search';
import axios from 'axios';
import type { Job } from '../types';
import { formatLocalDateTime, toLocalISODate } from '../utils/dateUtils';
import { getApiUrl } from '../utils/api';

const Applications = () => {
  const navigate = useNavigate();
  const [selectedDate, setSelectedDate] = useState(() => toLocalISODate(new Date()));
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchJobs = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await axios.get(getApiUrl('/jobs'), {
          timeout: 5000,
          headers: { 'accept': 'application/json' }
        });
        setJobs(response.data);
      } catch (err) {
        console.error("Error fetching jobs:", err);
        setError("Failed to load jobs. Please ensure backend is running.");
      } finally {
        setLoading(false);
      }
    };

    fetchJobs();
  }, []);

  const filteredJobs = jobs.filter(job => toLocalISODate(job.date_applied) === selectedDate);

  const getStatusColor = (score: number) => {
    if (score > 85) return 'success';
    if (score > 70) return 'primary';
    return 'warning';
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', mb: 4 }}>
        <Box>
          <Typography variant="h3" fontWeight="bold" gutterBottom>
            Application Tracker
          </Typography>
          <Typography variant="h6" color="text.secondary">
            Monitor the status of your automated job applications.
          </Typography>
        </Box>
        <TextField
          label="Filter by Date"
          type="date"
          value={selectedDate}
          onChange={(e) => setSelectedDate(e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
          size="small"
          sx={{ minWidth: 200 }}
        />
      </Box>

      {loading ? (
        <Box sx={{ width: '100%', mt: 4 }}>
          <LinearProgress />
        </Box>
      ) : error ? (
        <Alert severity="error">{error}</Alert>
      ) : filteredJobs.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center', borderRadius: 3 }}>
          <Typography variant="h6" color="text.secondary">
            No applications found for {selectedDate}.
          </Typography>
          <Link href="/jobs" sx={{ mt: 2, display: 'inline-block' }}>Find some jobs to apply for!</Link>
        </Paper>
      ) : (
        <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3 }}>
          <Table>
            <TableHead sx={{ bgcolor: 'grey.50' }}>
              <TableRow>
                <TableCell sx={{ fontWeight: 'bold' }}>Company</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Role</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Match Score</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Status</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Applied Date</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }} align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredJobs.map((job, index) => (
                <TableRow
                  key={index}
                  hover
                  onClick={() => navigate('/jobs/chat', { state: { job } })}
                  sx={{ cursor: 'pointer', '&:last-child td, &:last-child th': { border: 0 } }}
                >
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Avatar sx={{ bgcolor: 'primary.light', width: 32, height: 32, fontSize: '0.875rem' }}>
                        {job.company_name.charAt(0)}
                      </Avatar>
                      <Typography variant="body1" fontWeight="medium">
                        {job.company_name}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>{job.role}</TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Box sx={{ flexGrow: 1, minWidth: 80 }}>
                        <LinearProgress
                          variant="determinate"
                          value={job.resume_score}
                          color={getStatusColor(job.resume_score)}
                          sx={{ height: 6, borderRadius: 3 }}
                        />
                      </Box>
                      <Typography variant="body2" fontWeight="bold">
                        {Math.round(job.resume_score)}%
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label="Applied" 
                      size="small" 
                      color="success" 
                      variant="outlined" 
                      sx={{ fontWeight: 'bold' }}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {formatLocalDateTime(job.date_applied)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                      <Tooltip title="View Job Post">
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            window.open(job.url, '_blank');
                          }}
                        >
                          <Link href={job.url} target="_blank" rel="noopener" sx={{ display: 'none' }} />
                          <SearchIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Download Submitted Resume">
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={(e) => {
                            e.stopPropagation();
                            window.open(getApiUrl(`/download-resume?url=${encodeURIComponent(job.url)}`), '_blank');
                          }}
                        >
                          <DownloadIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
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

export default Applications;
