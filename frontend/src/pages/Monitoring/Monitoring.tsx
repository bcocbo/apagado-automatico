import React from 'react';
import { Box, Typography, Card, CardContent } from '@mui/material';
import { Helmet } from 'react-helmet-async';

const Monitoring: React.FC = () => {
  return (
    <>
      <Helmet>
        <title>Monitoring - Namespace Controller</title>
        <meta name="description" content="System monitoring and metrics" />
      </Helmet>

      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          Monitoring
        </Typography>
        
        <Card>
          <CardContent>
            <Typography variant="body1">
              Monitoring functionality will be implemented here.
            </Typography>
          </CardContent>
        </Card>
      </Box>
    </>
  );
};

export default Monitoring;