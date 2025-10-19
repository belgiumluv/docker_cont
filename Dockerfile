FROM debian:12-slim
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates bash supervisor inotify-tools openssl \
 && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates bash supervisor inotify-tools openssl \
    liblua5.4-0 libpcre2-8-0 libssl3 libcap2 libsystemd0 zlib1g libzstd1 liblz4-1 libgcrypt20 libgpg-error0 liblzma5 \
 && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates bash supervisor inotify-tools openssl \
    python3 python3-requests sqlite3 \
 && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates bash supervisor inotify-tools openssl sqlite3 \
    python3 python3-requests python3-nacl \
 && rm -rf /var/lib/apt/lists/*
 
WORKDIR /app

COPY haproxy-etc.tar.gz /tmp/haproxy-etc.tar.gz
RUN mkdir -p /etc/haproxy \
 && tar -xzf /tmp/haproxy-etc.tar.gz -C /etc/haproxy \
 && rm /tmp/haproxy-etc.tar.gz

COPY configs/haproxy.cfg /etc/haproxy/haproxy.cfg



# Копируем бинарник и конфиг
COPY bin/sing-box /vpn/sing-box
COPY configs/server.json /vpn/server.json

COPY bin/haproxy /usr/sbin/haproxy
COPY configs/haproxy.cfg /haproxy/haproxy.cfg

# Копируем служебные скрипты
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/cfgwatch.sh /usr/local/bin/cfgwatch.sh
COPY docker/cfgwatch-haproxy.sh /usr/local/bin/cfgwatch-haproxy.sh

RUN chmod +x /usr/local/bin/*.sh /vpn/sing-box
RUN chmod +x /usr/sbin/haproxy

COPY docker/haproxy-reloader.sh /usr/local/bin/haproxy-reloader.sh
COPY docker/singbox-reloader.sh  /usr/local/bin/singbox-reloader.sh
RUN chmod +x /usr/local/bin/haproxy-reloader.sh /usr/local/bin/singbox-reloader.sh

# бд
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates bash supervisor inotify-tools openssl sqlite3 \
 && rm -rf /var/lib/apt/lists/*

COPY docker/sqlite-init.sh /usr/local/bin/sqlite-init.sh
RUN chmod +x /usr/local/bin/sqlite-init.sh

COPY scripts /app/scripts
RUN chmod +x /app/scripts/*.py

# --- vpnserver ---
COPY bin/vpnserver /opt/vpnserver
COPY docker/run-vpnserver.sh /usr/local/bin/run-vpnserver.sh
RUN chmod +x /opt/vpnserver /usr/local/bin/run-vpnserver.sh

VOLUME ["/data", "/vpn", "/opt/ssl"]

EXPOSE 443 80
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
