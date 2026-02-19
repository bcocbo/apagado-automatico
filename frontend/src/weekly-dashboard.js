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
            // Show modal to create new task for this time slot
            this.showCreateTaskModal(dayIndex, hour);
        } else {
            // Show existing tasks in this slot
            this.showTasksInSlot(dayIndex, hour, tasks);
        }
    }

    /**
     * Show modal to create a new task for a specific time slot
     */
    showCreateTaskModal(dayIndex, hour) {
        // Create and show a modal for task creation
        const modal = this.createTaskCreationModal(dayIndex, hour);
        document.body.appendChild(modal);
        
        // Show the modal using Bootstrap
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
        
        // Clean up modal when hidden
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
    }

    /**
     * Create task creation modal HTML
     */
    createTaskCreationModal(dayIndex, hour) {
        const dayName = this.dayDisplayNames[dayIndex];
        const timeString = `${hour.toString().padStart(2, '0')}:00`;
        
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'weeklyTaskModal';
        modal.tabIndex = -1;
        
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-plus-circle"></i> 
                            Programar Tarea - ${dayName} ${timeString}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="weeklyTaskForm">
                            <div class="mb-3">
                                <label for="taskNamespace" class="form-label">Namespace <span class="text-danger">*</span></label>
                                <select class="form-control" id="taskNamespace" required>
                                    <option value="">Cargando namespaces...</option>
                                </select>
                                <small class="form-text text-muted">Selecciona el namespace a programar</small>
                            </div>
                            
                            <div class="mb-3">
                                <label for="taskOperation" class="form-label">Tipo de Programación <span class="text-danger">*</span></label>
                                <select class="form-control" id="taskOperation" required>
                                    <option value="duration">Activar por duración específica</option>
                                </select>
                                <small class="form-text text-muted">Se creará automáticamente la tarea de activación y desactivación</small>
                            </div>
                            
                            <div class="mb-3">
                                <label for="taskDuration" class="form-label">Duración (horas) <span class="text-danger">*</span></label>
                                <select class="form-control" id="taskDuration" required>
                                    <option value="1">1 hora</option>
                                    <option value="2">2 horas</option>
                                    <option value="4">4 horas</option>
                                    <option value="8">8 horas</option>
                                    <option value="12">12 horas</option>
                                    <option value="24">24 horas</option>
                                </select>
                                <small class="form-text text-muted">¿Por cuántas horas debe estar activo el namespace?</small>
                            </div>
                            
                            <div class="mb-3">
                                <label for="taskCostCenter" class="form-label">Centro de Costo <span class="text-danger">*</span></label>
                                <select class="form-control" id="taskCostCenter" required>
                                    <option value="">Seleccionar...</option>
                                    <option value="default">default</option>
                                    <option value="development">development</option>
                                    <option value="testing">testing</option>
                                    <option value="production">production</option>
                                </select>
                            </div>
                            
                            <div class="mb-3">
                                <label for="taskMinute" class="form-label">Minuto</label>
                                <select class="form-control" id="taskMinute">
                                    <option value="0">00 (inicio de hora)</option>
                                    <option value="15">15</option>
                                    <option value="30">30</option>
                                    <option value="45">45</option>
                                </select>
                            </div>
                            
                            <div class="mb-3">
                                <label for="taskDescription" class="form-label">Descripción (opcional)</label>
                                <textarea class="form-control" id="taskDescription" rows="2" 
                                    placeholder="Descripción adicional de la tarea"></textarea>
                            </div>
                            
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle"></i>
                                <strong>Programación:</strong> ${dayName} a las ${timeString}
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                        <button type="button" class="btn btn-primary" onclick="weeklyDashboard.createTaskFromModal(${dayIndex}, ${hour})">
                            <i class="fas fa-save"></i> Crear Tarea
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Load schedulable namespaces when modal is shown
        modal.addEventListener('shown.bs.modal', () => {
            this.loadSchedulableNamespaces();
        });
        
        return modal;
    }

    /**
     * Load schedulable namespaces for the modal
     */
    async loadSchedulableNamespaces() {
        const select = document.getElementById('taskNamespace');
        
        if (!select) {
            console.error('taskNamespace select element not found');
            return;
        }
        
        try {
            console.log('Loading schedulable namespaces...');
            
            // Show loading state
            select.innerHTML = '<option value="">Cargando namespaces...</option>';
            select.disabled = true;
            
            const response = await fetch('/api/namespaces/schedulable');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('Schedulable namespaces response:', data);
            
            // Check if response indicates success
            if (data.success === false) {
                throw new Error(data.error || 'Error desconocido del servidor');
            }
            
            // Re-enable select
            select.disabled = false;
            select.innerHTML = '<option value="">Seleccionar namespace...</option>';
            
            if (data.schedulable_namespaces && data.schedulable_namespaces.length > 0) {
                data.schedulable_namespaces.forEach(ns => {
                    const option = document.createElement('option');
                    option.value = ns.name;
                    option.textContent = `${ns.name} ${ns.is_active ? '(activo)' : '(inactivo)'}`;
                    select.appendChild(option);
                });
                console.log(`Added ${data.schedulable_namespaces.length} namespaces to select`);
            } else {
                select.innerHTML = '<option value="">No hay namespaces programables</option>';
                console.warn('No schedulable namespaces found');
            }
            
        } catch (error) {
            console.error('Error loading schedulable namespaces:', error);
            
            // Re-enable select and show error
            select.disabled = false;
            select.innerHTML = '<option value="">Error cargando namespaces</option>';
            
            // Show user-friendly error notification
            if (typeof showNotification === 'function') {
                showNotification(`Error cargando namespaces: ${error.message}`, 'error');
            } else {
                // Fallback to alert if notification system not available
                console.warn('showNotification function not available, using alert');
                alert(`Error cargando namespaces: ${error.message}`);
            }
        }
    }

    /**
     * Create task from modal form
     */
    async createTaskFromModal(dayIndex, hour) {
        try {
            const form = document.getElementById('weeklyTaskForm');
            
            const namespace = document.getElementById('taskNamespace').value;
            const operation = document.getElementById('taskOperation').value;
            const costCenter = document.getElementById('taskCostCenter').value;
            const minute = parseInt(document.getElementById('taskMinute').value);
            const duration = parseInt(document.getElementById('taskDuration').value);
            const description = document.getElementById('taskDescription').value;
            
            // Validate required fields
            if (!namespace || !operation || !costCenter || !duration) {
                alert('Por favor completa todos los campos requeridos');
                return;
            }
            
            // Show loading state
            const createButton = document.querySelector('#weeklyTaskModal .btn-primary');
            const originalText = createButton.innerHTML;
            createButton.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Creando...';
            createButton.disabled = true;
            
            try {
                // Create activation task
                const activationResponse = await fetch('/api/weekly-schedule/create-task', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        namespace: namespace,
                        day_of_week: dayIndex,
                        hour: hour,
                        minute: minute,
                        operation_type: 'activate',
                        cost_center: costCenter,
                        description: description || `Activar ${namespace} por ${duration} horas`,
                        user_id: 'weekly-view-user',
                        requested_by: 'weekly-view-user'
                    })
                });
                
                const activationResult = await activationResponse.json();
                
                if (!activationResponse.ok || !activationResult.success) {
                    throw new Error(activationResult.error || 'Error creando tarea de activación');
                }
                
                // Calculate deactivation time
                const deactivationHour = (hour + duration) % 24;
                const dayOffset = Math.floor((hour + duration) / 24);
                const deactivationDay = (dayIndex + dayOffset) % 7; // Wrap to next week if needed
                
                // Create deactivation task
                const deactivationResponse = await fetch('/api/weekly-schedule/create-task', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        namespace: namespace,
                        day_of_week: deactivationDay,
                        hour: deactivationHour,
                        minute: minute,
                        operation_type: 'deactivate',
                        cost_center: costCenter,
                        description: description || `Desactivar ${namespace} después de ${duration} horas`,
                        user_id: 'weekly-view-user',
                        requested_by: 'weekly-view-user'
                    })
                });
                
                const deactivationResult = await deactivationResponse.json();
                
                if (!deactivationResponse.ok || !deactivationResult.success) {
                    console.warn('Error creating deactivation task:', deactivationResult.error);
                    // Continue anyway - activation was successful
                    if (typeof showNotification === 'function') {
                        showNotification(`Tarea de activación creada, pero falló la desactivación: ${deactivationResult.error}`, 'warning');
                    }
                } else {
                    // Both tasks created successfully
                    if (typeof showNotification === 'function') {
                        showNotification(`Tareas creadas: activación y desactivación después de ${duration} horas`, 'success');
                    } else {
                        alert(`Tareas creadas exitosamente: activación y desactivación después de ${duration} horas`);
                    }
                }
                
                // Success - close modal and refresh data
                const modal = bootstrap.Modal.getInstance(document.getElementById('weeklyTaskModal'));
                modal.hide();
                
                // Refresh weekly data
                await this.refreshData();
                
            } catch (error) {
                console.error('Error creating tasks:', error);
                
                // Show error message
                if (typeof showNotification === 'function') {
                    showNotification(`Error creando tareas: ${error.message}`, 'error');
                } else {
                    alert(`Error creando tareas: ${error.message}`);
                }
                
                // Restore button state
                createButton.innerHTML = originalText;
                createButton.disabled = false;
            }
            
        } catch (error) {
            console.error('Error in createTaskFromModal:', error);
            alert(`Error inesperado: ${error.message}`);
            
            // Restore button state
            const createButton = document.querySelector('#weeklyTaskModal .btn-primary');
            if (createButton) {
                createButton.innerHTML = '<i class="fas fa-save"></i> Crear Tarea';
                createButton.disabled = false;
            }
        }
    }

    /**
     * Show existing tasks in a time slot
     */
    showTasksInSlot(dayIndex, hour, tasks) {
        console.log(`Showing ${tasks.length} tasks for ${this.dayDisplayNames[dayIndex]} ${hour}:00`, tasks);
        
        // Could implement a modal to show/edit existing tasks
        // For now, just log the information
        if (tasks.length === 1) {
            // Single task - could open edit modal
            console.log('Single task clicked - could open edit modal');
        } else {
            // Multiple tasks - could show list modal
            console.log('Multiple tasks clicked - could show list modal');
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