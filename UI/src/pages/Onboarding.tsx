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
  RadioGroup,
  Radio,
  LinearProgress,
  Snackbar,
  Alert,
  CircularProgress,
  FormLabel,
  Divider
} from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import axios from 'axios';
import type { UserOnboarding } from '../types';
import {
  EmploymentType,
  Gender,
  RaceEthnicity,
  VeteranStatus,
  DisabilityStatus,
  YesNoNA
} from '../types';

const steps = [
  'Personal Information',
  'Work Authorization & Position',
  'EEO Information',
  'Employment History',
  'Job Requirements & Certifications',
  'Review & Signature'
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
    work_eligible_us: false,
    visa_sponsorship: false,
    available_start_date: '',
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
    // Pre-fill data from login if available
    const email = sessionStorage.getItem('userEmail');
    const name = sessionStorage.getItem('userName');
    const phone = sessionStorage.getItem('userPhone');
    const countryCode = sessionStorage.getItem('userCountryCode');
    const location = sessionStorage.getItem('userLocation');

    const updates: Partial<UserOnboarding> = {};

    if (email) {
      updates.email_address = email;
    }

    if (name) {
      updates.full_name = name;
      updates.electronic_signature = name; // Pre-fill signature with name
    }

    if (phone && countryCode) {
      updates.phone_number = `${countryCode} ${phone}`;
    }

    // Parse location (e.g., "San Francisco, CA" -> city: "San Francisco", state: "CA")
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
    const value = e.target.type === 'checkbox'
      ? e.target.checked
      : e.target.value;

    setFormData({ ...formData, [field]: value });
    // Clear error for this field
    if (errors[field]) {
      const newErrors = { ...errors };
      delete newErrors[field];
      setErrors(newErrors);
    }
  };

  const handleSelectChange = (field: keyof UserOnboarding) => (
    e: SelectChangeEvent
  ) => {
    setFormData({ ...formData, [field]: e.target.value });
    // Clear error for this field
    if (errors[field]) {
      const newErrors = { ...errors };
      delete newErrors[field];
      setErrors(newErrors);
    }
  };

  const validateStep = (step: number): boolean => {
    const newErrors: Record<string, string> = {};

    switch (step) {
      case 0: // Personal Information
        if (!formData.full_name.trim()) newErrors.full_name = 'Full name is required';
        if (!formData.street_address.trim()) newErrors.street_address = 'Street address is required';
        if (!formData.city.trim()) newErrors.city = 'City is required';
        if (!formData.state.trim()) newErrors.state = 'State is required';
        if (!formData.zip_code.trim()) newErrors.zip_code = 'ZIP code is required';
        if (!formData.phone_number.trim()) newErrors.phone_number = 'Phone number is required';
        if (!formData.email_address.trim()) {
          newErrors.email_address = 'Email address is required';
        } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email_address)) {
          newErrors.email_address = 'Please enter a valid email address';
        }
        if (!formData.age_18_or_older) newErrors.age_18_or_older = 'You must confirm you are 18 or older';
        break;

      case 1: // Work Authorization & Position
        if (!formData.available_start_date.trim()) newErrors.available_start_date = 'Start date is required';
        if (!formData.desired_salary.trim()) newErrors.desired_salary = 'Desired salary is required';
        break;

      case 2: // EEO Information (all optional)
        // No validation needed - all fields are optional
        break;

      case 3: // Employment History
        if (formData.ever_terminated && !formData.termination_explanation?.trim()) {
          newErrors.termination_explanation = 'Please explain the circumstances';
        }
        break;

      case 4: // Job Requirements & Certifications
        if (!formData.cert_accuracy) newErrors.cert_accuracy = 'Required';
        if (!formData.cert_dismissal) newErrors.cert_dismissal = 'Required';
        if (!formData.cert_background_check) newErrors.cert_background_check = 'Required';
        if (!formData.cert_drug_testing) newErrors.cert_drug_testing = 'Required';
        if (!formData.cert_at_will) newErrors.cert_at_will = 'Required';
        if (!formData.cert_job_description) newErrors.cert_job_description = 'Required';
        if (!formData.cert_privacy_notice) newErrors.cert_privacy_notice = 'Required';
        if (!formData.cert_data_processing) newErrors.cert_data_processing = 'Required';
        break;

      case 5: // Review & Signature
        if (!formData.electronic_signature.trim()) newErrors.electronic_signature = 'Signature is required';
        if (!formData.signature_date.trim()) newErrors.signature_date = 'Date is required';
        break;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => prev + 1);
    }
  };

  const handleBack = () => {
    setCurrentStep(prev => prev - 1);
  };

  const handleSubmit = async () => {
    if (!validateStep(currentStep)) {
      return;
    }

    setLoading(true);
    setError('');

    try {
      await axios.post('/api/user-form', formData);
      // Clear all session data after successful submission
      sessionStorage.removeItem('userEmail');
      sessionStorage.removeItem('userName');
      sessionStorage.removeItem('userPhone');
      sessionStorage.removeItem('userCountryCode');
      sessionStorage.removeItem('userLocation');
      navigate('/tailor');
    } catch (err: any) {
      console.error('Error saving user data:', err);
      setError(err.response?.data?.detail || 'Failed to save user information. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const renderStepContent = (step: number) => {
    switch (step) {
      case 0: // Personal Information
        return (
          <Box>
            <Typography variant="h6" gutterBottom>Personal Information</Typography>
            <TextField
              fullWidth
              label="Full Name"
              value={formData.full_name}
              onChange={handleChange('full_name')}
              error={!!errors.full_name}
              helperText={errors.full_name}
              margin="normal"
              required
            />
            <TextField
              fullWidth
              label="Street Address"
              value={formData.street_address}
              onChange={handleChange('street_address')}
              error={!!errors.street_address}
              helperText={errors.street_address}
              margin="normal"
              required
            />
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                fullWidth
                label="City"
                value={formData.city}
                onChange={handleChange('city')}
                error={!!errors.city}
                helperText={errors.city}
                margin="normal"
                required
              />
              <TextField
                fullWidth
                label="State"
                value={formData.state}
                onChange={handleChange('state')}
                error={!!errors.state}
                helperText={errors.state}
                margin="normal"
                required
              />
              <TextField
                fullWidth
                label="ZIP Code"
                value={formData.zip_code}
                onChange={handleChange('zip_code')}
                error={!!errors.zip_code}
                helperText={errors.zip_code}
                margin="normal"
                required
              />
            </Box>
            <TextField
              fullWidth
              label="Phone Number"
              value={formData.phone_number}
              onChange={handleChange('phone_number')}
              error={!!errors.phone_number}
              helperText={errors.phone_number}
              margin="normal"
              required
            />
            <TextField
              fullWidth
              label="Email Address"
              type="email"
              value={formData.email_address}
              onChange={handleChange('email_address')}
              error={!!errors.email_address}
              helperText={errors.email_address}
              margin="normal"
              required
            />
            <TextField
              fullWidth
              label="Date of Birth"
              type="date"
              value={formData.date_of_birth}
              onChange={handleChange('date_of_birth')}
              margin="normal"
              InputLabelProps={{ shrink: true }}
              helperText="Optional"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.age_18_or_older}
                  onChange={handleChange('age_18_or_older')}
                />
              }
              label="I am 18 years of age or older"
            />
            {errors.age_18_or_older && (
              <Typography color="error" variant="caption" display="block">
                {errors.age_18_or_older}
              </Typography>
            )}
          </Box>
        );

      case 1: // Work Authorization & Position
        return (
          <Box>
            <Typography variant="h6" gutterBottom>Work Authorization & Position Details</Typography>

            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.work_eligible_us}
                  onChange={handleChange('work_eligible_us')}
                />
              }
              label="Are you legally eligible to work in the United States?"
            />

            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.visa_sponsorship}
                  onChange={handleChange('visa_sponsorship')}
                />
              }
              label="Do you now or will you in the future require visa sponsorship?"
            />

            <TextField
              fullWidth
              label="Available Start Date"
              type="date"
              value={formData.available_start_date}
              onChange={handleChange('available_start_date')}
              error={!!errors.available_start_date}
              helperText={errors.available_start_date}
              margin="normal"
              InputLabelProps={{ shrink: true }}
              required
            />

            <FormControl fullWidth margin="normal">
              <InputLabel>Employment Type</InputLabel>
              <Select
                value={formData.employment_type}
                onChange={handleSelectChange('employment_type')}
                label="Employment Type"
              >
                <MenuItem value={EmploymentType.FULL_TIME}>Full-time</MenuItem>
                <MenuItem value={EmploymentType.PART_TIME}>Part-time</MenuItem>
                <MenuItem value={EmploymentType.EITHER}>Either</MenuItem>
              </Select>
            </FormControl>

            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.willing_relocate}
                  onChange={handleChange('willing_relocate')}
                />
              }
              label="Are you willing to relocate?"
            />

            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.willing_travel}
                  onChange={handleChange('willing_travel')}
                />
              }
              label="Are you willing to travel?"
            />

            {formData.willing_travel && (
              <TextField
                fullWidth
                label="Travel Percentage"
                value={formData.travel_percentage}
                onChange={handleChange('travel_percentage')}
                margin="normal"
                helperText="e.g., 25%"
              />
            )}

            <TextField
              fullWidth
              label="Desired Salary/Wage"
              value={formData.desired_salary}
              onChange={handleChange('desired_salary')}
              error={!!errors.desired_salary}
              helperText={errors.desired_salary}
              margin="normal"
              required
            />
          </Box>
        );

      case 2: // EEO Information
        return (
          <Box>
            <Typography variant="h6" gutterBottom>EEO Information</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Voluntary - You may skip this section. This information is used for equal employment opportunity reporting.
            </Typography>

            <FormControl fullWidth margin="normal">
              <InputLabel>Gender</InputLabel>
              <Select
                value={formData.gender || ''}
                onChange={handleSelectChange('gender')}
                label="Gender"
              >
                <MenuItem value="">Prefer not to answer</MenuItem>
                <MenuItem value={Gender.MALE}>Male</MenuItem>
                <MenuItem value={Gender.FEMALE}>Female</MenuItem>
                <MenuItem value={Gender.NON_BINARY}>Non-binary</MenuItem>
                <MenuItem value={Gender.PREFER_NOT_TO_ANSWER}>Prefer not to answer</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth margin="normal">
              <InputLabel>Race/Ethnicity</InputLabel>
              <Select
                value={formData.race_ethnicity || ''}
                onChange={handleSelectChange('race_ethnicity')}
                label="Race/Ethnicity"
              >
                <MenuItem value="">Prefer not to answer</MenuItem>
                <MenuItem value={RaceEthnicity.HISPANIC_LATINO}>Hispanic or Latino</MenuItem>
                <MenuItem value={RaceEthnicity.WHITE}>White</MenuItem>
                <MenuItem value={RaceEthnicity.BLACK_AFRICAN_AMERICAN}>Black or African American</MenuItem>
                <MenuItem value={RaceEthnicity.ASIAN}>Asian</MenuItem>
                <MenuItem value={RaceEthnicity.AMERICAN_INDIAN_ALASKA_NATIVE}>American Indian or Alaska Native</MenuItem>
                <MenuItem value={RaceEthnicity.NATIVE_HAWAIIAN_PACIFIC_ISLANDER}>Native Hawaiian or Other Pacific Islander</MenuItem>
                <MenuItem value={RaceEthnicity.TWO_OR_MORE_RACES}>Two or More Races</MenuItem>
                <MenuItem value={RaceEthnicity.PREFER_NOT_TO_ANSWER}>Prefer not to answer</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth margin="normal">
              <InputLabel>Veteran Status</InputLabel>
              <Select
                value={formData.veteran_status || ''}
                onChange={handleSelectChange('veteran_status')}
                label="Veteran Status"
              >
                <MenuItem value="">Prefer not to answer</MenuItem>
                <MenuItem value={VeteranStatus.DISABLED_VETERAN}>Disabled veteran</MenuItem>
                <MenuItem value={VeteranStatus.RECENTLY_SEPARATED_VETERAN}>Recently separated veteran</MenuItem>
                <MenuItem value={VeteranStatus.ACTIVE_WARTIME_VETERAN}>Active wartime veteran</MenuItem>
                <MenuItem value={VeteranStatus.ARMED_FORCES_SERVICE_MEDAL_VETERAN}>Armed Forces service medal veteran</MenuItem>
                <MenuItem value={VeteranStatus.OTHER_PROTECTED_VETERAN}>Other protected veteran</MenuItem>
                <MenuItem value={VeteranStatus.NOT_A_VETERAN}>Not a veteran</MenuItem>
                <MenuItem value={VeteranStatus.PREFER_NOT_TO_ANSWER}>Prefer not to answer</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth margin="normal">
              <InputLabel>Disability Status</InputLabel>
              <Select
                value={formData.disability_status || ''}
                onChange={handleSelectChange('disability_status')}
                label="Disability Status"
              >
                <MenuItem value="">Prefer not to answer</MenuItem>
                <MenuItem value={DisabilityStatus.YES}>Yes, I have a disability</MenuItem>
                <MenuItem value={DisabilityStatus.NO}>No, I do not have a disability</MenuItem>
                <MenuItem value={DisabilityStatus.PREFER_NOT_TO_ANSWER}>Prefer not to answer</MenuItem>
              </Select>
            </FormControl>
          </Box>
        );

      case 3: // Employment History
        return (
          <Box>
            <Typography variant="h6" gutterBottom>Employment History</Typography>

            <FormControl component="fieldset" margin="normal" fullWidth>
              <FormLabel component="legend">Are you a current employee of this company?</FormLabel>
              <RadioGroup
                value={formData.current_employee.toString()}
                onChange={(e) => setFormData({ ...formData, current_employee: e.target.value === 'true' })}
              >
                <FormControlLabel value="true" control={<Radio />} label="Yes" />
                <FormControlLabel value="false" control={<Radio />} label="No" />
              </RadioGroup>
            </FormControl>

            <FormControl component="fieldset" margin="normal" fullWidth>
              <FormLabel component="legend">Have you ever been terminated or asked to resign from any position?</FormLabel>
              <RadioGroup
                value={formData.ever_terminated.toString()}
                onChange={(e) => setFormData({ ...formData, ever_terminated: e.target.value === 'true' })}
              >
                <FormControlLabel value="true" control={<Radio />} label="Yes" />
                <FormControlLabel value="false" control={<Radio />} label="No" />
              </RadioGroup>
            </FormControl>

            {formData.ever_terminated && (
              <TextField
                fullWidth
                label="Please explain the circumstances"
                value={formData.termination_explanation}
                onChange={handleChange('termination_explanation')}
                error={!!errors.termination_explanation}
                helperText={errors.termination_explanation}
                margin="normal"
                multiline
                rows={3}
                required
              />
            )}
          </Box>
        );

      case 4: // Job Requirements & Certifications
        return (
          <Box>
            <Typography variant="h6" gutterBottom>Job Requirements & Certifications</Typography>

            <FormControl fullWidth margin="normal">
              <InputLabel>Are you eligible for security clearance?</InputLabel>
              <Select
                value={formData.security_clearance}
                onChange={handleSelectChange('security_clearance')}
                label="Are you eligible for security clearance?"
              >
                <MenuItem value={YesNoNA.YES}>Yes</MenuItem>
                <MenuItem value={YesNoNA.NO}>No</MenuItem>
                <MenuItem value={YesNoNA.NA}>N/A</MenuItem>
              </Select>
            </FormControl>

            <Divider sx={{ my: 3 }} />
            <Typography variant="subtitle1" gutterBottom>Certifications and Declarations</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Please read and agree to the following statements:
            </Typography>

            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.cert_accuracy}
                  onChange={handleChange('cert_accuracy')}
                />
              }
              label="I certify that all information provided is true and accurate"
            />
            {errors.cert_accuracy && <Typography color="error" variant="caption" display="block">{errors.cert_accuracy}</Typography>}

            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.cert_dismissal}
                  onChange={handleChange('cert_dismissal')}
                />
              }
              label="I understand that false statements may result in dismissal"
            />
            {errors.cert_dismissal && <Typography color="error" variant="caption" display="block">{errors.cert_dismissal}</Typography>}

            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.cert_background_check}
                  onChange={handleChange('cert_background_check')}
                />
              }
              label="I authorize background and reference checks"
            />
            {errors.cert_background_check && <Typography color="error" variant="caption" display="block">{errors.cert_background_check}</Typography>}

            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.cert_drug_testing}
                  onChange={handleChange('cert_drug_testing')}
                />
              }
              label="I authorize drug testing (if applicable)"
            />
            {errors.cert_drug_testing && <Typography color="error" variant="caption" display="block">{errors.cert_drug_testing}</Typography>}

            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.cert_at_will}
                  onChange={handleChange('cert_at_will')}
                />
              }
              label="I understand this is at-will employment"
            />
            {errors.cert_at_will && <Typography color="error" variant="caption" display="block">{errors.cert_at_will}</Typography>}

            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.cert_job_description}
                  onChange={handleChange('cert_job_description')}
                />
              }
              label="I have read and understand the job description"
            />
            {errors.cert_job_description && <Typography color="error" variant="caption" display="block">{errors.cert_job_description}</Typography>}

            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.cert_privacy_notice}
                  onChange={handleChange('cert_privacy_notice')}
                />
              }
              label="I acknowledge receipt of privacy notice"
            />
            {errors.cert_privacy_notice && <Typography color="error" variant="caption" display="block">{errors.cert_privacy_notice}</Typography>}

            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.cert_data_processing}
                  onChange={handleChange('cert_data_processing')}
                />
              }
              label="I consent to processing of personal data"
            />
            {errors.cert_data_processing && <Typography color="error" variant="caption" display="block">{errors.cert_data_processing}</Typography>}
          </Box>
        );

      case 5: // Review & Signature
        return (
          <Box>
            <Typography variant="h6" gutterBottom>Review & Signature</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Please review your information and provide your electronic signature to complete the onboarding process.
            </Typography>

            <Paper elevation={1} sx={{ p: 2, mb: 3, bgcolor: 'grey.50' }}>
              <Typography variant="subtitle2" gutterBottom>Summary</Typography>
              <Typography variant="body2"><strong>Name:</strong> {formData.full_name}</Typography>
              <Typography variant="body2"><strong>Email:</strong> {formData.email_address}</Typography>
              <Typography variant="body2"><strong>Phone:</strong> {formData.phone_number}</Typography>
              <Typography variant="body2"><strong>Address:</strong> {formData.street_address}, {formData.city}, {formData.state} {formData.zip_code}</Typography>
              <Typography variant="body2"><strong>Start Date:</strong> {formData.available_start_date}</Typography>
              <Typography variant="body2"><strong>Employment Type:</strong> {formData.employment_type}</Typography>
            </Paper>

            <TextField
              fullWidth
              label="Electronic Signature"
              value={formData.electronic_signature}
              onChange={handleChange('electronic_signature')}
              error={!!errors.electronic_signature}
              helperText={errors.electronic_signature || "Type your full name as your signature"}
              margin="normal"
              required
            />

            <TextField
              fullWidth
              label="Signature Date"
              type="date"
              value={formData.signature_date}
              onChange={handleChange('signature_date')}
              error={!!errors.signature_date}
              helperText={errors.signature_date}
              margin="normal"
              InputLabelProps={{ shrink: true }}
              required
            />
          </Box>
        );

      default:
        return null;
    }
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ mt: 4, mb: 4 }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom align="center">
            User Onboarding
          </Typography>

          <Stepper activeStep={currentStep} sx={{ my: 4 }}>
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>

          <LinearProgress
            variant="determinate"
            value={((currentStep + 1) / steps.length) * 100}
            sx={{ mb: 3 }}
          />

          <Box sx={{ minHeight: '400px' }}>
            {renderStepContent(currentStep)}
          </Box>

          <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 4 }}>
            <Button
              disabled={currentStep === 0 || loading}
              onClick={handleBack}
            >
              Previous
            </Button>

            <Box>
              {currentStep === steps.length - 1 ? (
                <Button
                  variant="contained"
                  onClick={handleSubmit}
                  disabled={loading}
                  size="large"
                >
                  {loading ? <CircularProgress size={24} /> : 'Submit Application'}
                </Button>
              ) : (
                <Button
                  variant="contained"
                  onClick={handleNext}
                >
                  Next
                </Button>
              )}
            </Box>
          </Box>
        </Paper>
      </Box>

      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={() => setError('')}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setError('')} severity="error" sx={{ width: '100%' }}>
          {error}
        </Alert>
      </Snackbar>
    </Container>
  );
}

export default Onboarding;
