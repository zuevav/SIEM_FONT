import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import duration from 'dayjs/plugin/duration'
import 'dayjs/locale/ru'

dayjs.extend(relativeTime)
dayjs.extend(duration)
dayjs.locale('ru')

// ============================================================================
// Date/Time Formatters
// ============================================================================

export function formatDateTime(date: string | Date): string {
  return dayjs(date).format('DD.MM.YYYY HH:mm:ss')
}

export function formatDate(date: string | Date): string {
  return dayjs(date).format('DD.MM.YYYY')
}

export function formatTime(date: string | Date): string {
  return dayjs(date).format('HH:mm:ss')
}

export function formatRelativeTime(date: string | Date): string {
  return dayjs(date).fromNow()
}

export function formatDuration(seconds: number): string {
  const d = dayjs.duration(seconds, 'seconds')
  const hours = Math.floor(d.asHours())
  const minutes = d.minutes()
  const secs = d.seconds()

  if (hours > 0) {
    return `${hours}ч ${minutes}м`
  } else if (minutes > 0) {
    return `${minutes}м ${secs}с`
  } else {
    return `${secs}с`
  }
}

// ============================================================================
// Number Formatters
// ============================================================================

export function formatNumber(num: number): string {
  return new Intl.NumberFormat('ru-RU').format(num)
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes'

  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

export function formatPercent(value: number, total: number): string {
  if (total === 0) return '0%'
  return `${Math.round((value / total) * 100)}%`
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
  }).format(amount)
}

// ============================================================================
// Severity Formatters
// ============================================================================

export function getSeverityText(severity: number): string {
  const severityMap: Record<number, string> = {
    0: 'Инфо',
    1: 'Низкий',
    2: 'Средний',
    3: 'Высокий',
    4: 'Критический',
  }
  return severityMap[severity] || 'Неизвестно'
}

export function getSeverityColor(severity: number): string {
  const colorMap: Record<number, string> = {
    0: 'default',
    1: 'blue',
    2: 'gold',
    3: 'orange',
    4: 'red',
  }
  return colorMap[severity] || 'default'
}

export function getPriorityText(priority: number): string {
  const priorityMap: Record<number, string> = {
    1: 'Низкий',
    2: 'Средний',
    3: 'Высокий',
    4: 'Критический',
  }
  return priorityMap[priority] || 'Неизвестно'
}

export function getPriorityColor(priority: number): string {
  return getSeverityColor(priority)
}

// ============================================================================
// Status Formatters
// ============================================================================

export function getStatusText(status: string): string {
  const statusMap: Record<string, string> = {
    // Alerts
    new: 'Новый',
    acknowledged: 'Подтверждён',
    in_progress: 'В работе',
    investigating: 'Расследуется',
    resolved: 'Решён',
    false_positive: 'Ложный',

    // Incidents
    open: 'Открыт',
    contained: 'Локализован',
    remediated: 'Устранён',
    closed: 'Закрыт',

    // Agents
    online: 'Онлайн',
    offline: 'Оффлайн',
    error: 'Ошибка',
  }
  return statusMap[status] || status
}

export function getStatusColor(status: string): string {
  const colorMap: Record<string, string> = {
    // Alerts
    new: 'red',
    acknowledged: 'blue',
    in_progress: 'processing',
    investigating: 'processing',
    resolved: 'success',
    false_positive: 'default',

    // Incidents
    open: 'red',
    contained: 'orange',
    remediated: 'processing',
    closed: 'success',

    // Agents
    online: 'success',
    offline: 'default',
    error: 'error',
  }
  return colorMap[status] || 'default'
}

// ============================================================================
// Event Code Formatters
// ============================================================================

export function getEventCodeDescription(code: number): string {
  const descriptions: Record<number, string> = {
    // Windows Security Event IDs
    4624: 'Успешный вход',
    4625: 'Неудачный вход',
    4634: 'Выход пользователя',
    4648: 'Вход с явными учётными данными',
    4672: 'Назначены специальные привилегии',
    4688: 'Создан новый процесс',
    4720: 'Создана учётная запись пользователя',
    4722: 'Учётная запись пользователя включена',
    4723: 'Попытка изменения пароля',
    4724: 'Попытка сброса пароля',
    4725: 'Учётная запись пользователя отключена',
    4726: 'Учётная запись пользователя удалена',
    4732: 'Участник добавлен в группу безопасности',
    4733: 'Участник удалён из группы безопасности',
    4738: 'Изменена учётная запись пользователя',
    4740: 'Учётная запись заблокирована',
    4767: 'Учётная запись разблокирована',
    4776: 'Попытка аутентификации NTLM',
    4798: 'Запрошена локальная группа пользователя',
    4799: 'Локальная группа была перечислена',

    // Sysmon Event IDs
    1: 'Создание процесса',
    2: 'Изменение времени создания файла',
    3: 'Сетевое подключение',
    5: 'Завершение процесса',
    7: 'Загрузка образа',
    8: 'Создание удалённого потока',
    10: 'Доступ к процессу',
    11: 'Создание файла',
    12: 'Создание или удаление объекта реестра',
    13: 'Установка значения реестра',
    15: 'Создание альтернативного потока данных',
    22: 'DNS запрос',
    23: 'Удаление файла',

    // Windows System Event IDs
    7045: 'Установлена новая служба',
    7040: 'Изменён тип запуска службы',
    7036: 'Служба вошла в состояние',
  }

  return descriptions[code] || `Event ${code}`
}

// ============================================================================
// IP Address Formatters
// ============================================================================

export function isPrivateIP(ip: string): boolean {
  if (!ip) return false

  const parts = ip.split('.').map(Number)
  if (parts.length !== 4) return false

  // 10.0.0.0 - 10.255.255.255
  if (parts[0] === 10) return true

  // 172.16.0.0 - 172.31.255.255
  if (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31) return true

  // 192.168.0.0 - 192.168.255.255
  if (parts[0] === 192 && parts[1] === 168) return true

  // 127.0.0.0 - 127.255.255.255 (loopback)
  if (parts[0] === 127) return true

  return false
}

export function formatIP(ip?: string): string {
  if (!ip) return '-'
  return ip
}

// ============================================================================
// MITRE ATT&CK Formatters
// ============================================================================

export function getMitreTacticName(tactic: string): string {
  const tactics: Record<string, string> = {
    'Initial Access': 'Первоначальный доступ',
    'Execution': 'Выполнение',
    'Persistence': 'Закрепление',
    'Privilege Escalation': 'Повышение привилегий',
    'Defense Evasion': 'Обход защиты',
    'Credential Access': 'Доступ к учётным данным',
    'Discovery': 'Обнаружение',
    'Lateral Movement': 'Горизонтальное перемещение',
    'Collection': 'Сбор данных',
    'Command and Control': 'Управление и контроль',
    'Exfiltration': 'Эксфильтрация',
    'Impact': 'Воздействие',
  }
  return tactics[tactic] || tactic
}

export function formatMitreTechnique(technique: string): string {
  if (!technique) return '-'
  return technique
}

// ============================================================================
// Text Truncation
// ============================================================================

export function truncate(text: string, maxLength: number): string {
  if (!text || text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

export function truncateMiddle(text: string, maxLength: number, separator: string = '...'): string {
  if (!text || text.length <= maxLength) return text

  const sepLen = separator.length
  const charsToShow = maxLength - sepLen
  const frontChars = Math.ceil(charsToShow / 2)
  const backChars = Math.floor(charsToShow / 2)

  return text.substring(0, frontChars) + separator + text.substring(text.length - backChars)
}
