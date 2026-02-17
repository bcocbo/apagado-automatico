// API Client with error handling, retry logic, and loading indicators
class APIClient {
    constructor(baseURL = '') {
        this.baseURL = baseURL;
        this.maxRetries = 3;
        this.retryDelay = 1000; // 1 second
        this.timeout = 30000; // 30 seconds
        this.loadingCallbacks = [];
    }

    // Register loading callback
    onLoadingChange(callback) {
        this.loadingCallbacks.push(callback);
    }

    // Notify loading state change
    notifyLoading(isLoading) {
        this.loadingCallbacks.forEach(callback => callback(isLoading));
    }

    // Generate unique request ID
    generateRequestId() {
        return `req-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    // Fetch with timeout
    async fetchWithTimeout(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('Request timeout');
            }
            throw error;
        }
    }

    // Retry logic
    async retryRequest(fn, retries = this.maxRetries) {
        for (let attempt = 1; attempt <= retries; attempt++) {
            try {
                return await fn();
            } catch (error) {
                console.warn(`Attempt ${attempt}/${retries} failed:`, error.message);
                
                if (attempt === retries) {
                    throw error;
                }
                
                // Exponential backoff
                const delay = this.retryDelay * Math.pow(2, attempt - 1);
                console.log(`Retrying in ${delay}ms...`);
                await this.sleep(delay);
            }
        }
    }

    // Sleep utility
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Validate response
    validateResponse(response) {
        if (!response) {
            throw new Error('No response received');
        }

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return response;
    }

    // Parse response
    async parseResponse(response) {
        const contentType = response.headers.get('content-type');
        
        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            
            // Check for error in response body
            if (data.error) {
                throw new Error(data.error);
            }
            
            return data;
        }
        
        return await response.text();
    }

    // Generic request method
    async request(method, endpoint, options = {}) {
        const requestId = this.generateRequestId();
        const url = `${this.baseURL}${endpoint}`;
        
        console.log(`[${requestId}] ${method} ${endpoint}`);
        
        // Show loading
        this.notifyLoading(true);
        
        try {
            const response = await this.retryRequest(async () => {
                const fetchOptions = {
                    method,
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Request-ID': requestId,
                        ...options.headers
                    },
                    ...options
                };

                if (options.body && typeof options.body === 'object') {
                    fetchOptions.body = JSON.stringify(options.body);
                }

                const res = await this.fetchWithTimeout(url, fetchOptions);
                this.validateResponse(res);
                return res;
            });

            const data = await this.parseResponse(response);
            console.log(`[${requestId}] Success:`, data);
            
            return {
                success: true,
                data,
                requestId
            };

        } catch (error) {
            console.error(`[${requestId}] Error:`, error);
            
            return {
                success: false,
                error: error.message,
                requestId
            };
        } finally {
            // Hide loading
            this.notifyLoading(false);
        }
    }

    // Convenience methods
    async get(endpoint, options = {}) {
        return this.request('GET', endpoint, options);
    }

    async post(endpoint, body, options = {}) {
        return this.request('POST', endpoint, { ...options, body });
    }

    async put(endpoint, body, options = {}) {
        return this.request('PUT', endpoint, { ...options, body });
    }

    async delete(endpoint, options = {}) {
        return this.request('DELETE', endpoint, options);
    }

    // API-specific methods
    async getNamespaces() {
        return this.get('/api/namespaces');
    }

    async getNamespacesStatus() {
        return this.get('/api/namespaces/status');
    }

    async activateNamespace(namespace, costCenter, userId = 'web-user') {
        return this.post(`/api/namespaces/${namespace}/activate`, {
            cost_center: costCenter,
            user_id: userId
        });
    }

    async deactivateNamespace(namespace, costCenter, userId = 'web-user') {
        return this.post(`/api/namespaces/${namespace}/deactivate`, {
            cost_center: costCenter,
            user_id: userId
        });
    }

    async getTasks() {
        return this.get('/api/tasks');
    }

    async createTask(task) {
        return this.post('/api/tasks', task);
    }

    async updateTask(taskId, task) {
        return this.put(`/api/tasks/${taskId}`, task);
    }

    async getTask(taskId) {
        return this.get(`/api/tasks/${taskId}`);
    }

    async deleteTask(taskId) {
        return this.delete(`/api/tasks/${taskId}`);
    }

    async runTask(taskId) {
        return this.post(`/api/tasks/${taskId}/run`);
    }

    async getLogs(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const endpoint = `/api/logs${queryString ? '?' + queryString : ''}`;
        return this.get(endpoint);
    }

    async getTaskStats() {
        return this.get('/api/tasks/stats');
    }

    async getHealth() {
        return this.get('/health');
    }
    
    async validateCostCenter(costCenter, userId = 'web-user') {
        return this.get(`/api/cost-centers/${costCenter}/validate`, {
            headers: {
                'X-User-ID': userId
            }
        });
    }
}

// Create singleton instance
const apiClient = new APIClient();
