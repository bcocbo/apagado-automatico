import React from 'react';
import { Box, Typography, Card, CardContent } from '@mui/material';
import { Helmet } from 'react-helmet-async';

const ScheduleForm: React.FC = () => {
  return (
    <>
      <Helmet>
        <title>Schedule Form - Namespace Controller</title>
        <meta name="description" content="Create or edit namespace schedules" />
      </Helmet>

      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          Schedule Form
        </Typography>
        
        <Card>
          <CardContent>
            <Typography variant="body1">
              Schedule form functionality will be implemented here.
            </Typography>
          </CardContent>
        </Card>
      </Box>
    </>
  );
};

export default ScheduleForm;