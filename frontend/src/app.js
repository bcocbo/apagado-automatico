// Task Scheduler Application
class TaskScheduler {
    constructor() {
        this.calendar = null;
        this.tasks = [];
        this.currentTaskId = null;
        this.init();
    }

    init() {
        this.initCalendar();
        this.bindEvents();
        this.loadTasks();
        this.updateDashboard();
        this.showDashboard();
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
        
        const task = {
            id: this.generateId(),
            title: document.getElementById('task-name').value,
            command: document.getElementById('task-command').value,
            schedule: document.getElementById('task-schedule').value,
            namespace: document.getElementById('task-namespace').value,
            status: 'pending',
            start: new Date().toISOString(),
            allDay: false
        };

        this.createTask(task);
        document.getElementById('task-form').reset();
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
        const details = `
            <p><strong>Nombre:</strong> ${task.title}</p>
            <p><strong>Comando:</strong> <code>${task.command}</code></p>
            <p><strong>Programación:</strong> ${task.schedule}</p>
            <p><strong>Namespace:</strong> ${task.namespace}</p>
            <p><strong>Estado:</strong> <span class="status-badge status-${task.status}">${task.status}</span></p>
            <p><strong>Fecha:</strong> ${new Date(task.start).toLocaleString()}</p>
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

// Initialize the application
let taskScheduler;
document.addEventListener('DOMContentLoaded', function() {
    taskScheduler = new TaskScheduler();
});