import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  AlertTitle,
  Stack,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  BugReport as BugReportIcon,
} from '@mui/icons-material';

interface ErrorFallbackProps {
  error: Error;
  resetErrorBoundary: () => void;
}

const ErrorFallback: React.FC<ErrorFallbackProps> = ({
  error,
  resetErrorBoundary,
}) => {
  const handleReload = () => {
    window.location.reload();
  };

  const handleReset = () => {
    resetErrorBoundary();
  };

  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      minHeight="100vh"
      p={3}
      bgcolor="background.default"
    >
      <Paper
        elevation={3}
        sx={{
          p: 4,
          maxWidth: 600,
          width: '100%',
          textAlign: 'center',
        }}
      >
        <BugReportIcon
          color="error"
          sx={{ fontSize: 64, mb: 2 }}
        />
        
        <Typography variant="h4" gutterBottom color="error">
          Oops! Something went wrong
        </Typography>
        
        <Typography variant="body1" color="text.secondary" paragraph>
          We're sorry, but something unexpected happened. The application has encountered an error.
        </Typography>

        <Alert severity="error" sx={{ mb: 3, textAlign: 'left' }}>
          <AlertTitle>Error Details</AlertTitle>
          <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
            {error.message}
          </Typography>
        </Alert>

        <Stack direction="row" spacing={2} justifyContent="center">
          <Button
            variant="contained"
            startIcon={<RefreshIcon />}
            onClick={handleReset}
            color="primary"
          >
            Try Again
          </Button>
          
          <Button
            variant="outlined"
            onClick={handleReload}
            color="secondary"
          >
            Reload Page
          </Button>
        </Stack>

        {process.env.NODE_ENV === 'development' && (
          <Box mt={3}>
            <Typography variant="h6" gutterBottom>
              Stack Trace (Development Only)
            </Typography>
            <Paper
              variant="outlined"
              sx={{
                p: 2,
                bgcolor: 'grey.100',
                textAlign: 'left',
                maxHeight: 200,
                overflow: 'auto',
              }}
            >
              <Typography
                variant="body2"
                component="pre"
                sx={{
                  fontFamily: 'monospace',
                  fontSize: '0.75rem',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {error.stack}
              </Typography>
            </Paper>
          </Box>
        )}
      </Paper>
    </Box>
  );
};

export default ErrorFallback;