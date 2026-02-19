/**
 * Weekly Dashboard Component
 * Handles the weekly view of scheduled tasks in a 7x24 grid format
 */

class WeeklyDashboard {
    constructor() {
        this.currentWeekStart = this.getMondayOfCurrentWeek();
        this.cache = new Map();
        this.cacheTTL = 5 * 60 * 1000; // 5 minutes
        this.isLoading = false;
        
        // Day names for the grid
        this.dayNames = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
        this.dayDisplayNames = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
        
        // Color mapping for different namespaces
        this.namespaceColors = new Map();
        this.colorPalette = [
            '#007bff', '#28a745', '#dc3545', '#ffc107', 
            '#17a2b8', '#6f42c1', '#fd7e14', '#20c997'
        ];
    }

    /**
     * Get Monday of the current week
     */
    getMondayOfCurrentWeek() {
        const today = new Date();
        const dayOfWeek = today.getDay();
        const daysToMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek; // Sunday is 0, Monday is 1
        const monday = new Date(today);
        monday.setDate(today.getDate() + daysToMonday);
        monday.setHours(0, 0, 0, 0);
        return monday;
    }

    /**
     * Format date to YYYY-MM-DD
     */
    formatDate(date) {
        return date.toISOString().split('T')[0];
    }

    /**
     * Format date range for display
     */
    formatDateRange(startDate) {
        const endDate = new Date(startDate);
        endDate.setDate(startDate.getDate() + 6);
        
        const options = { 
            day: 'numeric', 
            month: 'short', 
            year: startDate.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined 
        };
        
        return `${startDate.toLocaleDateString('es-ES', options)} - ${endDate.toLocaleDateString('es-ES', options)}`;
    }

    /**
     * Initialize the weekly dashboard
     */
    async init() {
        try {
            await this.loadWeekData(this.currentWeekStart);
            this.updateWeekDisplay();
        } catch (error) {
            console.error('Error initializing weekly dashboard:', error);
            this.showError('Error inicializando la vista semanal');
        }
    }

