# Деплой на сервер

Открытый доступ (без логина/пароля), приватный только код — репозиторий не
публикуется, на сервер код доставляется напрямую.

Сервер уже занят под AmneziaVPN — сначала проверяем, что порты 80/443
свободны, чтобы не столкнуться с протоколами VPN, которые тоже иногда
маскируются под HTTPS-трафик на 443:

```bash
sudo ss -tulnp | grep -E ':80 |:443 '
```

Если 443 занят каким-то из процессов Amnezia — используйте другой порт для
сайта (например 8443) и указывайте его в ссылке.

## 1. Установить Docker и nginx

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx
```

## 2. Скопировать код на сервер

Репозиторий приватный, поэтому пуш на сервер — напрямую с локальной машины
(без публикации в GitHub):

```bash
rsync -av --exclude='.git' --exclude='__pycache__' --exclude='.pytest_cache' \
  --exclude='*.xlsx' --exclude='*.xls' \
  "c:\Users\Platon\PycharmProjects\crypto-codes-suppuration/" \
  user@SERVER_IP:/opt/crypto-codes/
```

(Дальнейшие обновления — та же команда повторно.)

## 3. Запустить приложение в Docker

```bash
ssh user@SERVER_IP
cd /opt/crypto-codes
sudo docker compose up -d --build
```

Приложение слушает `127.0.0.1:8501` — снаружи недоступно напрямую, только
через nginx (шаг 4).

## 4. Настроить nginx + HTTPS без покупки домена

`sslip.io` резолвит `SERVER_IP.sslip.io` прямо в ваш IP — Let's Encrypt
выдаёт на такой адрес настоящий доверенный сертификат бесплатно.

```bash
export HOST="$(curl -s ifconfig.me | tr '.' '-').sslip.io"
echo "Сайт будет доступен на: https://$HOST"

sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/crypto-codes
sudo sed -i "s/YOUR_HOST/$HOST/" /etc/nginx/sites-available/crypto-codes
sudo ln -s /etc/nginx/sites-available/crypto-codes /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

sudo certbot --nginx -d "$HOST"
```

Certbot сам допишет в конфиг блок `listen 443 ssl` и настроит редирект с
80 на 443.

## 5. Открыть порты в файрволе

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

(Порт 8501 наружу открывать не нужно — он проброшен только на localhost.)

## Проверка

Открыть `https://SERVER_IP.sslip.io` (адрес из шага 4) — должна открыться
страница «Объединение Excel-файлов с кодами маркировки».

## Без HTTPS (максимально просто)

Если сертификат не нужен — пропустить шаг 4, в `docker-compose.yml` заменить
`127.0.0.1:8501:8501` на `8501:8501` и открыть `sudo ufw allow 8501/tcp`.
Сайт будет доступен по `http://SERVER_IP:8501` без шифрования — учитывайте,
что коды маркировки в загружаемых файлах при этом идут по сети открытым
текстом.

## Обновление после изменений в коде

```bash
# локально — та же rsync-команда из шага 2, затем:
ssh user@SERVER_IP "cd /opt/crypto-codes && sudo docker compose up -d --build"
```
