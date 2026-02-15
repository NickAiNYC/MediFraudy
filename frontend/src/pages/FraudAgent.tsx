import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  TextField,
  IconButton,
  Paper,
  Avatar,
  Chip,
  CircularProgress,
  Tooltip,
  Divider,
  InputAdornment,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  Send as SendIcon,
  SmartToy as BotIcon,
  Person as PersonIcon,
  DeleteSweep as ClearIcon,
  ContentCopy as CopyIcon,
  Gavel as GavelIcon,
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  provider_id?: number;
}

const SUGGESTED_PROMPTS = [
  "What are the top Medicaid fraud schemes in NYC right now?",
  "How do I structure a qui tam complaint for capacity violations?",
  "What's the estimated whistleblower reward for a $50M fraud case?",
  "Explain the key elements needed to prove a False Claims Act violation.",
  "What red flags should I look for in home care billing data?",
  "How do cross-borough referral rings work in Medicaid fraud?",
];

const FraudAgent: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: `**NYC Medicaid Fraud Legal Assistant** — powered by DeepSeek

I'm your specialized AI legal assistant for NYC Medicaid fraud investigation. I can help with:

• **False Claims Act analysis** — federal & NY state theories
• **Billing pattern interpretation** — z-scores, peer deviations, spikes
• **Qui tam strategy** — whistleblower procedures, relator protections, reward calculations
• **Evidence review** — analyzing risk scores, network graphs, anomaly data
• **NYC-specific fraud patterns** — home care, NEMT, DME, SADC, CDPAP
• **Litigation drafting** — complaint language, disclosure statements

You can optionally select a Provider ID to give me context about a specific provider's risk profile.

How can I assist your investigation today?`,
      timestamp: new Date().toISOString(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [providerId, setProviderId] = useState<string>('');
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const [agentStatus, setAgentStatus] = useState<{ configured: boolean; model: string } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Check agent status on mount
  useEffect(() => {
    axios.get(`${API_BASE}/api/v1/agent/status`)
      .then(res => setAgentStatus(res.data))
      .catch(() => setAgentStatus({ configured: false, model: 'unknown' }));
  }, []);

  const sendMessage = async (text?: string) => {
    const messageText = text || input.trim();
    if (!messageText || loading) return;

    const userMessage: Message = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: messageText,
      timestamp: new Date().toISOString(),
      provider_id: providerId ? parseInt(providerId) : undefined,
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await axios.post(`${API_BASE}/api/v1/agent/chat`, {
        message: messageText,
        session_id: sessionId,
        provider_id: providerId ? parseInt(providerId) : null,
      });

      const assistantMessage: Message = {
        id: `assistant_${Date.now()}`,
        role: 'assistant',
        content: response.data.response,
        timestamp: response.data.timestamp || new Date().toISOString(),
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error: any) {
      const errorMessage: Message = {
        id: `error_${Date.now()}`,
        role: 'assistant',
        content: `⚠️ ${error.response?.data?.detail || error.message || 'Failed to reach the agent. Check your connection and API key.'}`,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = async () => {
    try {
      await axios.post(`${API_BASE}/api/v1/agent/clear-session?session_id=${sessionId}`);
    } catch { /* ignore */ }
    setMessages([messages[0]]); // Keep welcome message
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 100px)' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Avatar sx={{ bgcolor: 'rgba(99, 102, 241, 0.15)', border: '1px solid rgba(99, 102, 241, 0.4)' }}>
            <GavelIcon sx={{ color: '#818cf8' }} />
          </Avatar>
          <Box>
            <Typography variant="h5" sx={{ color: '#f1f5f9', fontWeight: 700 }}>
              Fraud Legal Assistant
            </Typography>
            <Typography variant="caption" sx={{ color: '#64748b' }}>
              DeepSeek AI · NYC Medicaid Fraud Specialist
            </Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Chip
            label={agentStatus?.configured ? '● Connected' : '○ Not Configured'}
            size="small"
            sx={{
              bgcolor: agentStatus?.configured ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
              color: agentStatus?.configured ? '#10b981' : '#ef4444',
              fontWeight: 600,
              fontSize: '0.65rem',
            }}
          />
          <Tooltip title="Clear conversation">
            <IconButton onClick={clearChat} sx={{ color: '#64748b', '&:hover': { color: '#ef4444' } }}>
              <ClearIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Messages Area */}
      <Paper
        sx={{
          flex: 1,
          overflow: 'auto',
          bgcolor: '#0a0f1e',
          border: '1px solid #1e293b',
          borderRadius: 2,
          p: 2,
          mb: 2,
          '&::-webkit-scrollbar': { width: 6 },
          '&::-webkit-scrollbar-thumb': { bgcolor: '#334155', borderRadius: 3 },
        }}
      >
        {messages.map((msg) => (
          <Box
            key={msg.id}
            sx={{
              display: 'flex',
              gap: 1.5,
              mb: 2,
              flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
            }}
          >
            <Avatar
              sx={{
                width: 32,
                height: 32,
                bgcolor: msg.role === 'user'
                  ? 'rgba(16, 185, 129, 0.15)'
                  : 'rgba(99, 102, 241, 0.15)',
                border: `1px solid ${msg.role === 'user' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(99, 102, 241, 0.3)'}`,
                mt: 0.5,
              }}
            >
              {msg.role === 'user'
                ? <PersonIcon sx={{ fontSize: 16, color: '#10b981' }} />
                : <BotIcon sx={{ fontSize: 16, color: '#818cf8' }} />
              }
            </Avatar>
            <Box
              sx={{
                maxWidth: '75%',
                bgcolor: msg.role === 'user' ? 'rgba(16, 185, 129, 0.08)' : 'rgba(30, 41, 59, 0.6)',
                border: `1px solid ${msg.role === 'user' ? 'rgba(16, 185, 129, 0.2)' : '#1e293b'}`,
                borderRadius: 2,
                p: 2,
                position: 'relative',
              }}
            >
              {msg.provider_id && (
                <Chip
                  label={`Provider #${msg.provider_id}`}
                  size="small"
                  sx={{
                    mb: 1,
                    bgcolor: 'rgba(59, 130, 246, 0.1)',
                    color: '#60a5fa',
                    fontSize: '0.6rem',
                    height: 20,
                  }}
                />
              )}
              <Typography
                variant="body2"
                sx={{
                  color: '#e2e8f0',
                  whiteSpace: 'pre-wrap',
                  lineHeight: 1.7,
                  fontSize: '0.85rem',
                  '& strong': { color: '#f1f5f9' },
                }}
              >
                {msg.content}
              </Typography>
              {msg.role === 'assistant' && msg.id !== 'welcome' && (
                <Tooltip title="Copy response">
                  <IconButton
                    size="small"
                    onClick={() => copyToClipboard(msg.content)}
                    sx={{
                      position: 'absolute',
                      top: 4,
                      right: 4,
                      color: '#475569',
                      '&:hover': { color: '#94a3b8' },
                    }}
                  >
                    <CopyIcon sx={{ fontSize: 14 }} />
                  </IconButton>
                </Tooltip>
              )}
            </Box>
          </Box>
        ))}
        {loading && (
          <Box sx={{ display: 'flex', gap: 1.5, mb: 2 }}>
            <Avatar sx={{ width: 32, height: 32, bgcolor: 'rgba(99, 102, 241, 0.15)', border: '1px solid rgba(99, 102, 241, 0.3)', mt: 0.5 }}>
              <BotIcon sx={{ fontSize: 16, color: '#818cf8' }} />
            </Avatar>
            <Box sx={{ bgcolor: 'rgba(30, 41, 59, 0.6)', border: '1px solid #1e293b', borderRadius: 2, p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
              <CircularProgress size={16} sx={{ color: '#818cf8' }} />
              <Typography variant="body2" sx={{ color: '#64748b', fontStyle: 'italic' }}>
                Analyzing...
              </Typography>
            </Box>
          </Box>
        )}
        <div ref={messagesEndRef} />
      </Paper>

      {/* Suggested Prompts (show when chat is fresh) */}
      {messages.length <= 1 && (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
          {SUGGESTED_PROMPTS.map((prompt, i) => (
            <Chip
              key={i}
              label={prompt}
              size="small"
              onClick={() => sendMessage(prompt)}
              sx={{
                bgcolor: 'rgba(99, 102, 241, 0.08)',
                color: '#94a3b8',
                border: '1px solid rgba(99, 102, 241, 0.2)',
                fontSize: '0.7rem',
                cursor: 'pointer',
                '&:hover': {
                  bgcolor: 'rgba(99, 102, 241, 0.15)',
                  color: '#c7d2fe',
                  borderColor: 'rgba(99, 102, 241, 0.4)',
                },
              }}
            />
          ))}
        </Box>
      )}

      {/* Input Area */}
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
        <TextField
          size="small"
          placeholder="Provider ID (optional)"
          value={providerId}
          onChange={(e) => setProviderId(e.target.value.replace(/\D/g, ''))}
          sx={{
            width: 140,
            '& .MuiOutlinedInput-root': {
              bgcolor: '#0f172a',
              color: '#f1f5f9',
              '& fieldset': { borderColor: '#1e293b' },
              '&:hover fieldset': { borderColor: '#334155' },
              '&.Mui-focused fieldset': { borderColor: '#6366f1' },
            },
            '& .MuiInputBase-input::placeholder': { color: '#475569' },
          }}
        />
        <TextField
          fullWidth
          multiline
          maxRows={4}
          placeholder="Ask about NYC Medicaid fraud law, billing analysis, qui tam strategy..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          sx={{
            '& .MuiOutlinedInput-root': {
              bgcolor: '#0f172a',
              color: '#f1f5f9',
              '& fieldset': { borderColor: '#1e293b' },
              '&:hover fieldset': { borderColor: '#334155' },
              '&.Mui-focused fieldset': { borderColor: '#6366f1' },
            },
            '& .MuiInputBase-input::placeholder': { color: '#475569' },
          }}
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <IconButton
                  onClick={() => sendMessage()}
                  disabled={!input.trim() || loading}
                  sx={{
                    color: input.trim() ? '#818cf8' : '#334155',
                    '&:hover': { color: '#a5b4fc' },
                  }}
                >
                  <SendIcon />
                </IconButton>
              </InputAdornment>
            ),
          }}
        />
      </Box>
    </Box>
  );
};

export default FraudAgent;
