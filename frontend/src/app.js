// Task Scheduler Application
class TaskScheduler {
    constructor() {
        this.calendar = null;
        this.tasks = [];
        this.namespaces = [];
        this.namespacesStatus = {};
        this.currentTaskId = null;
        this.init();
    }

    init() {
        this.initCalendar();
        this.bindEvents();
        this.loadTasks();
        this.loadNamespaces();
        this.loadNamespacesStatus();
        this.updateDashboard();
        this.showDashboard();
        
        // Auto-refresh every 30 seconds
        setInterval(() => {
            this.loadNamespacesStatus();
            this.updateDashboard();
            
            // Also refresh tasks if on scheduler view
            const schedulerSection = document.getElementById('scheduler-section');
            if (schedulerSection && schedulerSection.style.display !== 'none') {
                this.loadTasks();
            }
        }, 30000);
    }

    initCalendar() {
        const calendarEl = document.getElementById('calendar');
        this.calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek'
            },
            editable: false,  // Disable drag and drop for now
            selectable: false,  // Disable date selection for now
            selectMirror: true,
            dayMaxEvents: true,
            weekends: true,
            eventClick: this.handleEventClick.bind(this),
            eventsSet: this.handleEvents.bind(this),
            eventClassNames: function(arg) {
                return ['task-' + arg.event.extendedProps.status];
            },
            eventContent: function(arg) {
                // Custom event rendering
                const status = arg.event.extendedProps.status || 'pending';
                const operationType = arg.event.extendedProps.operation_type || 'command';
                
                let icon = '📋';
                if (operationType === 'activate') icon = '✅';
                else if (operationType === 'deactivate') icon = '⏸️';
                
                return {
                    html: `<div class="fc-event-main-frame">
                        <div class="fc-event-title-container">
                            <div class="fc-event-title">${icon} ${arg.event.title}</div>
                        </div>
                    </div>`
                };
            },
            eventDidMount: function(info) {
                // Add tooltip with task details
                const task = info.event.extendedProps;
                const tooltip = `
                    Tipo: ${task.operation_type || 'command'}
                    Namespace: ${task.namespace || 'N/A'}
                    Centro de Costo: ${task.cost_center || 'N/A'}
                    Estado: ${task.status || 'pending'}
                    ${task.schedule ? 'Programación: ' + task.schedule : ''}
                `;
                info.el.title = tooltip.trim();
            }
        });
        this.calendar.render();
    }

    bindEvents() {
        document.getElementById('task-form').addEventListener('submit', this.handleTaskSubmit.bind(this));
        
        // Add cost center validation on change
        const nsCostCenter = document.getElementById('ns-cost-center');
        if (nsCostCenter) {
            nsCostCenter.addEventListener('change', this.validateCostCenterOnChange.bind(this));
        }
        
        const taskCostCenter = document.getElementById('task-cost-center');
        if (taskCostCenter) {
            taskCostCenter.addEventListener('change', this.validateCostCenterOnChange.bind(this));
        }
        
        // Add cron validation on input
        const taskSchedule = document.getElementById('task-schedule');
        if (taskSchedule) {
            taskSchedule.addEventListener('input', this.validateCronExpression.bind(this));
            taskSchedule.addEventListener('blur', this.validateCronExpression.bind(this));
        }
    }
    
    validateCronExpression(event) {
        const cronInput = event.target;
        const cronExpression = cronInput.value.trim();
        const feedbackElement = document.getElementById('cron-validation-feedback');
        
        if (!cronExpression) {
            cronInput.classList.remove('is-valid', 'is-invalid');
            if (feedbackElement) {
                feedbackElement.innerHTML = '';
                feedbackElement.className = '';
            }
            return;
        }
        
        const validation = this.parseCronExpression(cronExpression);
        
        if (validation.valid) {
            cronInput.classList.remove('is-invalid');
            cronInput.classList.add('is-valid');
            if (feedbackElement) {
                feedbackElement.className = 'valid';
                feedbackElement.innerHTML = `
                    <i class="fas fa-check-circle"></i> 
                    <strong>Expresión válida:</strong> ${validation.description}
                `;
            }
        } else {
            cronInput.classList.remove('is-valid');
            cronInput.classList.add('is-invalid');
            if (feedbackElement) {
                feedbackElement.className = 'invalid';
                feedbackElement.innerHTML = `
                    <i class="fas fa-exclamation-circle"></i> 
                    <strong>Error:</strong> ${validation.error}
                `;
            }
        }
    }
    
    parseCronExpression(cronExpression) {
        // Basic cron validation (minute hour day month weekday)
        const parts = cronExpression.split(/\s+/);
        
        if (parts.length !== 5) {
            return {
                valid: false,
                error: 'La expresión cron debe tener exactamente 5 campos (minuto hora día mes día-semana)'
            };
        }
        
        const [minute, hour, day, month, weekday] = parts;
        
        // Validate each field
        const validations = [
            { value: minute, name: 'Minuto', min: 0, max: 59 },
            { value: hour, name: 'Hora', min: 0, max: 23 },
            { value: day, name: 'Día', min: 1, max: 31 },
            { value: month, name: 'Mes', min: 1, max: 12 },
            { value: weekday, name: 'Día de semana', min: 0, max: 7 }
        ];
        
        for (const field of validations) {
            const validation = this.validateCronField(field.value, field.min, field.max);
            if (!validation.valid) {
                return {
                    valid: false,
                    error: `${field.name}: ${validation.error}`
                };
            }
        }
        
        // Generate human-readable description
        const description = this.describeCronExpression(minute, hour, day, month, weekday);
        
        return {
            valid: true,
            description: description
        };
    }
    
    validateCronField(value, min, max) {
        // Allow * (any)
        if (value === '*') {
            return { valid: true };
        }
        
        // Allow */n (every n)
        if (value.startsWith('*/')) {
            const step = parseInt(value.substring(2));
            if (isNaN(step) || step < 1) {
                return { valid: false, error: 'Valor de paso inválido' };
            }
            return { valid: true };
        }
        
        // Allow ranges (n-m)
        if (value.includes('-')) {
            const [start, end] = value.split('-').map(v => parseInt(v));
            if (isNaN(start) || isNaN(end) || start < min || end > max || start > end) {
                return { valid: false, error: `Rango inválido (debe estar entre ${min}-${max})` };
            }
            return { valid: true };
        }
        
        // Allow lists (n,m,o)
        if (value.includes(',')) {
            const values = value.split(',').map(v => parseInt(v));
            for (const v of values) {
                if (isNaN(v) || v < min || v > max) {
                    return { valid: false, error: `Valor inválido en lista (debe estar entre ${min}-${max})` };
                }
            }
            return { valid: true };
        }
        
        // Single value
        const num = parseInt(value);
        if (isNaN(num) || num < min || num > max) {
            return { valid: false, error: `Debe estar entre ${min} y ${max}` };
        }
        
        return { valid: true };
    }
    
    describeCronExpression(minute, hour, day, month, weekday) {
        let description = 'Se ejecutará ';
        
        // Describe frequency
        if (minute.startsWith('*/')) {
            const interval = minute.substring(2);
            description += `cada ${interval} minuto(s)`;
        } else if (minute === '*') {
            description += 'cada minuto';
        } else {
            description += `en el minuto ${minute}`;
        }
        
        if (hour.startsWith('*/')) {
            const interval = hour.substring(2);
            description += `, cada ${interval} hora(s)`;
        } else if (hour !== '*') {
            description += ` a las ${hour}:${minute.padStart(2, '0')}`;
        }
        
        // Describe day/month
        if (day !== '*') {
            description += `, día ${day}`;
        }
        
        if (month !== '*') {
            const monthNames = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                              'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
            if (month.includes(',')) {
                description += ` en los meses: ${month}`;
            } else if (month.includes('-')) {
                description += ` de ${month}`;
            } else {
                description += ` en ${monthNames[parseInt(month)]}`;
            }
        }
        
        // Describe weekday
        if (weekday !== '*') {
            const dayNames = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
            if (weekday.includes('-')) {
                const [start, end] = weekday.split('-');
                description += `, de ${dayNames[parseInt(start)]} a ${dayNames[parseInt(end)]}`;
            } else if (weekday.includes(',')) {
                const days = weekday.split(',').map(d => dayNames[parseInt(d)]).join(', ');
                description += `, los días: ${days}`;
            } else {
                description += `, los ${dayNames[parseInt(weekday)]}`;
            }
        }
        
        return description;
    }
    
    async validateCostCenterOnChange(event) {
        const costCenter = event.target.value;
        const elementId = event.target.id;
        
        if (!costCenter) {
            this.clearCostCenterValidation(elementId);
            return;
        }
        
        // Show validating state
        event.target.disabled = true;
        
        const validationResult = await apiClient.validateCostCenter(costCenter);
        
        event.target.disabled = false;
        
        if (validationResult.success && validationResult.data.is_authorized) {
            this.markCostCenterValid(elementId);
        } else {
            this.markCostCenterInvalid(elementId);
        }
    }

    // handleDateSelect disabled - use form to create tasks
    // handleDateSelect(selectInfo) {
    //     const title = prompt('Nombre de la nueva tarea:');
    //     const calendarApi = selectInfo.view.calendar;
    //     calendarApi.unselect();
    //     if (title) {
    //         const task = {
    //             id: this.generateId(),
    //             title: title,
    //             start: selectInfo.startStr,
    //             end: selectInfo.endStr,
    //             allDay: selectInfo.allDay,
    //             status: 'pending',
    //             command: '',
    //             schedule: '',
    //             namespace: 'default'
    //         };
    //         calendarApi.addEvent(task);
    //         this.tasks.push(task);
    //         this.saveTasks();
    //         this.updateDashboard();
    //     }
    // }

    handleEventClick(clickInfo) {
        const task = this.tasks.find(t => t.id === clickInfo.event.id);
        if (task) {
            this.showTaskDetails(task);
        }
    }

    handleEvents(events) {
        // Handle events change
    }

    handleTaskSubmit(e) {
        e.preventDefault();
        
        const taskType = document.getElementById('task-type').value;
        const costCenter = document.getElementById('task-cost-center').value;
        
        // Validate cost center before creating task
        this.validateAndCreateTask(taskType, costCenter);
    }
    
    async validateAndCreateTask(taskType, costCenter) {
        const createBtn = document.getElementById('create-task-btn');
        
        // Disable button during validation
        if (createBtn) {
            createBtn.disabled = true;
            createBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Validando...';
        }
        
        try {
            // Validate cost center
            const validationResult = await apiClient.validateCostCenter(costCenter);
            
            if (!validationResult.success) {
                notificationManager.error(`Error al validar centro de costo: ${validationResult.error}`);
                return;
            }
            
            if (!validationResult.data.is_authorized) {
                notificationManager.error(`El centro de costo "${costCenter}" no está autorizado para crear tareas`);
                this.markCostCenterInvalid('task-cost-center');
                return;
            }
            
            // Mark as valid and proceed
            this.markCostCenterValid('task-cost-center');
            
            // Update button text
            if (createBtn) {
                createBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Creando tarea...';
            }
            
            const task = {
                id: this.generateId(),
                title: document.getElementById('task-name').value,
                description: document.getElementById('task-description').value || '',
                schedule: document.getElementById('task-schedule').value,
                namespace: document.getElementById('task-namespace').value,
                cost_center: costCenter,
                operation_type: taskType,
                status: 'pending',
                start: new Date().toISOString(),
                allDay: false
            };

            // Add command only for command type tasks
            if (taskType === 'command') {
                task.command = document.getElementById('task-command').value;
            }

            await this.createTask(task);
            
            // Reset form on success
            this.resetTaskForm();
            
        } catch (error) {
            notificationManager.error(`Error inesperado: ${error.message}`);
        } finally {
            // Re-enable button
            if (createBtn) {
                createBtn.disabled = false;
                createBtn.innerHTML = '<i class="fas fa-plus-circle"></i> Crear Tarea';
            }
        }
    }
    
    resetTaskForm() {
        const form = document.getElementById('task-form');
        if (form) {
            form.reset();
            
            // Clear validation states
            this.clearCostCenterValidation('task-cost-center');
            
            // Reset command field visibility
            const commandField = document.getElementById('command-field');
            if (commandField) {
                commandField.style.display = 'none';
            }
            
            // Clear cron validation feedback
            const cronFeedback = document.getElementById('cron-validation-feedback');
            if (cronFeedback) {
                cronFeedback.innerHTML = '';
            }
            
            notificationManager.info('Formulario limpiado');
        }
    }

    async loadNamespaces() {
        // Show loading state in selects
        this.setNamespaceSelectsLoading(true);
        
        const result = await apiClient.getNamespaces();
        
        if (result.success) {
            this.namespaces = result.data;
            this.populateNamespaceSelects();
            console.log(`Loaded ${this.namespaces.length} namespaces successfully`);
        } else {
            notificationManager.error(`Error al cargar namespaces: ${result.error}`);
            console.error('Error loading namespaces:', result.error);
            this.setNamespaceSelectsError();
        }
    }
    
    setNamespaceSelectsLoading(isLoading) {
        const selects = ['task-namespace', 'ns-select'];
        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            if (select) {
                if (isLoading) {
                    select.disabled = true;
                    // Keep first option, add loading message
                    while (select.children.length > 1) {
                        select.removeChild(select.lastChild);
                    }
                    const option = document.createElement('option');
                    option.value = '';
                    option.textContent = 'Cargando namespaces...';
                    option.disabled = true;
                    select.appendChild(option);
                } else {
                    select.disabled = false;
                }
            }
        });
    }
    
    setNamespaceSelectsError() {
        const selects = ['task-namespace', 'ns-select'];
        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            if (select) {
                select.disabled = false;
                // Keep first option, add error message
                while (select.children.length > 1) {
                    select.removeChild(select.lastChild);
                }
                const option = document.createElement('option');
                option.value = '';
                option.textContent = 'Error al cargar namespaces';
                option.disabled = true;
                option.style.color = 'red';
                select.appendChild(option);
            }
        });
    }

    async loadNamespacesStatus() {
        const result = await apiClient.getNamespacesStatus();
        
        if (result.success) {
            this.namespacesStatus = result.data;
            this.updateNamespaceStatus();
            this.updateLastUpdateTime();
        } else {
            console.error('Error loading namespace status:', result.error);
            // Don't show notification for status updates to avoid spam
        }
    }
    
    updateLastUpdateTime() {
        const timeElement = document.getElementById('last-update-time');
        if (timeElement) {
            const now = new Date();
            const timeString = now.toLocaleTimeString('es-ES', { 
                hour: '2-digit', 
                minute: '2-digit',
                second: '2-digit'
            });
            timeElement.textContent = `Última actualización: ${timeString}`;
        }
    }

    populateNamespaceSelects() {
        const selects = ['task-namespace', 'ns-select'];
        
        if (!this.namespaces || this.namespaces.length === 0) {
            console.warn('No namespaces available to populate');
            return;
        }
        
        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            if (!select) {
                console.warn(`Select element with id '${selectId}' not found`);
                return;
            }
            
            // Clear all existing options
            select.innerHTML = '';
            
            // Add default "select" option for ns-select
            if (selectId === 'ns-select') {
                const defaultOption = document.createElement('option');
                defaultOption.value = '';
                defaultOption.textContent = 'Seleccionar namespace...';
                select.appendChild(defaultOption);
            }
            
            // Add all namespaces
            this.namespaces.forEach(namespace => {
                const option = document.createElement('option');
                option.value = namespace;
                option.textContent = namespace;
                select.appendChild(option);
            });
            
            console.log(`Populated ${selectId} with ${this.namespaces.length} namespaces`);
        });
    }

    updateNamespaceStatus() {
        if (!this.namespacesStatus) return;
        
        const activeCount = this.namespacesStatus.active_count || 0;
        const isNonBusinessHours = this.namespacesStatus.is_non_business_hours;
        
        // Update active namespace count
        document.getElementById('active-ns-count').textContent = activeCount;
        
        // Update progress bar
        const progressBar = document.getElementById('ns-progress');
        const percentage = (activeCount / 5) * 100;
        progressBar.style.width = `${percentage}%`;
        progressBar.className = `progress-bar ${percentage > 80 ? 'bg-danger' : percentage > 60 ? 'bg-warning' : 'bg-success'}`;
        
        // Update business hours status
        const statusElement = document.getElementById('business-hours-status');
        if (isNonBusinessHours) {
            statusElement.textContent = 'Horario no hábil - Límite de 5 namespaces';
            statusElement.className = 'text-warning';
        } else {
            statusElement.textContent = 'Horario laboral - Sin límite';
            statusElement.className = 'text-success';
        }
        
        // Update namespace status list with highlighting
        const highlightNs = this.lastOperationNamespace || null;
        const highlightType = this.lastOperationType || null;
        this.updateNamespaceStatusList(highlightNs, highlightType);
        
        // Clear highlight info after use
        this.lastOperationNamespace = null;
        this.lastOperationType = null;
    }
    
    updateNamespaceStatusList(highlightNamespace = null, highlightType = null) {
        const container = document.getElementById('namespace-status-list');
        if (!container) return;
        
        // Add updating animation
        container.classList.add('updating');
        
        const namespaces = this.namespacesStatus.namespaces || [];
        
        if (namespaces.length === 0) {
            container.innerHTML = '<div class="list-group-item text-center text-muted">No hay namespaces disponibles</div>';
            container.classList.remove('updating');
            return;
        }
        
        // Filter out system namespaces for cleaner display
        const userNamespaces = namespaces.filter(ns => !ns.is_system);
        
        if (userNamespaces.length === 0) {
            container.innerHTML = '<div class="list-group-item text-center text-muted">No hay namespaces de usuario</div>';
            container.classList.remove('updating');
            return;
        }
        
        container.innerHTML = userNamespaces.map(ns => {
            const statusBadge = ns.is_active 
                ? '<span class="badge bg-success">Activo</span>' 
                : '<span class="badge bg-secondary">Inactivo</span>';
            
            const podsInfo = ns.active_pods > 0 
                ? `<small class="text-muted">Pods: ${ns.active_pods}</small>` 
                : '';
            
            const deploymentsInfo = ns.deployments && ns.deployments.length > 0
                ? `<small class="text-muted ms-2">Deployments: ${ns.deployments.length}</small>`
                : '';
            
            const statefulsetsInfo = ns.statefulsets && ns.statefulsets.length > 0
                ? `<small class="text-muted ms-2">StatefulSets: ${ns.statefulsets.length}</small>`
                : '';
            
            // Add highlight class if this is the namespace that was just modified
            const highlightClass = (highlightNamespace === ns.name && highlightType) 
                ? `highlight-${highlightType}` 
                : '';
            
            return `
                <div class="list-group-item ${highlightClass}" data-namespace="${ns.name}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${ns.name}</strong>
                            ${statusBadge}
                        </div>
                        <div class="text-end">
                            ${podsInfo}
                            ${deploymentsInfo}
                            ${statefulsetsInfo}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        // Remove animation after a short delay
        setTimeout(() => {
            container.classList.remove('updating');
        }, 300);
    }

    async activateNamespace() {
        const namespace = document.getElementById('ns-select').value;
        const costCenter = document.getElementById('ns-cost-center').value;
        
        if (!namespace) {
            notificationManager.warning('Por favor selecciona un namespace');
            return;
        }
        
        if (!costCenter) {
            notificationManager.warning('Por favor selecciona un centro de costo');
            return;
        }
        
        // Show confirmation dialog
        const confirmed = await this.showConfirmation(
            'Confirmar Activación',
            `¿Está seguro de que desea activar el namespace <strong>${namespace}</strong> con el centro de costo <strong>${costCenter}</strong>?`,
            'success'
        );
        
        if (!confirmed) {
            return;
        }
        
        const activateBtn = document.querySelector('button.btn-success');
        const deactivateBtn = document.querySelector('button.btn-warning');
        
        // Disable buttons during operation
        this.setOperationInProgress(true, activateBtn, deactivateBtn);
        
        try {
            // Validate cost center before proceeding
            notificationManager.info('Validando centro de costo...');
            const validationResult = await apiClient.validateCostCenter(costCenter);
            
            if (!validationResult.success) {
                notificationManager.error(`Error al validar centro de costo: ${validationResult.error}`);
                return;
            }
            
            if (!validationResult.data.is_authorized) {
                notificationManager.error(`El centro de costo "${costCenter}" no está autorizado para realizar operaciones`);
                this.markCostCenterInvalid('ns-cost-center');
                return;
            }
            
            // Mark cost center as valid
            this.markCostCenterValid('ns-cost-center');
            
            // Show activating message
            notificationManager.info(`Activando namespace ${namespace}...`);
            
            // Proceed with activation
            const result = await apiClient.activateNamespace(namespace, costCenter);
            
            if (result.success) {
                // Show success with animation
                this.showOperationSuccess('activate', namespace);
                notificationManager.success(result.data.message || 'Namespace activado exitosamente');
                
                // Refresh status immediately
                await this.loadNamespacesStatus();
            } else {
                // Show error with animation
                this.showOperationError('activate', namespace, result.error);
                notificationManager.error(`Error al activar namespace: ${result.error}`);
            }
        } catch (error) {
            this.showOperationError('activate', namespace, error.message);
            notificationManager.error(`Error inesperado: ${error.message}`);
        } finally {
            // Re-enable buttons
            this.setOperationInProgress(false, activateBtn, deactivateBtn);
        }
    }

    async deactivateNamespace() {
        const namespace = document.getElementById('ns-select').value;
        const costCenter = document.getElementById('ns-cost-center').value;
        
        if (!namespace) {
            notificationManager.warning('Por favor selecciona un namespace');
            return;
        }
        
        if (!costCenter) {
            notificationManager.warning('Por favor selecciona un centro de costo');
            return;
        }
        
        // Show confirmation dialog with warning
        const confirmed = await this.showConfirmation(
            'Confirmar Desactivación',
            `<div class="alert alert-warning mb-3">
                <i class="fas fa-exclamation-triangle"></i> 
                <strong>Advertencia:</strong> Esta operación escalará todos los recursos a 0 réplicas.
            </div>
            ¿Está seguro de que desea desactivar el namespace <strong>${namespace}</strong>?`,
            'warning'
        );
        
        if (!confirmed) {
            return;
        }
        
        const activateBtn = document.querySelector('button.btn-success');
        const deactivateBtn = document.querySelector('button.btn-warning');
        
        // Disable buttons during operation
        this.setOperationInProgress(true, activateBtn, deactivateBtn);
        
        try {
            // Validate cost center before proceeding
            notificationManager.info('Validando centro de costo...');
            const validationResult = await apiClient.validateCostCenter(costCenter);
            
            if (!validationResult.success) {
                notificationManager.error(`Error al validar centro de costo: ${validationResult.error}`);
                return;
            }
            
            if (!validationResult.data.is_authorized) {
                notificationManager.error(`El centro de costo "${costCenter}" no está autorizado para realizar operaciones`);
                this.markCostCenterInvalid('ns-cost-center');
                return;
            }
            
            // Mark cost center as valid
            this.markCostCenterValid('ns-cost-center');
            
            // Show deactivating message
            notificationManager.info(`Desactivando namespace ${namespace}...`);
            
            // Proceed with deactivation
            const result = await apiClient.deactivateNamespace(namespace, costCenter);
            
            if (result.success) {
                // Show success with animation
                this.showOperationSuccess('deactivate', namespace);
                notificationManager.success(result.data.message || 'Namespace desactivado exitosamente');
                
                // Refresh status immediately
                await this.loadNamespacesStatus();
            } else {
                // Show error with animation
                this.showOperationError('deactivate', namespace, result.error);
                notificationManager.error(`Error al desactivar namespace: ${result.error}`);
            }
        } catch (error) {
            this.showOperationError('deactivate', namespace, error.message);
            notificationManager.error(`Error inesperado: ${error.message}`);
        } finally {
            // Re-enable buttons
            this.setOperationInProgress(false, activateBtn, deactivateBtn);
        }
    }
    
    showConfirmation(title, message, type = 'primary') {
        return new Promise((resolve) => {
            const modal = document.getElementById('confirmationModal');
            const modalTitle = document.getElementById('confirmationModalTitle');
            const modalBody = document.getElementById('confirmationModalBody');
            const confirmBtn = document.getElementById('confirmationModalConfirm');
            
            // Set modal content
            modalTitle.textContent = title;
            modalBody.innerHTML = message;
            
            // Set button style based on type
            confirmBtn.className = `btn btn-${type}`;
            confirmBtn.textContent = type === 'warning' ? 'Sí, desactivar' : 'Confirmar';
            
            // Create Bootstrap modal instance
            const bsModal = new bootstrap.Modal(modal);
            
            // Handle confirm button click
            const handleConfirm = () => {
                bsModal.hide();
                resolve(true);
                cleanup();
            };
            
            // Handle modal close (cancel)
            const handleCancel = () => {
                resolve(false);
                cleanup();
            };
            
            // Cleanup event listeners
            const cleanup = () => {
                confirmBtn.removeEventListener('click', handleConfirm);
                modal.removeEventListener('hidden.bs.modal', handleCancel);
            };
            
            // Add event listeners
            confirmBtn.addEventListener('click', handleConfirm);
            modal.addEventListener('hidden.bs.modal', handleCancel, { once: true });
            
            // Show modal
            bsModal.show();
        });
    }
    
    setOperationInProgress(inProgress, activateBtn, deactivateBtn) {
        if (inProgress) {
            if (activateBtn) {
                activateBtn.disabled = true;
                activateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Procesando...';
            }
            if (deactivateBtn) {
                deactivateBtn.disabled = true;
                deactivateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Procesando...';
            }
        } else {
            if (activateBtn) {
                activateBtn.disabled = false;
                activateBtn.innerHTML = 'Activar';
            }
            if (deactivateBtn) {
                deactivateBtn.disabled = false;
                deactivateBtn.innerHTML = 'Desactivar';
            }
        }
    }
    
    showOperationSuccess(operation, namespace) {
        // Add visual feedback to the namespace in the list
        const listContainer = document.getElementById('namespace-status-list');
        if (listContainer) {
            listContainer.classList.add('operation-success');
            setTimeout(() => {
                listContainer.classList.remove('operation-success');
            }, 2000);
        }
        
        // Store namespace for highlighting after refresh
        this.lastOperationNamespace = namespace;
        this.lastOperationType = 'success';
        
        console.log(`✓ ${operation} operation successful for namespace: ${namespace}`);
    }
    
    showOperationError(operation, namespace, error) {
        // Add visual feedback for error
        const listContainer = document.getElementById('namespace-status-list');
        if (listContainer) {
            listContainer.classList.add('operation-error');
            setTimeout(() => {
                listContainer.classList.remove('operation-error');
            }, 2000);
        }
        
        // Store namespace for highlighting after refresh
        this.lastOperationNamespace = namespace;
        this.lastOperationType = 'error';
        
        console.error(`✗ ${operation} operation failed for namespace: ${namespace}`, error);
    }
    
    markCostCenterValid(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.classList.remove('cost-center-invalid');
            element.classList.add('cost-center-valid');
        }
        
        // Update status icon
        const statusElement = document.getElementById(`${elementId}-status`);
        if (statusElement) {
            statusElement.innerHTML = '<i class="fas fa-check-circle text-success"></i>';
        }
    }
    
    markCostCenterInvalid(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.classList.remove('cost-center-valid');
            element.classList.add('cost-center-invalid');
        }
        
        // Update status icon
        const statusElement = document.getElementById(`${elementId}-status`);
        if (statusElement) {
            statusElement.innerHTML = '<i class="fas fa-times-circle text-danger"></i>';
        }
    }
    
    clearCostCenterValidation(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.classList.remove('cost-center-valid', 'cost-center-invalid');
        }
        
        // Reset status icon
        const statusElement = document.getElementById(`${elementId}-status`);
        if (statusElement) {
            statusElement.innerHTML = '<i class="fas fa-question-circle text-muted"></i>';
        }
    }

    async createTask(task) {
        const result = await apiClient.createTask(task);
        
        if (result.success) {
            const createdTask = result.data;
            this.tasks.push(createdTask);
            this.addTaskToCalendar(createdTask);
            this.saveTasks();
            this.updateDashboard();
            notificationManager.success('Tarea creada exitosamente');
        } else {
            notificationManager.error(`Error al crear la tarea: ${result.error}`);
        }
    }

    async loadTasks() {
        const result = await apiClient.getTasks();
        
        if (result.success) {
            // Clear existing events from calendar
            const existingEvents = this.calendar.getEvents();
            existingEvents.forEach(event => event.remove());
            
            this.tasks = result.data;
            
            // Add tasks to calendar with proper formatting
            this.tasks.forEach(task => {
                this.addTaskToCalendar(task);
            });
            
            this.updateDashboard();
        } else {
            console.error('Error loading tasks:', result.error);
            notificationManager.warning('No se pudieron cargar las tareas del servidor, usando caché local');
            
            // Load from localStorage as fallback
            const savedTasks = localStorage.getItem('tasks');
            if (savedTasks) {
                // Clear existing events
                const existingEvents = this.calendar.getEvents();
                existingEvents.forEach(event => event.remove());
                
                this.tasks = JSON.parse(savedTasks);
                this.tasks.forEach(task => {
                    this.addTaskToCalendar(task);
                });
                this.updateDashboard();
            }
        }
    }
    
    addTaskToCalendar(task) {
        // Format task for FullCalendar
        const calendarEvent = {
            id: task.id,
            title: task.title,
            start: task.start || task.created_at || new Date().toISOString(),
            allDay: task.allDay !== undefined ? task.allDay : false,
            extendedProps: {
                status: task.status || 'pending',
                operation_type: task.operation_type,
                namespace: task.namespace,
                cost_center: task.cost_center,
                schedule: task.schedule,
                command: task.command,
                run_count: task.run_count || 0,
                success_count: task.success_count || 0,
                error_count: task.error_count || 0,
                next_run: task.next_run
            },
            backgroundColor: this.getTaskColor(task.status),
            borderColor: this.getTaskColor(task.status)
        };
        
        this.calendar.addEvent(calendarEvent);
    }
    
    getTaskColor(status) {
        const colors = {
            'pending': '#ffc107',
            'running': '#17a2b8',
            'completed': '#28a745',
            'failed': '#dc3545'
        };
        return colors[status] || '#6c757d';
    }

    saveTasks() {
        localStorage.setItem('tasks', JSON.stringify(this.tasks));
    }

    updateDashboard() {
        const stats = this.calculateStats();
        document.getElementById('active-tasks').textContent = stats.active;
        document.getElementById('completed-tasks').textContent = stats.completed;
        document.getElementById('pending-tasks').textContent = stats.pending;
        document.getElementById('failed-tasks').textContent = stats.failed;
    }

    calculateStats() {
        const today = new Date().toDateString();
        return {
            active: this.tasks.filter(t => t.status === 'running').length,
            completed: this.tasks.filter(t => t.status === 'completed' && 
                new Date(t.start).toDateString() === today).length,
            pending: this.tasks.filter(t => t.status === 'pending').length,
            failed: this.tasks.filter(t => t.status === 'failed').length
        };
    }

    showTaskDetails(task) {
        this.currentTaskId = task.id;
        const operationType = task.operation_type || 'command';
        const commandDisplay = operationType === 'command' ? task.command : `${operationType} namespace: ${task.namespace}`;
        
        // Build execution history section
        let executionHistory = '';
        if (task.execution_history && task.execution_history.length > 0) {
            executionHistory = `
                <hr>
                <h6 class="mt-3 mb-2"><i class="fas fa-history"></i> Historial de Ejecuciones (últimas 10)</h6>
                <div class="table-responsive" style="max-height: 300px; overflow-y: auto;">
                    <table class="table table-sm table-hover">
                        <thead class="table-light sticky-top">
                            <tr>
                                <th>Fecha/Hora</th>
                                <th>Estado</th>
                                <th>Duración</th>
                                <th>Mensaje</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${task.execution_history.slice(0, 10).map(exec => `
                                <tr>
                                    <td><small>${new Date(exec.timestamp).toLocaleString()}</small></td>
                                    <td>
                                        <span class="badge ${exec.status === 'success' ? 'bg-success' : exec.status === 'failed' ? 'bg-danger' : 'bg-warning'}">
                                            ${exec.status}
                                        </span>
                                    </td>
                                    <td><small>${exec.duration ? exec.duration + 's' : 'N/A'}</small></td>
                                    <td><small>${exec.message || 'Sin mensaje'}</small></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        } else {
            executionHistory = `
                <hr>
                <h6 class="mt-3 mb-2"><i class="fas fa-history"></i> Historial de Ejecuciones</h6>
                <p class="text-muted"><em>No hay ejecuciones registradas aún</em></p>
            `;
        }
        
        // Build next execution info
        let nextRunInfo = '';
        if (task.next_run) {
            const nextRunDate = new Date(task.next_run);
            const now = new Date();
            const diffMs = nextRunDate - now;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMins / 60);
            const diffDays = Math.floor(diffHours / 24);
            
            let timeUntil = '';
            if (diffDays > 0) {
                timeUntil = `en ${diffDays} día(s)`;
            } else if (diffHours > 0) {
                timeUntil = `en ${diffHours} hora(s)`;
            } else if (diffMins > 0) {
                timeUntil = `en ${diffMins} minuto(s)`;
            } else if (diffMs > 0) {
                timeUntil = 'muy pronto';
            } else {
                timeUntil = 'pendiente';
            }
            
            nextRunInfo = `
                <p><strong>Próxima Ejecución:</strong> ${nextRunDate.toLocaleString()} <span class="text-muted">(${timeUntil})</span></p>
            `;
        }
        
        const details = `
            <div class="task-details-content">
                <p><strong>Nombre:</strong> ${task.title}</p>
                ${task.description ? `<p><strong>Descripción:</strong> ${task.description}</p>` : ''}
                <p><strong>Tipo:</strong> <span class="badge bg-info">${operationType}</span></p>
                <p><strong>Comando/Operación:</strong> <code class="bg-light p-1 rounded">${commandDisplay}</code></p>
                <p><strong>Programación:</strong> <code class="bg-light p-1 rounded">${task.schedule}</code></p>
                <p><strong>Namespace:</strong> <span class="badge bg-secondary">${task.namespace}</span></p>
                <p><strong>Centro de Costo:</strong> <span class="badge bg-primary">${task.cost_center || 'default'}</span></p>
                <p><strong>Estado:</strong> <span class="status-badge status-${task.status}">${task.status}</span></p>
                <p><strong>Creada:</strong> ${new Date(task.start || task.created_at).toLocaleString()}</p>
                ${nextRunInfo}
                
                <div class="alert alert-info mt-3 mb-0">
                    <strong>Estadísticas:</strong><br>
                    Total de ejecuciones: ${task.run_count || 0} | 
                    Exitosas: <span class="text-success">${task.success_count || 0}</span> | 
                    Fallidas: <span class="text-danger">${task.error_count || 0}</span>
                </div>
                
                ${executionHistory}
            </div>
        `;
        document.getElementById('task-details').innerHTML = details;
        new bootstrap.Modal(document.getElementById('taskModal')).show();
    }

    async deleteTask() {
        if (!this.currentTaskId) return;

        const task = this.tasks.find(t => t.id === this.currentTaskId);
        if (!task) return;
        
        // Show confirmation dialog
        const confirmed = await this.showConfirmation(
            'Confirmar Eliminación',
            `¿Está seguro de que desea eliminar la tarea <strong>${task.title}</strong>?<br><br>
            <small class="text-muted">Esta acción no se puede deshacer.</small>`,
            'danger'
        );
        
        if (!confirmed) {
            return;
        }

        const result = await apiClient.deleteTask(this.currentTaskId);
        
        if (result.success) {
            this.tasks = this.tasks.filter(t => t.id !== this.currentTaskId);
            const event = this.calendar.getEventById(this.currentTaskId);
            if (event) event.remove();
            
            this.saveTasks();
            this.updateDashboard();
            bootstrap.Modal.getInstance(document.getElementById('taskModal')).hide();
            notificationManager.success('Tarea eliminada');
        } else {
            notificationManager.error(`Error al eliminar la tarea: ${result.error}`);
        }
    }
    
    editTask() {
        if (!this.currentTaskId) return;
        
        const task = this.tasks.find(t => t.id === this.currentTaskId);
        if (!task) return;
        
        // Populate edit form
        document.getElementById('edit-task-id').value = task.id;
        document.getElementById('edit-task-name').value = task.title;
        document.getElementById('edit-task-description').value = task.description || '';
        document.getElementById('edit-task-type').value = task.operation_type || 'activate';
        document.getElementById('edit-task-namespace').value = task.namespace;
        document.getElementById('edit-task-schedule').value = task.schedule;
        document.getElementById('edit-task-cost-center').value = task.cost_center;
        
        if (task.operation_type === 'command' && task.command) {
            document.getElementById('edit-task-command').value = task.command;
        }
        
        // Populate namespace select in edit form
        const editNamespaceSelect = document.getElementById('edit-task-namespace');
        editNamespaceSelect.innerHTML = '';
        this.namespaces.forEach(namespace => {
            const option = document.createElement('option');
            option.value = namespace;
            option.textContent = namespace;
            if (namespace === task.namespace) {
                option.selected = true;
            }
            editNamespaceSelect.appendChild(option);
        });
        
        // Toggle command field visibility
        toggleEditTaskFields();
        
        // Hide details modal and show edit modal
        bootstrap.Modal.getInstance(document.getElementById('taskModal')).hide();
        const editModal = new bootstrap.Modal(document.getElementById('taskEditModal'));
        editModal.show();
    }
    
    async saveTaskEdit() {
        const taskId = document.getElementById('edit-task-id').value;
        const task = this.tasks.find(t => t.id === taskId);
        
        if (!task) {
            notificationManager.error('Tarea no encontrada');
            return;
        }
        
        // Get updated values
        const updatedTask = {
            ...task,
            title: document.getElementById('edit-task-name').value,
            description: document.getElementById('edit-task-description').value,
            operation_type: document.getElementById('edit-task-type').value,
            namespace: document.getElementById('edit-task-namespace').value,
            schedule: document.getElementById('edit-task-schedule').value,
            cost_center: document.getElementById('edit-task-cost-center').value
        };
        
        if (updatedTask.operation_type === 'command') {
            updatedTask.command = document.getElementById('edit-task-command').value;
        }
        
        // Update task via API
        const result = await apiClient.updateTask(taskId, updatedTask);
        
        if (result.success) {
            // Update local task
            const index = this.tasks.findIndex(t => t.id === taskId);
            if (index !== -1) {
                this.tasks[index] = { ...this.tasks[index], ...updatedTask };
            }
            
            // Update calendar event
            const event = this.calendar.getEventById(taskId);
            if (event) {
                event.remove();
                this.addTaskToCalendar(this.tasks[index]);
            }
            
            this.saveTasks();
            this.updateDashboard();
            
            // Hide edit modal
            bootstrap.Modal.getInstance(document.getElementById('taskEditModal')).hide();
            
            notificationManager.success('Tarea actualizada exitosamente');
        } else {
            notificationManager.error(`Error al actualizar la tarea: ${result.error}`);
        }
    }

    async refreshLogs() {
        const result = await apiClient.getLogs({ limit: 50 });
        
        if (result.success) {
            const logs = result.data.logs || result.data;
            this.displayLogs(logs);
        } else {
            console.error('Error loading logs:', result.error);
            notificationManager.error('Error al cargar los logs');
            this.displayLogs([{
                timestamp: new Date().toISOString(),
                level: 'error',
                message: `Error al cargar los logs: ${result.error}`
            }]);
        }
    }

    displayLogs(logs) {
        const container = document.getElementById('logs-container');
        
        if (!logs || logs.length === 0) {
            container.innerHTML = '<div class="text-muted">No hay logs disponibles</div>';
            return;
        }
        
        container.innerHTML = logs.map(log => {
            const timestamp = log.timestamp ? new Date(log.timestamp).toLocaleString() : 'N/A';
            const level = log.level || 'info';
            const message = log.message || JSON.stringify(log);
            
            return `
                <div class="log-entry">
                    <span class="log-timestamp">[${timestamp}]</span>
                    <span class="log-level-${level.toLowerCase()}">[${level.toUpperCase()}]</span>
                    ${message}
                </div>
            `;
        }).join('');
        container.scrollTop = container.scrollHeight;
    }

    showNotification(message, type) {
        // Use new notification manager
        if (type === 'error') {
            notificationManager.error(message);
        } else if (type === 'success') {
            notificationManager.success(message);
        } else if (type === 'warning') {
            notificationManager.warning(message);
        } else {
            notificationManager.info(message);
        }
    }

    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
}

// Navigation functions
function showDashboard() {
    hideAllSections();
    document.getElementById('dashboard-section').style.display = 'block';
    taskScheduler.updateDashboard();
}

function showScheduler() {
    hideAllSections();
    document.getElementById('scheduler-section').style.display = 'block';
    taskScheduler.calendar.render();
    // Reload namespaces and status when showing scheduler
    taskScheduler.loadNamespaces();
    taskScheduler.loadNamespacesStatus();
}

function showLogs() {
    hideAllSections();
    document.getElementById('logs-section').style.display = 'block';
    taskScheduler.refreshLogs();
}

function hideAllSections() {
    document.querySelectorAll('.section').forEach(section => {
        section.style.display = 'none';
    });
}

function deleteTask() {
    taskScheduler.deleteTask();
}

function editTask() {
    taskScheduler.editTask();
}

function saveTaskEdit() {
    taskScheduler.saveTaskEdit();
}

function toggleEditTaskFields() {
    const taskType = document.getElementById('edit-task-type').value;
    const commandField = document.getElementById('edit-command-field');
    const commandInput = document.getElementById('edit-task-command');
    
    if (taskType === 'command') {
        commandField.style.display = 'block';
        commandInput.required = true;
    } else {
        commandField.style.display = 'none';
        commandInput.required = false;
        commandInput.value = '';
    }
}

function refreshLogs() {
    taskScheduler.refreshLogs();
}

function toggleTaskFields() {
    const taskType = document.getElementById('task-type').value;
    const commandField = document.getElementById('command-field');
    const commandInput = document.getElementById('task-command');
    
    if (taskType === 'command') {
        commandField.style.display = 'block';
        commandInput.required = true;
    } else {
        commandField.style.display = 'none';
        commandInput.required = false;
        commandInput.value = '';
    }
}

function activateNamespace() {
    taskScheduler.activateNamespace();
}

function deactivateNamespace() {
    taskScheduler.deactivateNamespace();
}

// Initialize the application
let taskScheduler;
document.addEventListener('DOMContentLoaded', function() {
    taskScheduler = new TaskScheduler();
});