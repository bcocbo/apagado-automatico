import React from 'react';
import { Box, Typography, Card, CardContent } from '@mui/material';
import { Helmet } from 'react-helmet-async';

const Settings: React.FC = () => {
  return (
    <>
      <Helmet>
        <title>Settings - Namespace Controller</title>
        <meta name="description" content="Application settings and configuration" />
      </Helmet>

      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          Settings
        </Typography>
        
        <Card>
          <CardContent>
            <Typography variant="body1">
              Settings functionality will be implemented here.
            </Typography>
          </CardContent>
        </Card>
      </Box>
    </>
  );
};

export default Settings;