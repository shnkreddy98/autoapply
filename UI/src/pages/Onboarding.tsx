import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  Stepper,
  Step,
  StepLabel,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Checkbox,
    Snackbar,
  Alert,
  CircularProgress,
    Divider,
  Stack,
  Card,
  } from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import axios from 'axios';
import { getApiUrl } from '../utils/api';
import type { UserOnboarding } from '../types';
import {
  EmploymentType,
  Gender,
  RaceEthnicity,
    YesNoNA
} from '../types';

const steps = [
  'Personal',
  'Work & Position',
  'EEO (Optional)',
  'History',
  'Requirements',
  'Finish'
];

function Onboarding() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const [formData, setFormData] = useState<UserOnboarding>({
    full_name: '',
    street_address: '',
    city: '',
    state: '',
    zip_code: '',
    phone_number: '',
    email_address: '',
    date_of_birth: '',
    age_18_or_older: false,
    work_eligible_us: true,
    visa_sponsorship: false,
    available_start_date: new Date().toISOString().split('T')[0],
    employment_type: EmploymentType.FULL_TIME,
    willing_relocate: false,
    willing_travel: false,
    travel_percentage: '',
    desired_salary: '',
    gender: undefined,
    race_ethnicity: undefined,
    veteran_status: undefined,
    disability_status: undefined,
    current_employee: false,
    ever_terminated: false,
    termination_explanation: '',
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
    signature_date: new Date().toISOString().split('T')[0]
  });

  useEffect(() => {
    const email = sessionStorage.getItem('userEmail');
    const name = sessionStorage.getItem('userName');
    const phone = sessionStorage.getItem('userPhone');
    const countryCode = sessionStorage.getItem('userCountryCode');
    const location = sessionStorage.getItem('userLocation');

    const updates: Partial<UserOnboarding> = {};
    if (email) updates.email_address = email;
    if (name) {
      updates.full_name = name;
      updates.electronic_signature = name;
    }
    if (phone && countryCode) updates.phone_number = `${countryCode} ${phone}`;
    if (location) {
      const locationParts = location.split(',').map(s => s.trim());
      if (locationParts.length >= 2) {
        updates.city = locationParts[0];
        updates.state = locationParts[1];
      } else if (locationParts.length === 1) {
        updates.city = locationParts[0];
      }
    }
    if (Object.keys(updates).length > 0) {
      setFormData(prev => ({ ...prev, ...updates }));
    }
  }, []);

  const handleChange = (field: keyof UserOnboarding) => (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setFormData({ ...formData, [field]: value });
    if (errors[field]) {
      const newErrors = { ...errors };
      delete newErrors[field];
      setErrors(newErrors);
    }
  };

  const handleSelectChange = (field: keyof UserOnboarding) => (e: SelectChangeEvent) => {
    setFormData({ ...formData, [field]: e.target.value });
    if (errors[field]) {
      const newErrors = { ...errors };
      delete newErrors[field];
      setErrors(newErrors);
    }
  };

  const validateStep = (step: number): boolean => {
    const newErrors: Record<string, string> = {};
    if (step === 0) {
        if (!formData.full_name.trim()) newErrors.full_name = 'Full name is required';
        if (!formData.email_address.trim()) newErrors.email_address = 'Email is required';
        if (!formData.age_18_or_older) newErrors.age_18_or_older = 'Required';
    } else if (step === 1) {
        if (!formData.desired_salary.trim()) newErrors.desired_salary = 'Desired salary is required';
    } else if (step === 4) {
        if (!formData.cert_accuracy) newErrors.cert_accuracy = 'Agreement required';
    } else if (step === 5) {
        if (!formData.electronic_signature.trim()) newErrors.electronic_signature = 'Signature required';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (validateStep(currentStep)) setCurrentStep(prev => prev + 1);
  };

  const handleBack = () => setCurrentStep(prev => prev - 1);

  const handleSubmit = async () => {
    if (!validateStep(currentStep)) return;
    setLoading(true);
    setError('');
    try {
      // Actual API call
      await axios.post(getApiUrl('/user-form'), formData);
      
      // Save email to localStorage and clear session
      localStorage.setItem('userEmail', formData.email_address);
      sessionStorage.setItem('onboardingData', JSON.stringify(formData));
      
      navigate('/jobs');
    } catch (err: any) {
      console.error('Error saving user form:', err);
      setError(err.response?.data?.detail || 'An error occurred during submission.');
    } finally {
      setLoading(false);
    }
  };

  const renderStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <Stack spacing={3}>
            <Typography variant="h5" fontWeight="bold">Personal Details</Typography>
            <TextField fullWidth label="Full Name" value={formData.full_name} onChange={handleChange('full_name')} error={!!errors.full_name} required />
            <TextField fullWidth label="Street Address" value={formData.street_address} onChange={handleChange('street_address')} />
            <Stack direction="row" spacing={2}>
              <TextField fullWidth label="City" value={formData.city} onChange={handleChange('city')} />
              <TextField fullWidth label="State" value={formData.state} onChange={handleChange('state')} />
              <TextField fullWidth label="ZIP" value={formData.zip_code} onChange={handleChange('zip_code')} />
            </Stack>
            <TextField fullWidth label="Phone" value={formData.phone_number} onChange={handleChange('phone_number')} />
            <TextField fullWidth label="Email" value={formData.email_address} onChange={handleChange('email_address')} error={!!errors.email_address} required />
            <FormControlLabel
              control={<Checkbox checked={formData.age_18_or_older} onChange={handleChange('age_18_or_older')} />}
              label="I am 18 years of age or older"
            />
          </Stack>
        );
      case 1:
        return (
          <Stack spacing={3}>
            <Typography variant="h5" fontWeight="bold">Work & Position</Typography>
            <Stack direction="row" spacing={2}>
                <FormControlLabel control={<Checkbox checked={formData.work_eligible_us} onChange={handleChange('work_eligible_us')} />} label="Eligible to work in US" />
                <FormControlLabel control={<Checkbox checked={formData.visa_sponsorship} onChange={handleChange('visa_sponsorship')} />} label="Require Sponsorship" />
            </Stack>
            <TextField fullWidth label="Start Date" type="date" value={formData.available_start_date} onChange={handleChange('available_start_date')} InputLabelProps={{ shrink: true }} />
            <FormControl fullWidth>
              <InputLabel>Employment Type</InputLabel>
              <Select value={formData.employment_type} onChange={handleSelectChange('employment_type')} label="Employment Type">
                <MenuItem value={EmploymentType.FULL_TIME}>Full-time</MenuItem>
                <MenuItem value={EmploymentType.PART_TIME}>Part-time</MenuItem>
                <MenuItem value={EmploymentType.EITHER}>Either</MenuItem>
              </Select>
            </FormControl>
            <TextField fullWidth label="Desired Salary" value={formData.desired_salary} onChange={handleChange('desired_salary')} error={!!errors.desired_salary} required placeholder="e.g. $150,000" />
            <Stack direction="row" spacing={2}>
                <FormControlLabel control={<Checkbox checked={formData.willing_relocate} onChange={handleChange('willing_relocate')} />} label="Willing to Relocate" />
                <FormControlLabel control={<Checkbox checked={formData.willing_travel} onChange={handleChange('willing_travel')} />} label="Willing to Travel" />
            </Stack>
          </Stack>
        );
      case 2:
        return (
          <Stack spacing={3}>
            <Typography variant="h5" fontWeight="bold">EEO Information</Typography>
            <Typography variant="body2" color="text.secondary">This information is voluntary and used for diversity tracking.</Typography>
            <FormControl fullWidth>
              <InputLabel>Gender</InputLabel>
              <Select value={formData.gender || ''} onChange={handleSelectChange('gender')} label="Gender">
                <MenuItem value={Gender.MALE}>Male</MenuItem>
                <MenuItem value={Gender.FEMALE}>Female</MenuItem>
                <MenuItem value={Gender.NON_BINARY}>Non-binary</MenuItem>
                <MenuItem value={Gender.PREFER_NOT_TO_ANSWER}>Prefer not to answer</MenuItem>
              </Select>
            </FormControl>
            <FormControl fullWidth>
                <InputLabel>Race/Ethnicity</InputLabel>
                <Select value={formData.race_ethnicity || ''} onChange={handleSelectChange('race_ethnicity')} label="Race/Ethnicity">
                    {Object.values(RaceEthnicity).map(r => <MenuItem key={r} value={r}>{r}</MenuItem>)}
                </Select>
            </FormControl>
          </Stack>
        );
      case 4:
        return (
          <Stack spacing={2}>
            <Typography variant="h5" fontWeight="bold">Requirements & Certifications</Typography>
            <FormControl fullWidth>
              <InputLabel>Security Clearance Eligibility</InputLabel>
              <Select value={formData.security_clearance} onChange={handleSelectChange('security_clearance')} label="Security Clearance Eligibility">
                <MenuItem value={YesNoNA.YES}>Yes</MenuItem>
                <MenuItem value={YesNoNA.NO}>No</MenuItem>
                <MenuItem value={YesNoNA.NA}>N/A</MenuItem>
              </Select>
            </FormControl>
            <Card variant="outlined" sx={{ p: 2, bgcolor: 'grey.50' }}>
                <Typography variant="subtitle2" gutterBottom>By checking below, you agree to our terms:</Typography>
                <Stack spacing={1}>
                    <FormControlLabel control={<Checkbox checked={formData.cert_accuracy} onChange={handleChange('cert_accuracy')} />} label="I certify the accuracy of all information." />
                    <FormControlLabel control={<Checkbox checked={formData.cert_background_check} onChange={handleChange('cert_background_check')} />} label="I authorize background checks." />
                    <FormControlLabel control={<Checkbox checked={formData.cert_data_processing} onChange={handleChange('cert_data_processing')} />} label="I consent to data processing for applications." />
                </Stack>
            </Card>
          </Stack>
        );
      case 5:
        return (
            <Stack spacing={3}>
                <Typography variant="h5" fontWeight="bold">Final Review</Typography>
                <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="body1"><strong>Name:</strong> {formData.full_name}</Typography>
                    <Typography variant="body1"><strong>Email:</strong> {formData.email_address}</Typography>
                    <Typography variant="body1"><strong>Position:</strong> {formData.employment_type}, {formData.desired_salary}</Typography>
                </Paper>
                <TextField fullWidth label="Electronic Signature" placeholder="Type your full name" value={formData.electronic_signature} onChange={handleChange('electronic_signature')} error={!!errors.electronic_signature} required />
            </Stack>
        );
      default:
        return <Typography>More fields coming soon...</Typography>;
    }
  };

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#f8fafc', py: 8 }}>
      <Container maxWidth="md">
        <Paper elevation={0} sx={{ p: { xs: 3, md: 6 }, borderRadius: 4, border: '1px solid', borderColor: 'divider' }}>
          <Box sx={{ mb: 4, textAlign: 'center' }}>
            <Typography variant="h4" fontWeight="bold" color="primary" gutterBottom>Onboarding</Typography>
            <Typography variant="body1" color="text.secondary">Complete your profile to unlock AI-powered job applications.</Typography>
          </Box>

          <Stepper activeStep={currentStep} alternativeLabel sx={{ mb: 6 }}>
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>

          <Box sx={{ minHeight: 400, mb: 4 }}>
            {renderStepContent(currentStep)}
          </Box>

          <Divider sx={{ my: 4 }} />

          <Stack direction="row" justifyContent="space-between">
            <Button disabled={currentStep === 0 || loading} onClick={handleBack} variant="text" size="large">Back</Button>
            <Box>
              {currentStep === steps.length - 1 ? (
                <Button variant="contained" onClick={handleSubmit} disabled={loading} size="large" sx={{ px: 4, borderRadius: 2 }}>
                  {loading ? <CircularProgress size={24} color="inherit" /> : 'Complete Setup'}
                </Button>
              ) : (
                <Button variant="contained" onClick={handleNext} size="large" sx={{ px: 4, borderRadius: 2 }}>Next</Button>
              )}
            </Box>
          </Stack>
        </Paper>
      </Container>
      <Snackbar open={!!error} autoHideDuration={6000} onClose={() => setError('')}>
        <Alert severity="error" sx={{ width: '100%' }}>{error}</Alert>
      </Snackbar>
    </Box>
  );
}

export default Onboarding;
