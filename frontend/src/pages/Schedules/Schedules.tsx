import React from 'react';
import { Box, Typography, Card, CardContent } from '@mui/material';
import { Helmet } from 'react-helmet-async';

const Schedules: React.FC = () => {
  return (
    <>
      <Helmet>
        <title>Schedules - Namespace Controller</title>
        <meta name="description" content="Manage namespace schedules" />
      </Helmet>

      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          Schedules
        </Typography>
        
        <Card>
          <CardContent>
            <Typography variant="body1">
              Schedule management functionality will be implemented here.
            </Typography>
          </CardContent>
        </Card>
      </Box>
    </>
  );
};

export default Schedules;