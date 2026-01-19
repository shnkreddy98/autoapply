import { Container, Card, CardContent, Typography, CardActionArea, Box, LinearProgress } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import type { Job } from '../types';

// Mock Data
const MOCK_JOBS: Job[] = [
  { id: '1', companyName: 'Google', jobRole: 'Frontend Engineer', resumeMatch: 85, resumeName: 'My_Resume_v1.pdf' },
  { id: '2', companyName: 'Amazon', jobRole: 'Backend Developer', resumeMatch: 92, resumeName: 'My_Resume_Backend.pdf' },
  { id: '3', companyName: 'Netflix', jobRole: 'Full Stack Engineer', resumeMatch: 78, resumeName: 'My_Resume_General.pdf' },
];

const JobList = () => {
  const navigate = useNavigate();

  const handleCardClick = (id: string) => {
    navigate(`/jobs/${id}`);
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>
        Application Status
      </Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        {MOCK_JOBS.map((job) => (
          <Box key={job.id} sx={{ width: '100%' }}>
            <Card>
              <CardActionArea onClick={() => handleCardClick(job.id)}>
                <CardContent>
                  <Typography variant="h6" component="div">
                    {job.companyName}
                  </Typography>
                  <Typography color="text.secondary" gutterBottom>
                    {job.jobRole}
                  </Typography>
                  
                  <Box sx={{ mt: 2, mb: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      Resume Match: {job.resumeMatch}%
                    </Typography>
                    <LinearProgress 
                      variant="determinate" 
                      value={job.resumeMatch} 
                      color={job.resumeMatch > 80 ? "success" : "primary"}
                    />
                  </Box>
                  
                  <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                    Resume: {job.resumeName}
                  </Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          </Box>
        ))}
      </Box>
    </Container>
  );
};

export default JobList;