import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import {
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  Chip,
  Box,
  Button,
  Stack,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Paper,
  Divider,
} from '@mui/material';
import { Close as CloseIcon, Visibility as VisibilityIcon } from '@mui/icons-material';

interface JobSession {
  session_id: string;
  url: string;
  status: 'queued' | 'running' | 'paused' | 'completed' | 'failed';
  current_step: string;
  screenshot_url: string;
  tab_index: number;
  timeline: TimelineEvent[];
}

interface TimelineEvent {
  type: 'thought' | 'tool_call' | 'screenshot' | 'error' | 'pause' | 'resume' | 'status_update';
  timestamp: string;
  content: string;
  screenshot_url?: string;
}

const JobMonitor = () => {
  const location = useLocation();
  const initialSessions = location.state?.sessions || [];
  const [sessions, setSessions] = useState<Map<string, JobSession>>(new Map());
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [eventSources, setEventSources] = useState<Map<string, EventSource>>(new Map());

  // Initialize sessions from location state
  useEffect(() => {
    const sessionMap = new Map<string, JobSession>();
    initialSessions.forEach((s: any) => {
      sessionMap.set(s.session_id, {
        ...s,
        current_step: 'Queued',
        screenshot_url: '',
        tab_index: -1,
        timeline: [],
      });
    });
    setSessions(sessionMap);
  }, []);

  // Set up SSE connections for each session
  useEffect(() => {
    const newEventSources = new Map<string, EventSource>();

    sessions.forEach((session, session_id) => {
      if (!eventSources.has(session_id) && session.status !== 'completed' && session.status !== 'failed') {
        const eventSource = new EventSource(`/api/stream/${session_id}`);

        eventSource.addEventListener('status_update', (e) => {
          const data = JSON.parse(e.data);
          setSessions((prev) => {
            const updated = new Map(prev);
            const session = updated.get(session_id);
            if (session) {
              updated.set(session_id, {
                ...session,
                status: data.status,
                timeline: [
                  ...session.timeline,
                  {
                    type: 'status_update',
                    timestamp: new Date().toISOString(),
                    content: data.message || `Status: ${data.status}`,
                  },
                ],
              });
            }
            return updated;
          });
        });

        eventSource.addEventListener('tool_call', (e) => {
          const data = JSON.parse(e.data);
          setSessions((prev) => {
            const updated = new Map(prev);
            const session = updated.get(session_id);
            if (session) {
              updated.set(session_id, {
                ...session,
                current_step: data.description,
                timeline: [
                  ...session.timeline,
                  {
                    type: 'tool_call',
                    timestamp: new Date().toISOString(),
                    content: data.description,
                  },
                ],
              });
            }
            return updated;
          });
        });

        eventSource.addEventListener('screenshot', (e) => {
          const data = JSON.parse(e.data);
          setSessions((prev) => {
            const updated = new Map(prev);
            const session = updated.get(session_id);
            if (session) {
              updated.set(session_id, {
                ...session,
                screenshot_url: data.url,
                timeline: [
                  ...session.timeline,
                  {
                    type: 'screenshot',
                    timestamp: new Date().toISOString(),
                    content: `Screenshot captured (step ${data.step_number})`,
                    screenshot_url: data.url,
                  },
                ],
              });
            }
            return updated;
          });
        });

        eventSource.addEventListener('error', (e) => {
          const data = JSON.parse(e.data);
          setSessions((prev) => {
            const updated = new Map(prev);
            const session = updated.get(session_id);
            if (session) {
              updated.set(session_id, {
                ...session,
                status: 'paused',
                timeline: [
                  ...session.timeline,
                  {
                    type: 'error',
                    timestamp: new Date().toISOString(),
                    content: data.error,
                  },
                ],
              });
            }
            return updated;
          });
        });

        eventSource.addEventListener('pause', (e) => {
          const data = JSON.parse(e.data);
          setSessions((prev) => {
            const updated = new Map(prev);
            const session = updated.get(session_id);
            if (session) {
              updated.set(session_id, {
                ...session,
                status: 'paused',
                timeline: [
                  ...session.timeline,
                  {
                    type: 'pause',
                    timestamp: new Date().toISOString(),
                    content: `Paused: ${data.reason}`,
                  },
                ],
              });
            }
            return updated;
          });
        });

        eventSource.addEventListener('resume', (e) => {
          const data = JSON.parse(e.data);
          setSessions((prev) => {
            const updated = new Map(prev);
            const session = updated.get(session_id);
            if (session) {
              updated.set(session_id, {
                ...session,
                status: 'running',
                timeline: [
                  ...session.timeline,
                  {
                    type: 'resume',
                    timestamp: new Date().toISOString(),
                    content: data.message || 'Agent resumed',
                  },
                ],
              });
            }
            return updated;
          });
        });

        eventSource.onerror = () => {
          console.error(`SSE connection error for session ${session_id}`);
          eventSource.close();
          newEventSources.delete(session_id);
        };

        newEventSources.set(session_id, eventSource);
      }
    });

    setEventSources(newEventSources);

    // Cleanup on unmount
    return () => {
      newEventSources.forEach((es) => es.close());
    };
  }, [sessions.size]);

  const handleViewVNC = async (session_id: string) => {
    try {
      const response = await fetch(`/api/sessions/${session_id}/vnc-focus`, {
        method: 'GET',
      });
      const data = await response.json();
      window.open(data.vnc_url, 'vnc', 'width=1280,height=720');
    } catch (error) {
      console.error('Error focusing VNC:', error);
    }
  };

  const handlePause = async (session_id: string) => {
    try {
      await fetch(`/api/sessions/${session_id}/pause`, { method: 'POST' });
    } catch (error) {
      console.error('Error pausing:', error);
    }
  };

  const handleResume = async (session_id: string) => {
    try {
      await fetch(`/api/sessions/${session_id}/resume`, { method: 'POST' });
    } catch (error) {
      console.error('Error resuming:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'queued':
        return 'default';
      case 'running':
        return 'primary';
      case 'paused':
        return 'warning';
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        Job Applications Monitor
      </Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mb: 3 }}>
        Real-time monitoring of job applications. Click on a card to see full timeline and screenshots.
      </Typography>

      <Grid container spacing={3}>
        {Array.from(sessions.values()).map((session) => (
          <Grid item xs={12} md={6} lg={4} key={session.session_id}>
            <Card
              onClick={() => setSelectedSession(session.session_id)}
              sx={{
                cursor: 'pointer',
                '&:hover': { boxShadow: 6 },
                height: '100%',
                transition: 'box-shadow 0.2s',
              }}
            >
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                  <Typography variant="h6" noWrap title={session.url} sx={{ flex: 1, mr: 1 }}>
                    {new URL(session.url).hostname.replace('www.', '')}
                  </Typography>
                  <Chip label={session.status} color={getStatusColor(session.status)} size="small" />
                </Box>

                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mb: 2, minHeight: '2.5em' }}
                >
                  {session.current_step}
                </Typography>

                {session.screenshot_url && (
                  <Box sx={{ mb: 2, position: 'relative' }}>
                    <img
                      src={session.screenshot_url}
                      alt="Latest screenshot"
                      style={{
                        width: '100%',
                        borderRadius: 4,
                        border: '1px solid #ddd',
                        objectFit: 'cover',
                        maxHeight: '200px',
                      }}
                    />
                    <Box
                      sx={{
                        position: 'absolute',
                        top: 8,
                        right: 8,
                        bgcolor: 'rgba(0, 0, 0, 0.6)',
                        borderRadius: 1,
                        px: 1,
                        py: 0.5,
                      }}
                    >
                      <Typography variant="caption" color="white">
                        {session.timeline.length} steps
                      </Typography>
                    </Box>
                  </Box>
                )}

                <Stack direction="row" spacing={1} flexWrap="wrap" gap={1}>
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<VisibilityIcon />}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleViewVNC(session.session_id);
                    }}
                  >
                    View VNC
                  </Button>
                  {session.status === 'running' && (
                    <Button
                      variant="outlined"
                      size="small"
                      color="warning"
                      onClick={(e) => {
                        e.stopPropagation();
                        handlePause(session.session_id);
                      }}
                    >
                      Pause
                    </Button>
                  )}
                  {session.status === 'paused' && (
                    <Button
                      variant="contained"
                      size="small"
                      color="success"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleResume(session.session_id);
                      }}
                    >
                      Resume
                    </Button>
                  )}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Screenshot & Timeline Modal */}
      <Dialog open={!!selectedSession} onClose={() => setSelectedSession(null)} maxWidth="lg" fullWidth>
        <DialogTitle>
          Application Timeline
          <IconButton onClick={() => setSelectedSession(null)} sx={{ position: 'absolute', right: 8, top: 8 }}>
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          {selectedSession && sessions.get(selectedSession) && (
            <Grid container spacing={3}>
              <Grid item xs={12} md={8}>
                <Paper elevation={2} sx={{ p: 2, bgcolor: '#f5f5f5' }}>
                  <Typography variant="h6" gutterBottom>
                    Current Screenshot
                  </Typography>
                  {sessions.get(selectedSession)?.screenshot_url ? (
                    <img
                      src={sessions.get(selectedSession)?.screenshot_url}
                      alt="Application screenshot"
                      style={{ width: '100%', borderRadius: 4, border: '1px solid #ccc' }}
                    />
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      No screenshot available yet
                    </Typography>
                  )}
                </Paper>
              </Grid>
              <Grid item xs={12} md={4}>
                <Typography variant="h6" gutterBottom>
                  Timeline
                </Typography>
                <Paper elevation={1} sx={{ maxHeight: 500, overflowY: 'auto', p: 2 }}>
                  {sessions.get(selectedSession)?.timeline.map((event, idx) => (
                    <Box key={idx} sx={{ mb: 2, pb: 2, borderBottom: idx < sessions.get(selectedSession)!.timeline.length - 1 ? '1px solid #eee' : 'none' }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Chip label={event.type} size="small" variant="outlined" />
                        <Typography variant="caption" color="text.secondary">
                          {new Date(event.timestamp).toLocaleTimeString()}
                        </Typography>
                      </Box>
                      <Typography variant="body2">{event.content}</Typography>
                    </Box>
                  ))}
                  {sessions.get(selectedSession)?.timeline.length === 0 && (
                    <Typography variant="body2" color="text.secondary">
                      No events yet
                    </Typography>
                  )}
                </Paper>
              </Grid>
            </Grid>
          )}
        </DialogContent>
      </Dialog>
    </Container>
  );
};

export default JobMonitor;
