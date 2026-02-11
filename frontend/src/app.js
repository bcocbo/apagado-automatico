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
        }, 30000);
    }

    initCalendar() {
        const calendarEl = document.getElementById('calendar');
        this.calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay'
            },
            editable: true,
            selectable: true,
            selectMirror: true,
            dayMaxEvents: true,
            weekends: true,
            select: this.handleDateSelect.bind(this),
            eventClick: this.handleEventClick.bind(this),
            eventsSet: this.handleEvents.bind(this),
            eventClassNames: function(arg) {
                return ['task-' + arg.event.extendedProps.status];
            }
        });
        this.calendar.render();
    }

    bindEvents() {
        document.getElementById('task-form').addEventListener('submit', this.handleTaskSubmit.bind(this));
    }

    handleDateSelect(selectInfo) {
        const title = prompt('Nombre de la nueva tarea:');
        const calendarApi = selectInfo.view.calendar;

        calendarApi.unselect();

        if (title) {
            const task = {
                id: this.generateId(),
                title: title,
                start: selectInfo.startStr,
                end: selectInfo.endStr,
                allDay: selectInfo.allDay,
                status: 'pending',
                command: '',
                schedule: '',
                namespace: 'default'
            };

            calendarApi.addEvent(task);
            this.tasks.push(task);
            this.saveTasks();
            this.updateDashboard();
        }
    }

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
        const task = {
            id: this.generateId(),
            title: document.getElementById('task-name').value,
            schedule: document.getElementById('task-schedule').value,
            namespace: document.getElementById('task-namespace').value,
            cost_center: document.getElementById('task-cost-center').value,
            operation_type: taskType,
            status: 'pending',
            start: new Date().toISOString(),
            allDay: false
        };

        // Add command only for command type tasks
        if (taskType === 'command') {
            task.command = document.getElementById('task-command').value;
        }

        this.createTask(task);
        document.getElementById('task-form').reset();
    }

    async loadNamespaces() {
        try {
            const response = await fetch('/api/namespaces');
            if (response.ok) {
                this.namespaces = await response.json();
                this.populateNamespaceSelects();
            }
        } catch (error) {
            console.error('Error loading namespaces:', error);
        }
    }

    async loadNamespacesStatus() {
        try {
            const response = await fetch('/api/namespaces/status');
            if (response.ok) {
                const data = await response.json();
                this.namespacesStatus = data;
                this.updateNamespaceStatus();
            }
        } catch (error) {
            console.error('Error loading namespace status:', error);
        }
    }

    populateNamespaceSelects() {
        const selects = ['task-namespace', 'ns-select'];
        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            if (select) {
                // Clear existing options except first one
                while (select.children.length > 1) {
                    select.removeChild(select.lastChild);
                }
                
                this.namespaces.forEach(namespace => {
                    if (namespace !== 'default') {  // default is already there
                        const option = document.createElement('option');
                        option.value = namespace;
                        option.textContent = namespace;
                        select.appendChild(option);
                    }
                });
            }
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
    }

    async activateNamespace() {
        const namespace = document.getElementById('ns-select').value;
        const costCenter = document.getElementById('ns-cost-center').value;
        
        if (!namespace) {
            this.showNotification('Por favor selecciona un namespace', 'error');
            return;
        }
        
        try {
            const response = await fetch(`/api/namespaces/${namespace}/activate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    cost_center: costCenter,
                    user_id: 'web-user'
                })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showNotification(result.message, 'success');
                this.loadNamespacesStatus();
            } else {
                this.showNotification(result.error, 'error');
            }
        } catch (error) {
            console.error('Error activating namespace:', error);
            this.showNotification('Error al activar namespace', 'error');
        }
    }

    async deactivateNamespace() {
        const namespace = document.getElementById('ns-select').value;
        const costCenter = document.getElementById('ns-cost-center').value;
        
        if (!namespace) {
            this.showNotification('Por favor selecciona un namespace', 'error');
            return;
        }
        
        try {
            const response = await fetch(`/api/namespaces/${namespace}/deactivate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    cost_center: costCenter,
                    user_id: 'web-user'
                })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showNotification(result.message, 'success');
                this.loadNamespacesStatus();
            } else {
                this.showNotification(result.error, 'error');
            }
        } catch (error) {
            console.error('Error deactivating namespace:', error);
            this.showNotification('Error al desactivar namespace', 'error');
        }
    }

    async createTask(task) {
        try {
            const response = await fetch('/api/tasks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(task)
            });

            if (response.ok) {
                const createdTask = await response.json();
                this.tasks.push(createdTask);
                this.calendar.addEvent(createdTask);
                this.saveTasks();
                this.updateDashboard();
                this.showNotification('Tarea creada exitosamente', 'success');
            } else {
                throw new Error('Error al crear la tarea');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showNotification('Error al crear la tarea', 'error');
        }
    }

    async loadTasks() {
        try {
            const response = await fetch('/api/tasks');
            if (response.ok) {
                this.tasks = await response.json();
                this.tasks.forEach(task => {
                    this.calendar.addEvent(task);
                });
                this.updateDashboard();
            }
        } catch (error) {
            console.error('Error loading tasks:', error);
            // Load from localStorage as fallback
            const savedTasks = localStorage.getItem('tasks');
            if (savedTasks) {
                this.tasks = JSON.parse(savedTasks);
                this.tasks.forEach(task => {
                    this.calendar.addEvent(task);
                });
                this.updateDashboard();
            }
        }
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
        
        const details = `
            <p><strong>Nombre:</strong> ${task.title}</p>
            <p><strong>Tipo:</strong> ${operationType}</p>
            <p><strong>Comando/Operación:</strong> <code>${commandDisplay}</code></p>
            <p><strong>Programación:</strong> ${task.schedule}</p>
            <p><strong>Namespace:</strong> ${task.namespace}</p>
            <p><strong>Centro de Costo:</strong> ${task.cost_center || 'default'}</p>
            <p><strong>Estado:</strong> <span class="status-badge status-${task.status}">${task.status}</span></p>
            <p><strong>Fecha:</strong> ${new Date(task.start).toLocaleString()}</p>
            <p><strong>Ejecuciones:</strong> ${task.run_count || 0} (${task.success_count || 0} exitosas, ${task.error_count || 0} fallidas)</p>
        `;
        document.getElementById('task-details').innerHTML = details;
        new bootstrap.Modal(document.getElementById('taskModal')).show();
    }

    async deleteTask() {
        if (!this.currentTaskId) return;

        try {
            const response = await fetch(`/api/tasks/${this.currentTaskId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.tasks = this.tasks.filter(t => t.id !== this.currentTaskId);
                const event = this.calendar.getEventById(this.currentTaskId);
                if (event) event.remove();
                
                this.saveTasks();
                this.updateDashboard();
                bootstrap.Modal.getInstance(document.getElementById('taskModal')).hide();
                this.showNotification('Tarea eliminada', 'success');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showNotification('Error al eliminar la tarea', 'error');
        }
    }

    async refreshLogs() {
        try {
            const response = await fetch('/api/logs');
            if (response.ok) {
                const logs = await response.json();
                this.displayLogs(logs);
            }
        } catch (error) {
            console.error('Error loading logs:', error);
            this.displayLogs([{
                timestamp: new Date().toISOString(),
                level: 'error',
                message: 'Error al cargar los logs'
            }]);
        }
    }

    displayLogs(logs) {
        const container = document.getElementById('logs-container');
        container.innerHTML = logs.map(log => `
            <div class="log-entry">
                <span class="log-timestamp">[${new Date(log.timestamp).toLocaleString()}]</span>
                <span class="log-level-${log.level}">[${log.level.toUpperCase()}]</span>
                ${log.message}
            </div>
        `).join('');
        container.scrollTop = container.scrollHeight;
    }

    showNotification(message, type) {
        // Simple notification system
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : 'success'} position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999;';
        notification.textContent = message;
        
        document.body.appendChild(notification);
        setTimeout(() => {
            notification.remove();
        }, 3000);
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