import { useState } from 'react';
import {
  Container,
  Typography,
  Box,
  Card,
  CardContent,
  Button,
  Grid,
  TextField,
  InputAdornment,
  Stack,
  CircularProgress,
  Alert,
  Link as MuiLink
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import BusinessIcon from '@mui/icons-material/Business';
import WorkIcon from '@mui/icons-material/Work';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { getApiUrl } from '../utils/api';

const JobList = () => {
  const [role, setRole] = useState('');
  const [company, setCompany] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobUrls, setJobUrls] = useState<string[]>([]);
  const [searched, setSearched] = useState(false);
  
  const navigate = useNavigate();

  const handleSearch = async () => {
    if (!role) {
      setError("Role is required.");
      return;
    }
    
    setLoading(true);
    setError(null);
    setSearched(true);
    
    try {
      const response = await axios.post(getApiUrl('/search-jobs'), {
        role: role,
        company: company || undefined,
        force: false,
        pages: 1
      });
      setJobUrls(response.data);
    } catch (err: any) {
      console.error("Search failed:", err);
      setError(err.response?.data?.detail || "Failed to search for jobs.");
    } finally {
      setLoading(false);
    }
  };

  const applyToAll = () => {
    navigate('/apply', { state: { urls: jobUrls.join('\n') } });
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h3" fontWeight="bold" gutterBottom>
          Find Your Next Role
        </Typography>
        <Typography variant="h6" color="text.secondary">
          Search for roles across top ATS platforms.
        </Typography>
      </Box>

      <Card elevation={2} sx={{ mb: 4, p: 2, borderRadius: 3 }}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              <TextField
                  fullWidth
                  label="Role (e.g. Software Engineer)"
                  variant="outlined"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  slotProps={{
                    input: {
                      startAdornment: <InputAdornment position="start"><WorkIcon color="action" /></InputAdornment>,
                    }
                  }}
                  required
              />
              <TextField
                  fullWidth
                  label="Company (Optional)"
                  variant="outlined"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  slotProps={{
                    input: {
                      startAdornment: <InputAdornment position="start"><BusinessIcon color="action" /></InputAdornment>,
                    }
                  }}
              />
              <Button 
                variant="contained" 
                size="large" 
                onClick={handleSearch}
                disabled={loading || !role}
                sx={{ minWidth: 150, borderRadius: 2 }}
                startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <SearchIcon />}
              >
                  {loading ? 'Searching...' : 'Search'}
              </Button>
          </Stack>
      </Card>

      {error && <Alert severity="error" sx={{ mb: 4 }}>{error}</Alert>}

      {searched && !loading && jobUrls.length === 0 && !error && (
          <Alert severity="info">No jobs found for your criteria.</Alert>
      )}

      {jobUrls.length > 0 && (
          <Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h5" fontWeight="bold">Results ({jobUrls.length})</Typography>
                  <Button variant="contained" color="secondary" onClick={applyToAll}>
                      Apply to All Found
                  </Button>
              </Box>
              
              <Grid container spacing={2}>
                  {jobUrls.map((url, idx) => {
                      let domain = "Unknown";
                      try {
                          domain = new URL(url).hostname;
                      } catch(e) {}
                      return (
                          <Grid size={{ xs: 12 }} key={idx}>
                              <Card variant="outlined" sx={{ '&:hover': { boxShadow: 2 } }}>
                                  <CardContent sx={{ py: 2 }}>
                                      <Stack direction="row" justifyContent="space-between" alignItems="center">
                                          <Box sx={{ overflow: 'hidden', textOverflow: 'ellipsis', pr: 2 }}>
                                              <Typography variant="subtitle2" color="primary" sx={{ mb: 0.5 }}>{domain}</Typography>
                                              <MuiLink href={url} target="_blank" rel="noopener" color="inherit" underline="hover" sx={{ display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: { xs: '200px', sm: '400px', md: '800px' } }}>
                                                  {url}
                                              </MuiLink>
                                          </Box>
                                          <Button variant="outlined" size="small" onClick={() => navigate('/apply', { state: { urls: url } })}>
                                              Apply
                                          </Button>
                                      </Stack>
                                  </CardContent>
                              </Card>
                          </Grid>
                      )
                  })}
              </Grid>
          </Box>
      )}
    </Container>
  );
};

export default JobList;
