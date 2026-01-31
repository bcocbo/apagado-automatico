import React from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';
import { BaseComponentProps } from '../../types';

interface LoadingSpinnerProps extends BaseComponentProps {
  size?: number;
  message?: string;
  color?: 'primary' | 'secondary' | 'inherit';
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 40,
  message = 'Loading...',
  color = 'primary',
  className,
  'data-testid': testId,
}) => {
  return (
    <Box
      display="flex"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      gap={2}
      className={className}
      data-testid={testId}
    >
      <CircularProgress size={size} color={color} />
      {message && (
        <Typography variant="body2" color="text.secondary">
          {message}
        </Typography>
      )}
    </Box>
  );
};

export default LoadingSpinner;