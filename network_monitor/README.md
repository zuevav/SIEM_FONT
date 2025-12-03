# SIEM Network Monitor

Мониторинг сетевого оборудования (принтеры, коммутаторы, роутеры, МСЭ, UPS) для SIEM системы.

## 🎯 Возможности

### SNMP Мониторинг
- **Принтеры** (HP, Canon, Xerox, Brother)
  - Статус принтера
  - Уровень тонера/чернил
  - Счетчик страниц
  - Состояние лотков
  - Обнаружение ошибок

- **Коммутаторы** (Cisco, HP, D-Link, Juniper)
  - CPU и Memory usage
  - Состояние портов (up/down)
  - Трафик и ошибки интерфейсов
  - Статистика по портам

- **Роутеры**
  - Таблица маршрутизации
  - BGP peers status
  - CPU и Memory usage
  - Интерфейсы и трафик

- **Межсетевые экраны** (Fortinet, Checkpoint, Palo Alto)
  - Активные соединения
  - Заблокированные пакеты
  - VPN туннели
  - CPU и Memory

- **UPS** (APC, Eaton, CyberPower)
  - Статус батареи
  - Заряд батареи (%)
  - Время работы от батареи
  - Нагрузка (%)
  - Входное/выходное напряжение

### Syslog Receiver
- Прием syslog (UDP/TCP на порту 514)
- Поддержка RFC 3164 и RFC 5424
- Парсинг vendor-specific форматов (Cisco, Fortinet, Juniper)
- Фильтрация по источникам

### Детектирование аномалий
- Высокий CPU/Memory usage
- Низкий уровень тонера в принтере
- Низкий заряд батареи UPS
- Ошибки на интерфейсах
- Отказ устройства (unreachable)

---

## 📋 Требования

### Системные требования
- **ОС**: Linux (Ubuntu 20.04+, CentOS 8+, Debian 11+)
- **Python**: 3.11 или новее
- **RAM**: Минимум 256 MB
- **CPU**: 1 core (рекомендуется 2+)
- **Диск**: 100 MB свободного места

### Сетевые требования
- Доступ к сетевым устройствам по SNMP (UDP 161)
- Возможность приема syslog (UDP/TCP 514)
- Доступ к SIEM API по HTTP/HTTPS
- Bandwidth: ~100 KB/час на устройство

---

## 🚀 Быстрый старт

### 1. Установка

```bash
# Клонировать репозиторий (если еще не сделано)
cd SIEM_FONT/network_monitor

# Создать виртуальное окружение
python3.11 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Скопировать пример конфигурации
cp config.yaml.example config.yaml
```

### 2. Настройка

```bash
# Отредактировать config.yaml
nano config.yaml
```

**Минимальная конфигурация:**
```yaml
siem:
  server_url: "http://your-siem-server:8000"
  api_key: "your-api-key-here"

snmp:
  enabled: true
  community: "public"  # SNMP community string

  devices:
    - name: "HP-Printer-01"
      ip: "192.168.1.100"
      type: "printer"
      enabled: true

    - name: "Switch-Core"
      ip: "192.168.1.10"
      type: "switch"
      enabled: true

syslog:
  enabled: true
  listeners:
    - protocol: "udp"
      port: 514
      bind: "0.0.0.0"
```

### 3. Запуск

```bash
# В консольном режиме (для тестирования)
python main.py

# Или как systemd service (см. раздел "Установка как службы")
```

---

## 🔧 Конфигурация

### Добавление устройств

#### Принтер
```yaml
snmp:
  devices:
    - name: "HP-LaserJet-Office"
      ip: "192.168.1.100"
      type: "printer"
      enabled: true
      community: "public"
```

#### Коммутатор
```yaml
    - name: "Cisco-3750-Core"
      ip: "192.168.1.10"
      type: "switch"
      enabled: true
      community: "private"
      monitor:
        - interfaces
        - cpu
        - memory
        - errors
```

#### Роутер
```yaml
    - name: "Router-Main"
      ip: "192.168.1.1"
      type: "router"
      enabled: true
      monitor:
        - interfaces
        - routing_table
        - cpu
        - memory
```

#### МСЭ (Firewall)
```yaml
    - name: "Fortinet-FG100"
      ip: "192.168.1.254"
      type: "firewall"
      enabled: true
      monitor:
        - connections
        - blocked_packets
        - vpn_tunnels
```

#### UPS
```yaml
    - name: "APC-SmartUPS-1500"
      ip: "192.168.1.200"
      type: "ups"
      enabled: true
      monitor:
        - battery_status
        - load_percent
        - voltage
```

### Настройка порогов аномалий

```yaml
snmp:
  anomaly_detection:
    enabled: true
    cpu_threshold: 80              # % CPU
    memory_threshold: 85           # % Memory
    interface_errors_threshold: 100  # ошибок в минуту
    toner_low_threshold: 20        # % тонера
    battery_low_threshold: 30      # % заряда батареи
```

### Syslog настройка

```yaml
syslog:
  enabled: true

  listeners:
    # UDP (рекомендуется для большинства устройств)
    - protocol: "udp"
      port: 514
      bind: "0.0.0.0"

    # TCP (для критичных логов)
    - protocol: "tcp"
      port: 514
      bind: "0.0.0.0"

  # Фильтр по IP
  sources:
    use_snmp_devices: true  # Принимать от всех SNMP устройств
    allowed_ips:
      - "192.168.1.0/24"
    blocked_ips: []
```

### SNMP v3 (повышенная безопасность)

```yaml
snmp:
  version: "3"
  v3:
    username: "snmpuser"
    auth_protocol: "SHA"
    auth_password: "authpassword"
    priv_protocol: "AES"
    priv_password: "privpassword"
```

