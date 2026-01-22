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
  Button
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import type { Job } from '../types';

interface Message {
  id: number;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

const JobChat = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const job = location.state?.job as Job;
  const scrollRef = useRef<HTMLDivElement>(null);

  const [input, setInput] = useState('');
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

  const handleSend = () => {
    if (!input.trim()) return;

    const newMessage: Message = {
      id: messages.length + 1,
      text: input,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, newMessage]);
    setInput('');

    // Simulate bot typing/response
    setTimeout(() => {
      const botResponse: Message = {
        id: messages.length + 2,
        text: "I'm looking into that for you... (Backend integration coming soon)",
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, botResponse]);
    }, 1000);
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
            {job.detailed_explaination || "No detailed explanation available for this job yet."}
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
                {msg.sender === 'bot' && <Avatar sx={{ bgcolor: 'primary.main', width: 32, height: 32 }}><SmartToyIcon fontSize="small" /></Avatar>}
                <Paper 
                  sx={{ 
                    p: 1.5, 
                    maxWidth: '80%', 
                    bgcolor: msg.sender === 'user' ? 'primary.light' : 'white',
                    color: msg.sender === 'user' ? 'white' : 'text.primary',
                    borderRadius: 2
                  }}
                >
                  <Typography variant="body2">{msg.text}</Typography>
                </Paper>
                {msg.sender === 'user' && <Avatar sx={{ bgcolor: 'secondary.main', width: 32, height: 32 }}><PersonIcon fontSize="small" /></Avatar>}
              </Box>
            ))}
            <div ref={scrollRef} />
          </Box>

          <Box sx={{ p: 2, bgcolor: 'white', borderTop: '1px solid #e0e0e0' }}>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <TextField 
                fullWidth 
                placeholder="Ask a question..." 
                variant="outlined" 
                size="small"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyPress}
              />
              <IconButton color="primary" onClick={handleSend} disabled={!input.trim()}>
                <SendIcon />
              </IconButton>
            </Box>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

export default JobChat;