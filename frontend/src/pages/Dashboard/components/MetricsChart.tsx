import React from 'react';
import {
  Box,
  Typography,
  useTheme,
} from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';
import { SystemMetrics } from '../../../types';

interface MetricsChartProps {
  metrics: SystemMetrics;
}

const MetricsChart: React.FC<MetricsChartProps> = ({ metrics }) => {
  const theme = useTheme();

  // Generate sample time series data for demonstration
  const generateTimeSeriesData = () => {
    const now = new Date();
    const data = [];
    
    for (let i = 23; i >= 0; i--) {
      const time = new Date(now.getTime() - i * 60 * 60 * 1000);
      data.push({
        time: time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        operations: Math.floor(Math.random() * 20) + 5,
        responseTime: Math.floor(Math.random() * 100) + 50,
        activeNamespaces: Math.floor(Math.random() * 10) + (metrics.active_namespaces || 15),
        cpuUsage: Math.floor(Math.random() * 30) + 20,
        memoryUsage: Math.floor(Math.random() * 40) + 30,
      });
    }
    
    return data;
  };

  const timeSeriesData = generateTimeSeriesData();

  const formatTooltipValue = (value: number, name: string) => {
    switch (name) {
      case 'responseTime':
        return [`${value}ms`, 'Response Time'];
      case 'operations':
        return [value, 'Operations'];
      case 'activeNamespaces':
        return [value, 'Active Namespaces'];
      case 'cpuUsage':
        return [`${value}%`, 'CPU Usage'];
      case 'memoryUsage':
        return [`${value}%`, 'Memory Usage'];
      default:
        return [value, name];
    }
  };

  return (
    <Box>
      {/* Operations and Response Time Chart */}
      <Box mb={3}>
        <Typography variant="subtitle2" gutterBottom>
          Operations & Response Time (24h)
        </Typography>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={timeSeriesData}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
            <XAxis 
              dataKey="time" 
              stroke={theme.palette.text.secondary}
              fontSize={12}
            />
            <YAxis 
              yAxisId="left"
              stroke={theme.palette.text.secondary}
              fontSize={12}
            />
            <YAxis 
              yAxisId="right" 
              orientation="right"
              stroke={theme.palette.text.secondary}
              fontSize={12}
            />
            <Tooltip 
              formatter={formatTooltipValue}
              contentStyle={{
                backgroundColor: theme.palette.background.paper,
                border: `1px solid ${theme.palette.divider}`,
                borderRadius: theme.shape.borderRadius,
              }}
            />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="operations"
              stroke={theme.palette.primary.main}
              strokeWidth={2}
              dot={false}
              name="operations"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="responseTime"
              stroke={theme.palette.secondary.main}
              strokeWidth={2}
              dot={false}
              name="responseTime"
            />
          </LineChart>
        </ResponsiveContainer>
      </Box>

      {/* Resource Usage Chart */}
      <Box>
        <Typography variant="subtitle2" gutterBottom>
          Resource Usage (24h)
        </Typography>
        <ResponsiveContainer width="100%" height={180}>
          <AreaChart data={timeSeriesData}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
            <XAxis 
              dataKey="time" 
              stroke={theme.palette.text.secondary}
              fontSize={12}
            />
            <YAxis 
              stroke={theme.palette.text.secondary}
              fontSize={12}
              domain={[0, 100]}
            />
            <Tooltip 
              formatter={formatTooltipValue}
              contentStyle={{
                backgroundColor: theme.palette.background.paper,
                border: `1px solid ${theme.palette.divider}`,
                borderRadius: theme.shape.borderRadius,
              }}
            />
            <Area
              type="monotone"
              dataKey="cpuUsage"
              stackId="1"
              stroke={theme.palette.info.main}
              fill={theme.palette.info.light}
              fillOpacity={0.6}
              name="cpuUsage"
            />
            <Area
              type="monotone"
              dataKey="memoryUsage"
              stackId="1"
              stroke={theme.palette.warning.main}
              fill={theme.palette.warning.light}
              fillOpacity={0.6}
              name="memoryUsage"
            />
          </AreaChart>
        </ResponsiveContainer>
      </Box>

      {/* Current Metrics Summary */}
      <Box mt={2} display="flex" justifyContent="space-between" flexWrap="wrap">
        <Typography variant="body2" color="text.secondary">
          Avg Response Time: {metrics.avg_response_time || 'N/A'}ms
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Success Rate: {metrics.success_rate || 'N/A'}%
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Error Rate: {metrics.error_rate || 'N/A'}%
        </Typography>
      </Box>
    </Box>
  );
};

export default MetricsChart;