---

## 📊 Установка как службы

### Systemd Service

```bash
# Создать systemd service файл
sudo nano /etc/systemd/system/siem-network-monitor.service
```

Содержимое:
```ini
[Unit]
Description=SIEM Network Monitor
After=network.target

[Service]
Type=simple
User=siem
Group=siem
WorkingDirectory=/opt/siem/network_monitor
ExecStart=/opt/siem/network_monitor/venv/bin/python main.py
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

```bash
# Создать пользователя
sudo useradd -r -s /bin/false siem

# Установить права
sudo chown -R siem:siem /opt/siem/network_monitor

# Reload systemd
sudo systemctl daemon-reload

# Включить автозапуск
sudo systemctl enable siem-network-monitor

# Запустить службу
sudo systemctl start siem-network-monitor

# Проверить статус
sudo systemctl status siem-network-monitor
```

---

## 📝 Логи

### Просмотр логов службы

```bash
# Real-time логи
sudo journalctl -u siem-network-monitor -f

# Последние 100 строк
sudo journalctl -u siem-network-monitor -n 100

# Логи за сегодня
sudo journalctl -u siem-network-monitor --since today

# Логи с фильтром
sudo journalctl -u siem-network-monitor | grep ERROR
```

### Файловые логи

```bash
# Основной лог
tail -f /var/log/siem/network_monitor.log

# С фильтром
grep "anomaly" /var/log/siem/network_monitor.log
```

---

## 🔍 Мониторинг

### Статистика

В логах каждые 5 минут выводится статистика:

```
Network Monitor Statistics
Event Queue: 12/10000
SNMP Devices: 5 monitored
  - HP-Printer-01: HP LaserJet Pro (polled 45ms ago)
  - Switch-Core: Cisco 3750 (polled 123ms ago)
Syslog: 1523 received, 1520 parsed, 3 dropped
```

### Проверка связи с SIEM

```bash
# Проверить доступность SIEM API
curl http://your-siem-server:8000/api/v1/health

# Проверить heartbeat
journalctl -u siem-network-monitor | grep "heartbeat"
```

---

## 🐛 Troubleshooting

### Network Monitor не запускается

**Проблема**: Служба падает сразу после запуска

**Решение**:
1. Проверьте логи: `journalctl -u siem-network-monitor -n 50`
2. Проверьте config.yaml на ошибки
3. Убедитесь, что Python 3.11+ установлен
4. Проверьте права доступа к файлам

### SNMP не работает

**Проблема**: Нет данных от SNMP устройств

**Решение**:
1. Проверьте доступность устройства:
   ```bash
   ping 192.168.1.100
   ```

2. Проверьте SNMP вручную:
   ```bash
   snmpwalk -v2c -c public 192.168.1.100 system
   ```

3. Убедитесь, что SNMP включен на устройстве
4. Проверьте community string в config.yaml
5. Проверьте firewall

### Syslog не принимается

**Проблема**: Сообщения syslog не приходят

**Решение**:
1. Проверьте, что служба слушает порт:
   ```bash
   sudo netstat -ulnp | grep 514
   ```

2. Проверьте firewall:
   ```bash
   sudo ufw allow 514/udp
   sudo ufw allow 514/tcp
   ```

3. Настройте устройство для отправки syslog:
   - Cisco: `logging host 192.168.1.5`
   - Fortinet: `config log syslogd setting`

4. Проверьте источник в config.yaml (allowed_ips)

### События не отправляются в SIEM

**Проблема**: Network Monitor работает, но события не попадают в SIEM

**Решение**:
1. Проверьте API key в config.yaml
2. Проверьте доступность SIEM API
3. Проверьте очередь событий в логах
4. Проверьте retry attempts в конфигурации

---

## 🔒 Безопасность

### SNMP Security

- **Используйте SNMP v3** вместо v2c для критичных устройств
- **Измените community string** с "public" на уникальный
- **Ограничьте доступ** по IP на устройствах (SNMP ACL)
- **Используйте RO community**, а не RW

### Syslog Security

- **Фильтруйте источники** через allowed_ips
- **Используйте TLS** для syslog (RFC 5425) если возможно
- **Не открывайте порт 514** в Internet

### Network Monitor Security

- **Храните API key безопасно** (chmod 600 config.yaml)
- **Используйте HTTPS** для SIEM API в продакшене
- **Запускайте от отдельного пользователя** (не root)

---

## 📚 Поддерживаемые устройства

### Принтеры
- HP LaserJet, OfficeJet, PageWide
- Canon imageCLASS, PIXMA
- Xerox WorkCentre, Phaser
- Brother MFC, DCP
- Epson WorkForce, EcoTank

### Коммутаторы
- Cisco Catalyst, Nexus
- HP ProCurve, Aruba
- Juniper EX Series
- D-Link DGS, DES
- Mikrotik

### Роутеры
- Cisco ISR, ASR
- Juniper MX, SRX
- Mikrotik RouterOS
- Ubiquiti EdgeRouter

### Межсетевые экраны
- Fortinet FortiGate
- Checkpoint
- Palo Alto Networks
- pfSense, OPNsense
- Cisco ASA, Firepower

### UPS
- APC Smart-UPS, Back-UPS
- Eaton 5P, 9PX
- CyberPower OR, PR
- Tripp Lite SmartPro

---

## 🤝 Поддержка

При возникновении проблем:

1. Проверьте логи Network Monitor
2. Проверьте конфигурацию устройств
3. Проверьте сетевую доступность
4. Обратитесь к документации устройств

---

**Версия**: 1.0.0
**Последнее обновление**: 2025-12-02
