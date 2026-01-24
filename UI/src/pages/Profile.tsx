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
  Alert
} from '@mui/material';
import axios from 'axios';
import type { ProfileData } from '../types';

const Profile = () => {
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [resumeId, setResumeId] = useState<number | null>(null);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success'
  });

  const fetchProfile = async (id?: number) => {
    setLoading(true);
    try {
      const url = id ? `http://localhost:8000/get-details?resume_id=${id}` : 'http://localhost:8000/get-details';
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
    fetchProfile(resumeId || undefined);
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
      const uploadResponse = await axios.post<{ path: string }>('http://localhost:8000/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const filePath = uploadResponse.data.path;

      // Step 2: Parse the resume
      const parseResponse = await axios.post<number>('http://localhost:8000/upload-resume', { path: filePath });
      const newResumeId = parseResponse.data;
      
      setResumeId(newResumeId);
      setSnackbar({ open: true, message: 'Resume uploaded and parsed successfully!', severity: 'success' });
      // fetchProfile will be triggered by useEffect when resumeId changes
    } catch (error) {
      console.error('Error uploading resume:', error);
      setSnackbar({ open: true, message: 'Failed to upload and parse resume.', severity: 'error' });
    } finally {
      setUploading(false);
    }
  };

  const handleSave = async () => {
    if (!profile) return;
    setSaving(true);
    try {
      // Assuming there is a save-details or similar endpoint, 
      // otherwise this is a placeholder for the intent.
      await axios.post('http://localhost:8000/save-details', profile);
      setSnackbar({ open: true, message: 'Profile saved successfully!', severity: 'success' });
    } catch (error) {
      console.error('Error saving profile:', error);
      setSnackbar({ open: true, message: 'Failed to save profile.', severity: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const updateContact = (field: keyof ProfileData['contact'], value: string) => {
    if (!profile) return;
    setProfile({
      ...profile,
      contact: { ...profile.contact, [field]: value }
    });
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
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button variant="outlined" component="label" disabled={uploading}>
            {uploading ? 'Uploading...' : 'Upload Resume'}
            <input type="file" hidden accept=".pdf,.doc,.docx" onChange={handleFileUpload} />
          </Button>
          <Button variant="contained" onClick={handleSave} disabled={saving || !profile}>
            {saving ? 'Saving...' : 'Save Changes'}
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
                    onChange={(e) => updateContact(field, e.target.value)}
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
                        onChange={(e) => {
                          const newExp = [...p.job_exp];
                          newExp[index] = { ...job, job_title: e.target.value };
                          setProfile({ ...p, job_exp: newExp });
                        }}
                      />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField
                        fullWidth
                        label="Company"
                        value={job.company_name || ''}
                        onChange={(e) => {
                          const newExp = [...p.job_exp];
                          newExp[index] = { ...job, company_name: e.target.value };
                          setProfile({ ...p, job_exp: newExp });
                        }}
                      />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField
                        fullWidth
                        label="From Date"
                        value={job.from_date || ''}
                        onChange={(e) => {
                          const newExp = [...p.job_exp];
                          newExp[index] = { ...job, from_date: e.target.value };
                          setProfile({ ...p, job_exp: newExp });
                        }}
                      />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField
                        fullWidth
                        label="To Date"
                        value={job.to_date || ''}
                        onChange={(e) => {
                          const newExp = [...p.job_exp];
                          newExp[index] = { ...job, to_date: e.target.value };
                          setProfile({ ...p, job_exp: newExp });
                        }}
                      />
                    </Grid>
                    <Grid size={12}>
                      <TextField
                        fullWidth
                        multiline
                        rows={3}
                        label="Description"
                        value={job.experience ? job.experience.join('\n') : ''}
                        onChange={(e) => {
                          const newExp = [...p.job_exp];
                          newExp[index] = { ...job, experience: e.target.value.split('\n') };
                          setProfile({ ...p, job_exp: newExp });
                        }}
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
                  onChange={(e) => {
                    const newSkills = [...p.skills];
                    newSkills[index] = { ...skill, skills: e.target.value };
                    setProfile({ ...p, skills: newSkills });
                  }}
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
                  onChange={(e) => {
                    const newEdu = [...p.education];
                    newEdu[index] = { ...edu, college: e.target.value };
                    setProfile({ ...p, education: newEdu });
                  }}
                />
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <TextField
                    fullWidth
                    label="Degree"
                    value={edu.degree || ''}
                    size="small"
                    onChange={(e) => {
                      const newEdu = [...p.education];
                      newEdu[index] = { ...edu, degree: e.target.value };
                      setProfile({ ...p, education: newEdu });
                    }}
                  />
                  <TextField
                    fullWidth
                    label="Major"
                    value={edu.major || ''}
                    size="small"
                    onChange={(e) => {
                      const newEdu = [...p.education];
                      newEdu[index] = { ...edu, major: e.target.value };
                      setProfile({ ...p, education: newEdu });
                    }}
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
                  onChange={(e) => {
                    const newCert = [...p.certification];
                    newCert[index] = { ...cert, title: e.target.value };
                    setProfile({ ...p, certification: newCert });
                  }}
                />
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <TextField
                    fullWidth
                    label="Obtained Date"
                    value={cert.obtained_date || ''}
                    size="small"
                    onChange={(e) => {
                      const newCert = [...p.certification];
                      newCert[index] = { ...cert, obtained_date: e.target.value };
                      setProfile({ ...p, certification: newCert });
                    }}
                  />
                  <TextField
                    fullWidth
                    label="Expiry Date"
                    value={cert.expiry_date || ''}
                    size="small"
                    onChange={(e) => {
                      const newCert = [...p.certification];
                      newCert[index] = { ...cert, expiry_date: e.target.value };
                      setProfile({ ...p, certification: newCert });
                    }}
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