    /**
     * Load week data from API with caching
     */
    async loadWeekData(weekStart) {
        const cacheKey = this.formatDate(weekStart);
        
        // Check cache first
        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTTL) {
                this.renderWeeklyGrid(cached.data);
                this.updateStatistics(cached.data);
                return cached.data;
            }
        }

        this.showLoading();
        
        try {
            const response = await fetch(`/api/weekly-schedule/${cacheKey}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Error desconocido');
            }

            // Cache the result
            this.cache.set(cacheKey, {
                data: result.data,
                timestamp: Date.now()
            });

            this.hideLoading();
            this.renderWeeklyGrid(result.data);
            this.updateStatistics(result.data);
            
            return result.data;
            
        } catch (error) {
            console.error('Error loading week data:', error);
            this.hideLoading();
            this.showError(`Error cargando datos: ${error.message}`);
            throw error;
        }
    }

    /**
     * Show loading indicator
     */
    showLoading() {
        this.isLoading = true;
        document.getElementById('weekly-loading').style.display = 'block';
        document.getElementById('weekly-grid-container').style.display = 'none';
        document.getElementById('weekly-error').style.display = 'none';
    }

    /**
     * Hide loading indicator
     */
    hideLoading() {
        this.isLoading = false;
        document.getElementById('weekly-loading').style.display = 'none';
        document.getElementById('weekly-grid-container').style.display = 'block';
    }

    /**
     * Show error message
     */
    showError(message) {
        document.getElementById('weekly-loading').style.display = 'none';
        document.getElementById('weekly-grid-container').style.display = 'none';
        document.getElementById('weekly-error').style.display = 'block';
        document.getElementById('weekly-error-message').textContent = message;
    }

    /**
     * Render the weekly grid
     */
    renderWeeklyGrid(weekData) {
        const tbody = document.getElementById('weekly-grid-body');
        tbody.innerHTML = '';

        // Generate 24 hours (00:00 to 23:00)
        for (let hour = 0; hour < 24; hour++) {
            const row = document.createElement('tr');
            
            // Time cell
            const timeCell = document.createElement('td');
            timeCell.className = 'time-cell';
            timeCell.textContent = `${hour.toString().padStart(2, '0')}:00`;
            row.appendChild(timeCell);

            // Day cells
            this.dayNames.forEach((dayName, dayIndex) => {
                const dayCell = document.createElement('td');
                const hourKey = hour.toString().padStart(2, '0');
                
                // Add weekend styling
                if (dayIndex >= 5) { // Saturday and Sunday
                    dayCell.classList.add('weekend-cell');
                }

                // Add non-business hours styling
                if (hour < 7 || hour >= 20) {
                    dayCell.classList.add('non-business-hours');
                }

                // Get tasks for this time slot
                const tasks = weekData.time_slots[dayName]?.[hourKey] || [];
                
                if (tasks.length > 0) {
                    const container = document.createElement('div');
                    container.className = 'task-slot-container';
                    
                    tasks.forEach(task => {
                        const taskSlot = this.createTaskSlot(task);
                        container.appendChild(taskSlot);
                    });
                    
                    dayCell.appendChild(container);
                } else {
                    // Empty slot
                    const emptySlot = document.createElement('div');
                    emptySlot.className = 'empty-slot';
                    emptySlot.textContent = '+';
                    dayCell.appendChild(emptySlot);
                }

                // Add click handler for time slot
                dayCell.addEventListener('click', () => {
                    this.onTimeSlotClick(dayIndex, hour, tasks);
                });

                row.appendChild(dayCell);
            });

            tbody.appendChild(row);
        }
    }

    /**
     * Create a task slot element
     */
    createTaskSlot(task) {
        const slot = document.createElement('div');
        slot.className = `task-slot ${task.operation_type}`;
        
        // Set text content (namespace name)
        slot.textContent = task.namespace_name;
        
        // Add tooltip with full task information
        const tooltipText = [
            `Namespace: ${task.namespace_name}`,
            `Operación: ${task.operation_type}`,
            `Centro de Costo: ${task.cost_center}`,
            `Hora: ${task.minute.toString().padStart(2, '0')} min`,
            task.title ? `Título: ${task.title}` : null
        ].filter(Boolean).join('\n');
        
        slot.title = tooltipText;
        
        // Add click handler
        slot.addEventListener('click', (e) => {
            e.stopPropagation();
            this.onTaskSlotClick(task);
        });

        return slot;
    }

    /**
     * Handle time slot click
     */
    onTimeSlotClick(dayIndex, hour, tasks) {
        console.log(`Clicked time slot: ${this.dayDisplayNames[dayIndex]} ${hour}:00`, tasks);
        
        if (tasks.length === 0) {
            // Could open a "create task" modal here
            console.log('Empty slot clicked - could create new task');
        } else {
            // Show tasks in this slot
            console.log('Time slot with tasks clicked');
        }
    }

    /**
     * Handle task slot click
     */
    onTaskSlotClick(task) {
        console.log('Task clicked:', task);
        
        // Could open task details modal or edit task
        if (typeof showTaskDetails === 'function') {
            showTaskDetails(task.task_id);
        }
    }

    /**
     * Update week display information
     */
    updateWeekDisplay() {
        const weekRange = this.formatDateRange(this.currentWeekStart);
        document.getElementById('current-week-range').textContent = weekRange;
    }

    /**
     * Update statistics
     */
    updateStatistics(weekData) {
        const metadata = weekData.metadata || {};
        
        document.getElementById('weekly-unique-namespaces').textContent = 
            metadata.active_namespaces?.length || 0;
        
        document.getElementById('weekly-cost-centers').textContent = 
            metadata.cost_centers?.length || 0;
        
        document.getElementById('weekly-total-tasks').textContent = 
            metadata.total_tasks || 0;
        
        // Calculate scheduled hours (rough estimate)
        const scheduledHours = Math.ceil((metadata.total_tasks || 0) * 0.5); // Assume 30 min average
        document.getElementById('weekly-scheduled-hours').textContent = scheduledHours;
        
        // Update summary
        const summary = `${metadata.total_tasks || 0} tareas programadas`;
        document.getElementById('weekly-summary').textContent = summary;
    }

    /**
     * Navigate to different week
     */
    async navigateWeek(direction) {
        if (this.isLoading) return;

        let newWeekStart;
        
        switch (direction) {
            case 'prev':
                newWeekStart = new Date(this.currentWeekStart);
                newWeekStart.setDate(this.currentWeekStart.getDate() - 7);
                break;
            case 'next':
                newWeekStart = new Date(this.currentWeekStart);
                newWeekStart.setDate(this.currentWeekStart.getDate() + 7);
                break;
            case 'current':
                newWeekStart = this.getMondayOfCurrentWeek();
                break;
            default:
                return;
        }

        this.currentWeekStart = newWeekStart;
        this.updateWeekDisplay();
        
        try {
            await this.loadWeekData(this.currentWeekStart);
        } catch (error) {
            console.error('Error navigating week:', error);
        }
    }

    /**
     * Refresh current week data
     */
    async refreshData() {
        if (this.isLoading) return;

        // Clear cache for current week
        const cacheKey = this.formatDate(this.currentWeekStart);
        this.cache.delete(cacheKey);
        
        try {
            await this.loadWeekData(this.currentWeekStart);
            
            // Show success notification
            if (typeof showNotification === 'function') {
                showNotification('Datos actualizados correctamente', 'success');
            }
        } catch (error) {
            console.error('Error refreshing data:', error);
            
            // Show error notification
            if (typeof showNotification === 'function') {
                showNotification('Error actualizando datos', 'error');
            }
        }
    }

    /**
     * Clear all cache
     */
    clearCache() {
        this.cache.clear();
        console.log('Weekly dashboard cache cleared');
    }

    /**
     * Get cache statistics
     */
    getCacheStats() {
        return {
            size: this.cache.size,
            keys: Array.from(this.cache.keys()),
            ttl: this.cacheTTL
        };
    }
}

// Global instance
let weeklyDashboard = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    weeklyDashboard = new WeeklyDashboard();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WeeklyDashboard;
}