/**
 * Основные JavaScript функции для приложения Backup Google Sheets
 */

// Глобальный объект приложения
const App = {
    // Инициализация приложения
    init: function() {
        // Обработчики для общих элементов интерфейса
        this.setupUIHandlers();
        
        // Отображение/скрытие прелоадера
        this.showSpinner(false);
    },
    
    // Настройка обработчиков событий для общих UI элементов
    setupUIHandlers: function() {
        // Обработчик для всех кнопок, требующих подтверждения
        document.querySelectorAll('[data-confirm]').forEach(btn => {
            btn.addEventListener('click', function(e) {
                if (!confirm(this.dataset.confirm)) {
                    e.preventDefault();
                    return false;
                }
            });
        });
    },
    
    // Показать/скрыть индикатор загрузки
    showSpinner: function(show = true) {
        let spinner = document.querySelector('.spinner-overlay');
        
        // Если спиннер не существует, создаем его
        if (!spinner && show) {
            spinner = document.createElement('div');
            spinner.className = 'spinner-overlay';
            spinner.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Загрузка...</span></div>';
            document.body.appendChild(spinner);
        }
        
        // Показываем или скрываем спиннер
        if (spinner) {
            spinner.style.display = show ? 'flex' : 'none';
        }
    },
    
    // Обработка HTTP ошибок
    handleApiError: function(error, defaultMessage = 'Произошла ошибка при выполнении запроса') {
        console.error('API Error:', error);
        
        // Пытаемся получить сообщение об ошибке из ответа
        if (error.response && error.response.json) {
            error.response.json().then(data => {
                alert(data.detail || defaultMessage);
            }).catch(() => {
                alert(defaultMessage);
            });
        } else {
            alert(defaultMessage);
        }
    },
    
    // Форматирование даты и времени
    formatDateTime: function(dateString) {
        if (!dateString) return 'Н/Д';
        
        const date = new Date(dateString);
        return date.toLocaleString('ru-RU', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },
    
    // Форматирование размера файла
    formatFileSize: function(bytes) {
        if (bytes === 0 || bytes === null || bytes === undefined) return '0 Б';
        
        const k = 1024;
        const sizes = ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
};

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    App.init();
}); 