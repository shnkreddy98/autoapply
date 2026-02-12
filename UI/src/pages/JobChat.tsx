import { useState, useRef, useEffect, type KeyboardEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { 
  Container, 
  Typography, 
  Box, 
  Paper, 
  TextField, 
  IconButton, 
  Avatar, 
  Divider,
  Button,
  Tooltip,
  CircularProgress
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import axios from 'axios';
import type { Job, ApplicationAnswer, ApplicationAnswers } from '../types';

interface Message {
  id: number;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
  answers?: ApplicationAnswer[];
  isError?: boolean;
}

const JobChat = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const job = location.state?.job as Job;
  const scrollRef = useRef<HTMLDivElement>(null);

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      text: "Hi! I can help you understand this job role better. Ask me anything about the requirements, company, or how your resume matches.",
      sender: 'bot',
      timestamp: new Date()
    }
  ]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  if (!job) {
    return (
      <Container sx={{ mt: 4 }}>
        <Typography variant="h5">No job selected.</Typography>
        <Button onClick={() => navigate('/jobs')} sx={{ mt: 2 }}>
          Back to Jobs
        </Button>
      </Container>
    );
  }

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: messages.length + 1,
      text: input,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    const userQuestion = input; // Capture the input before clearing
    setInput('');
    setLoading(true);

    try {
      const response = await axios.post<ApplicationAnswers>('/api/application-question', {
        url: job.url,
        questions: userQuestion
      });

      const botMessage: Message = {
        id: messages.length + 2,
        text: "I've analyzed the job description and your resume. Here are the suggested answers:",
        sender: 'bot',
        timestamp: new Date(),
        answers: response.data.all_answers
      };
      setMessages(prev => [...prev, botMessage]);
    } catch (err) {
      console.error("Error fetching answers:", err);
      const errorMessage: Message = {
        id: messages.length + 2,
        text: "Sorry, I encountered an error while trying to generate answers. Please try again later.",
        sender: 'bot',
        timestamp: new Date(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, height: '85vh', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
        <IconButton onClick={() => navigate('/jobs')} sx={{ mr: 2 }}>
          <ArrowBackIcon />
        </IconButton>
        <Box>
          <Typography variant="h5">{job.role}</Typography>
          <Typography variant="subtitle1" color="text.secondary">{job.company_name}</Typography>
        </Box>
      </Box>

      <Box sx={{ display: 'flex', gap: 3, flex: 1, overflow: 'hidden' }}>
        {/* Left Panel: Job Explanation */}
        <Paper elevation={3} sx={{ flex: 1, p: 3, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          <Typography variant="h6" gutterBottom color="primary">
            Detailed Explanation
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Typography variant="body1" style={{ whiteSpace: 'pre-line' }}>
            {job.job_match_summary || "No detailed explanation available for this job yet."}
          </Typography>
        </Paper>

        {/* Right Panel: Chat Interface */}
        <Paper elevation={3} sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <Box sx={{ p: 2, bgcolor: 'primary.main', color: 'white', display: 'flex', alignItems: 'center', gap: 1 }}>
            <SmartToyIcon />
            <Typography variant="subtitle1">Job Assistant</Typography>
          </Box>
          
          <Box sx={{ flex: 1, p: 2, overflowY: 'auto', bgcolor: '#f5f5f5', display: 'flex', flexDirection: 'column', gap: 2 }}>
            {messages.map((msg) => (
              <Box 
                key={msg.id} 
                sx={{ 
                  display: 'flex', 
                  justifyContent: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                  gap: 1
                }}
              >
                {msg.sender === 'bot' && <Avatar sx={{ bgcolor: msg.isError ? 'error.main' : 'primary.main', width: 32, height: 32 }}><SmartToyIcon fontSize="small" /></Avatar>}
                <Paper 
                  sx={{ 
                    p: 1.5, 
                    maxWidth: '85%', 
                    bgcolor: msg.sender === 'user' ? 'primary.light' : 'white',
                    color: msg.sender === 'user' ? 'white' : (msg.isError ? 'error.main' : 'text.primary'),
                    borderRadius: 2
                  }}
                >
                  <Typography variant="body2" sx={{ mb: msg.answers ? 2 : 0 }}>{msg.text}</Typography>
                  
                  {msg.answers && (
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      {msg.answers.map((ans, idx) => (
                        <Box key={idx} sx={{ bgcolor: 'rgba(0,0,0,0.03)', p: 1.5, borderRadius: 1, border: '1px solid rgba(0,0,0,0.05)' }}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: 'primary.main', mb: 0.5 }}>
                            Q{idx + 1}: {ans.questions}
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
                            <Typography variant="body2" sx={{ flex: 1, color: 'text.secondary' }}>
                              A{idx + 1}: {ans.answer}
                            </Typography>
                            <Tooltip title="Copy Answer">
                              <IconButton size="small" onClick={() => handleCopy(ans.answer)}>
                                <ContentCopyIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </Box>
                        </Box>
                      ))}
                    </Box>
                  )}
                </Paper>
                {msg.sender === 'user' && <Avatar sx={{ bgcolor: 'secondary.main', width: 32, height: 32 }}><PersonIcon fontSize="small" /></Avatar>}
              </Box>
            ))}
            {loading && (
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Avatar sx={{ bgcolor: 'primary.main', width: 32, height: 32 }}><SmartToyIcon fontSize="small" /></Avatar>
                <Paper sx={{ p: 1.5, borderRadius: 2 }}>
                  <CircularProgress size={20} />
                </Paper>
              </Box>
            )}
            <div ref={scrollRef} />
          </Box>

          <Box sx={{ p: 2, bgcolor: 'white', borderTop: '1px solid #e0e0e0' }}>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <TextField 
                fullWidth 
                placeholder="Ask about application questions..." 
                variant="outlined" 
                size="small"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyPress}
                disabled={loading}
              />
              <IconButton color="primary" onClick={handleSend} disabled={!input.trim() || loading}>
                {loading ? <CircularProgress size={24} /> : <SendIcon />}
              </IconButton>
            </Box>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

export default JobChat;