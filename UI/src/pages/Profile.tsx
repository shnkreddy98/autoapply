import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Paper,
  Grid,
  TextField,
  Button,
  Box,
  Card,
  CardContent,
  CircularProgress,
  Snackbar,
  Alert,
  MenuItem,
  Select,
  FormControl,
  InputLabel
} from '@mui/material';
import axios from 'axios';
import type { ProfileData } from '../types';

const Profile = () => {
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [resumeId, setResumeId] = useState<string>('');
  const [resumes, setResumes] = useState<number[]>([]);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success'
  });

  useEffect(() => {
    const fetchResumes = async () => {
      try {
        const response = await axios.get('/api/list-resumes');
        if (Array.isArray(response.data)) {
            setResumes(response.data);
            if (response.data.length > 0 && !resumeId) {
                // Default to the first available ID if none selected
                setResumeId(String(response.data[0]));
            }
        }
      } catch (err) {
        console.error("Error fetching resumes:", err);
        setSnackbar({ open: true, message: 'Failed to load resume list.', severity: 'error' });
      }
    };
    fetchResumes();
  }, []); // Run once on mount

  const fetchProfile = async (id: string) => {
    if (!id) return;
    setLoading(true);
    try {
      const url = `/api/get-details?resume_id=${id}`;
      const response = await axios.get<ProfileData>(url);
      if (response.data) {
        setProfile(response.data);
      }
    } catch (error) {
      console.error('Error fetching profile:', error);
      setSnackbar({ open: true, message: 'Failed to fetch profile details.', severity: 'error' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (resumeId) {
        fetchProfile(resumeId);
    }
  }, [resumeId]);

  const handleCloseSnackbar = () => setSnackbar({ ...snackbar, open: false });

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!event.target.files || event.target.files.length === 0) return;

    const file = event.target.files[0];
    const formData = new FormData();
    formData.append('file', file);

    setUploading(true);
    try {
      // Step 1: Upload the file
      const uploadResponse = await axios.post<{ path: string }>('/api/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const filePath = uploadResponse.data.path;

      // Step 2: Parse the resume
      const parseResponse = await axios.post<number>('/api/upload-resume', { path: filePath });
      const newResumeId = parseResponse.data;
      
      setResumeId(String(newResumeId));
      
      // Refresh list to include new resume
      const listResponse = await axios.get('/api/list-resumes');
      if (Array.isArray(listResponse.data)) {
          setResumes(listResponse.data);
      }

      setSnackbar({ open: true, message: 'Resume uploaded and parsed successfully!', severity: 'success' });
    } catch (error) {
      console.error('Error uploading resume:', error);
      setSnackbar({ open: true, message: 'Failed to upload and parse resume.', severity: 'error' });
    } finally {
      setUploading(false);
    }
  };

  if (loading && !profile) {
    return (
      <Container sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Container>
    );
  }

  const p = profile || {
    contact: { name: '', email: '', location: '', phone: '', linkedin: '', github: '' },
    job_exp: [],
    skills: [],
    education: [],
    certification: []
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Profile</Typography>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel id="resume-select-label">Resume</InputLabel>
            <Select
                labelId="resume-select-label"
                value={resumeId}
                label="Resume"
                onChange={(e) => setResumeId(e.target.value)}
            >
                {resumes.map((id) => (
                    <MenuItem key={id} value={String(id)}>
                        Resume #{id}
                    </MenuItem>
                ))}
            </Select>
          </FormControl>
          <Button variant="contained" component="label" disabled={uploading}>
            {uploading ? 'Uploading...' : 'Upload New Resume'}
            <input type="file" hidden accept=".pdf,.doc,.docx" onChange={handleFileUpload} />
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        <Grid size={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>Contact Information</Typography>
            <Grid container spacing={2}>
              {(['name', 'email', 'phone', 'location', 'linkedin', 'github'] as const).map((field) => (
                <Grid size={{ xs: 12, sm: 6 }} key={field}>
                  <TextField
                    fullWidth
                    label={field.charAt(0).toUpperCase() + field.slice(1)}
                    value={p.contact[field] || ''}
                    slotProps={{ input: { readOnly: true } }}
                  />
                </Grid>
              ))}
            </Grid>
          </Paper>
        </Grid>

        {/* Experience */}
        <Grid size={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>Experience</Typography>
            {p.job_exp.map((job, index) => (
              <Card key={index} variant="outlined" sx={{ mb: 2 }}>
                <CardContent>
                  <Grid container spacing={2}>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField
                        fullWidth
                        label="Job Title"
                        value={job.job_title || ''}
                        slotProps={{ input: { readOnly: true } }}
                      />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField
                        fullWidth
                        label="Company"
                        value={job.company_name || ''}
                        slotProps={{ input: { readOnly: true } }}
                      />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField
                        fullWidth
                        label="From Date"
                        value={job.from_date ? new Date(job.from_date).toLocaleDateString() : ''}
                        slotProps={{ input: { readOnly: true } }}
                      />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField
                        fullWidth
                        label="To Date"
                        value={job.to_date && !['present', 'current'].includes(job.to_date.toLowerCase()) 
                          ? new Date(job.to_date).toLocaleDateString() 
                          : job.to_date || ''}
                        slotProps={{ input: { readOnly: true } }}
                      />
                    </Grid>
                    <Grid size={12}>
                      <TextField
                        fullWidth
                        multiline
                        rows={3}
                        label="Description"
                        value={job.experience ? job.experience.join('\n') : ''}
                        slotProps={{ input: { readOnly: true } }}
                      />
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            ))}
          </Paper>
        </Grid>

        {/* Skills */}
        <Grid size={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>Skills</Typography>
            {p.skills.map((skill, index) => (
              <Box key={index} sx={{ mb: 2 }}>
                <Typography variant="subtitle2">{skill.title}</Typography>
                <TextField
                  fullWidth
                  value={skill.skills || ''}
                  slotProps={{ input: { readOnly: true } }}
                />
              </Box>
            ))}
          </Paper>
        </Grid>

        {/* Education */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>Education</Typography>
            {p.education.map((edu, index) => (
              <Box key={index} sx={{ mb: 2, pb: 2, borderBottom: '1px solid #eee' }}>
                <TextField
                  fullWidth
                  label="College"
                  value={edu.college || ''}
                  size="small"
                  sx={{ mb: 1 }}
                  slotProps={{ input: { readOnly: true } }}
                />
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <TextField
                    fullWidth
                    label="Degree"
                    value={edu.degree || ''}
                    size="small"
                    slotProps={{ input: { readOnly: true } }}
                  />
                  <TextField
                    fullWidth
                    label="Major"
                    value={edu.major || ''}
                    size="small"
                    slotProps={{ input: { readOnly: true } }}
                  />
                </Box>
                <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                  <TextField
                    fullWidth
                    label="From Date"
                    value={edu.from_date ? new Date(edu.from_date).toLocaleDateString() : ''}
                    size="small"
                    slotProps={{ input: { readOnly: true } }}
                  />
                  <TextField
                    fullWidth
                    label="To Date"
                    value={edu.to_date ? new Date(edu.to_date).toLocaleDateString() : ''}
                    size="small"
                    slotProps={{ input: { readOnly: true } }}
                  />
                </Box>
              </Box>
            ))}
          </Paper>
        </Grid>

        {/* Certifications */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>Certifications</Typography>
            {p.certification.map((cert, index) => (
              <Box key={index} sx={{ mb: 2, pb: 2, borderBottom: '1px solid #eee' }}>
                <TextField
                  fullWidth
                  label="Certification Title"
                  value={cert.title || ''}
                  size="small"
                  sx={{ mb: 1 }}
                  slotProps={{ input: { readOnly: true } }}
                />
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <TextField
                    fullWidth
                    label="Obtained Date"
                    value={cert.obtained_date ? new Date(cert.obtained_date).toLocaleDateString() : ''}
                    size="small"
                    slotProps={{ input: { readOnly: true } }}
                  />
                  <TextField
                    fullWidth
                    label="Expiry Date"
                    value={cert.expiry_date && !['n/a', 'none'].includes(cert.expiry_date.toLowerCase()) 
                      ? new Date(cert.expiry_date).toLocaleDateString() 
                      : cert.expiry_date || ''}
                    size="small"
                    slotProps={{ input: { readOnly: true } }}
                  />
                </Box>
              </Box>
            ))}
          </Paper>
        </Grid>
      </Grid>

      <Snackbar open={snackbar.open} autoHideDuration={6000} onClose={handleCloseSnackbar}>
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} sx={{ width: '100%' }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default Profile;
