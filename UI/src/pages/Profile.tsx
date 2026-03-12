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
  InputLabel,
  Tabs,
  Tab,
  Stack,
  Divider,
  Avatar,
  } from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import axios from 'axios';
import type { ProfileData, UserOnboarding } from '../types';
import { formatLocalDate } from '../utils/dateUtils';
import { getApiUrl } from '../utils/api';
import { EmploymentType, YesNoNA } from '../types';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`profile-tabpanel-${index}`}
      aria-labelledby={`profile-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ py: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const Profile = () => {
  const [tabValue, setTabValue] = useState(0);
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [onboarding, setOnboarding] = useState<UserOnboarding | null>(null);
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
        const response = await axios.get(getApiUrl('/list-resumes'));
        if (Array.isArray(response.data)) {
            setResumes(response.data);
            if (response.data.length > 0 && !resumeId) {
                setResumeId(String(response.data[0]));
            }
        }
      } catch (err) {
        console.error("Error fetching resumes:", err);
      }
    };
    
    const savedOnboarding = sessionStorage.getItem('onboardingData');
    if (savedOnboarding) {
        setOnboarding(JSON.parse(savedOnboarding));
    } else {
        setOnboarding({
            full_name: 'No Name',
            email_address: 'No Email',
            phone_number: '',
            street_address: '',
            city: '',
            state: '',
            zip_code: '',
            age_18_or_older: false,
            work_eligible_us: false,
            visa_sponsorship: false,
            available_start_date: '',
            employment_type: EmploymentType.FULL_TIME,
            willing_relocate: false,
            willing_travel: false,
            desired_salary: '',
            current_employee: false,
            ever_terminated: false,
            security_clearance: YesNoNA.NA,
            cert_accuracy: false,
            cert_dismissal: false,
            cert_background_check: false,
            cert_drug_testing: false,
            cert_at_will: false,
            cert_job_description: false,
            cert_privacy_notice: false,
            cert_data_processing: false,
            electronic_signature: '',
            signature_date: ''
        });
    }

    fetchResumes();
  }, []);

  const fetchProfile = async (id: string) => {
    if (!id) return;
        try {
      const response = await axios.get<ProfileData>(getApiUrl(`/get-details?resume_id=${id}`));
      if (response.data) {
        setProfile(response.data);
      }
    } catch (error) {
      console.error('Error fetching profile:', error);
      // If error, we might still have partial data or just show empty
    } finally {
          }
  };

  useEffect(() => {
    if (resumeId) {
        fetchProfile(resumeId);
    }
  }, [resumeId]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!event.target.files || event.target.files.length === 0) return;
    const file = event.target.files[0];
    if (!file.name.toLowerCase().endsWith('.docx')) {
      setSnackbar({ open: true, message: 'Please upload a .docx file.', severity: 'error' });
      return;
    }
    const userEmail = localStorage.getItem('userEmail') || onboarding?.email_address;
    if (!userEmail) {
      setSnackbar({ open: true, message: 'User email not found.', severity: 'error' });
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    setUploading(true);
    try {
      const uploadResponse = await axios.post<{ resume_id: number; path: string }>(
        getApiUrl(`/upload?user_email=${encodeURIComponent(userEmail)}`),
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      const parseResponse = await axios.post<number>(getApiUrl('/upload-resume'), { path: uploadResponse.data.path });
      const newId = parseResponse.data;
      setResumes(prev => prev.includes(newId) ? prev : [...prev, newId]);
      setResumeId(String(newId));
      setSnackbar({ open: true, message: 'Resume uploaded successfully!', severity: 'success' });
    } catch (error) {
      setSnackbar({ open: true, message: 'Failed to upload resume.', severity: 'error' });
    } finally {
      setUploading(false);
    }
  };

  const p = profile || {
    contact: { name: '', email: '', location: '', phone: '', linkedin: '', github: '' },
    job_exp: [],
    skills: [],
    education: [],
    certifications: [],
    projects: [],
    achievements: []
  };

  const o = onboarding;

  if (!o) {
      return (
          <Container sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
              <CircularProgress />
          </Container>
      );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Paper elevation={0} sx={{ p: 4, mb: 4, borderRadius: 3, border: '1px solid', borderColor: 'divider' }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3} alignItems="center">
          <Avatar 
            sx={{ width: 100, height: 100, bgcolor: 'primary.main', fontSize: '2.5rem' }}
          >
            {(o.full_name || 'U').charAt(0)}
          </Avatar>
          <Box sx={{ textAlign: { xs: 'center', sm: 'left' }, flexGrow: 1 }}>
            <Typography variant="h4" fontWeight="bold">{o.full_name || 'User'}</Typography>
            <Typography variant="h6" color="text.secondary">{o.email_address || 'No Email'} • {o.phone_number || 'No Phone'}</Typography>
            <Stack direction="row" spacing={1} sx={{ mt: 1, justifyContent: { xs: 'center', sm: 'flex-start' } }}>
              <Button size="small" variant="outlined" startIcon={<EditIcon />}>Edit Profile</Button>
              <FormControl size="small" sx={{ minWidth: 150 }}>
                <InputLabel>Active Resume</InputLabel>
                <Select
                    value={resumeId}
                    label="Active Resume"
                    onChange={(e) => setResumeId(e.target.value)}
                >
                    {resumes.map((id) => <MenuItem key={id} value={String(id)}>Resume #{id}</MenuItem>)}
                </Select>
              </FormControl>
            </Stack>
          </Box>
          <Box>
            <Button 
                variant="contained" 
                component="label" 
                startIcon={uploading ? <CircularProgress size={20} color="inherit" /> : <CloudUploadIcon />}
                disabled={uploading}
                sx={{ borderRadius: 2 }}
            >
              Upload Resume
              <input type="file" hidden accept=".docx" onChange={handleFileUpload} />
            </Button>
          </Box>
        </Stack>
      </Paper>

      <Box sx={{ width: '100%' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="profile tabs">
            <Tab label="Resume Details" />
            <Tab label="Application Preferences" />
            <Tab label="Settings" />
          </Tabs>
        </Box>

        <TabPanel value={tabValue} index={0}>
          <Grid container spacing={3}>
            {/* Experience */}
            <Grid size={12}>
                <Typography variant="h5" fontWeight="bold" gutterBottom>Work Experience</Typography>
                {(p.job_exp || []).map((job, idx) => (
                    <Card key={idx} variant="outlined" sx={{ mb: 2, borderRadius: 2 }}>
                        <CardContent>
                            <Typography variant="h6">{job.job_title}</Typography>
                            <Typography variant="subtitle1" color="primary">{job.company_name}</Typography>
                            <Typography variant="caption" color="text.secondary">
                                {formatLocalDate(job.from_date)} - {job.to_date}
                            </Typography>
                            <Box sx={{ mt: 1 }}>
                                {(job.experience || []).map((bullet, i) => (
                                    <Typography key={i} variant="body2" sx={{ mb: 0.5 }}>• {bullet}</Typography>
                                ))}
                            </Box>
                        </CardContent>
                    </Card>
                ))}
            </Grid>
            {/* Skills */}
            <Grid size={{ xs: 12, md: 6 }}>
                <Paper variant="outlined" sx={{ p: 3, borderRadius: 2 }}>
                    <Typography variant="h6" fontWeight="bold" gutterBottom>Skills</Typography>
                    {(p.skills || []).map((s, idx) => (
                        <Box key={idx} sx={{ mb: 2 }}>
                            <Typography variant="subtitle2" color="text.secondary">{s.title}</Typography>
                            <Typography variant="body1">{s.skills}</Typography>
                        </Box>
                    ))}
                </Paper>
            </Grid>
            {/* Education */}
            <Grid size={{ xs: 12, md: 6 }}>
                <Paper variant="outlined" sx={{ p: 3, borderRadius: 2 }}>
                    <Typography variant="h6" fontWeight="bold" gutterBottom>Education</Typography>
                    {(p.education || []).map((edu, idx) => (
                        <Box key={idx} sx={{ mb: 2 }}>
                            <Typography variant="subtitle1" fontWeight="bold">{edu.degree} in {edu.major}</Typography>
                            <Typography variant="body2">{edu.college}</Typography>
                            <Typography variant="caption" color="text.secondary">{formatLocalDate(edu.from_date)} - {formatLocalDate(edu.to_date)}</Typography>
                        </Box>
                    ))}
                </Paper>
            </Grid>
          </Grid>
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 6 }}>
                <Paper variant="outlined" sx={{ p: 3, borderRadius: 2 }}>
                    <Typography variant="h6" fontWeight="bold" gutterBottom>Work Preferences</Typography>
                    <Stack spacing={2}>
                        <TextField fullWidth label="Desired Salary" value={o.desired_salary} slotProps={{ input: { readOnly: true } }} />
                        <TextField fullWidth label="Employment Type" value={o.employment_type} slotProps={{ input: { readOnly: true } }} />
                        <TextField fullWidth label="Available Start Date" value={o.available_start_date} slotProps={{ input: { readOnly: true } }} />
                        <Box sx={{ display: 'flex', gap: 2 }}>
                            <TextField fullWidth label="Willing to Relocate" value={o.willing_relocate ? 'Yes' : 'No'} slotProps={{ input: { readOnly: true } }} />
                            <TextField fullWidth label="Willing to Travel" value={o.willing_travel ? `Yes (${o.travel_percentage})` : 'No'} slotProps={{ input: { readOnly: true } }} />
                        </Box>
                    </Stack>
                </Paper>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
                <Paper variant="outlined" sx={{ p: 3, borderRadius: 2 }}>
                    <Typography variant="h6" fontWeight="bold" gutterBottom>Personal & Legal</Typography>
                    <Stack spacing={2}>
                        <TextField fullWidth label="Work Eligibility US" value={o.work_eligible_us ? 'Authorized' : 'Not Authorized'} slotProps={{ input: { readOnly: true } }} />
                        <TextField fullWidth label="Visa Sponsorship" value={o.visa_sponsorship ? 'Required' : 'Not Required'} slotProps={{ input: { readOnly: true } }} />
                        <TextField fullWidth label="Security Clearance" value={o.security_clearance} slotProps={{ input: { readOnly: true } }} />
                        <Divider sx={{ my: 1 }} />
                        <Typography variant="subtitle2" color="text.secondary">EEO Data (Optional)</Typography>
                        <Box sx={{ display: 'flex', gap: 2 }}>
                            <TextField fullWidth label="Gender" value={o.gender} size="small" slotProps={{ input: { readOnly: true } }} />
                            <TextField fullWidth label="Race" value={o.race_ethnicity} size="small" slotProps={{ input: { readOnly: true } }} />
                        </Box>
                    </Stack>
                </Paper>
            </Grid>
          </Grid>
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
           <Paper variant="outlined" sx={{ p: 4, borderRadius: 3, textAlign: 'center' }}>
                <Typography variant="h6">Account Settings</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    Manage your account connections and notification preferences.
                </Typography>
                <Button variant="outlined" color="error">Sign Out</Button>
           </Paper>
        </TabPanel>
      </Box>

      <Snackbar open={snackbar.open} autoHideDuration={6000} onClose={() => setSnackbar({ ...snackbar, open: false })}>
        <Alert severity={snackbar.severity} sx={{ width: '100%' }}>{snackbar.message}</Alert>
      </Snackbar>
    </Container>
  );
};

export default Profile;
