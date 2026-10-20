NGINX_CONF = """server {
    listen 8055;
    server_name thesimplechef.com www.thesimplechef.com thesimplechef.local localhost;
    
    root /var/www/thesimplechef/public;
    index index.html;
    
    # Isolated client logging
    access_log /var/log/nginx/thesimplechef_access.log;
    error_log /var/log/nginx/thesimplechef_error.log;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api/v1/chef/ {
        proxy_pass http://127.0.0.1:8080/api/v1/chef/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    # Security: deny access to hidden files (.git, .env)
    location ~ /\\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
"""

LOGROTATE_CONF = """/var/log/nginx/thesimplechef_access.log /var/log/nginx/thesimplechef_error.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 client_web_user www-data
    sharedscripts
    postrotate
        [ ! -f /run/nginx.pid ] || kill -USR1 `cat /run/nginx.pid`
    endscript
}
"""

with open("/etc/nginx/sites-available/thesimplechef", "w", encoding="utf-8") as f:
    f.write(NGINX_CONF)

with open("/etc/logrotate.d/thesimplechef", "w", encoding="utf-8") as f:
    f.write(LOGROTATE_CONF)

# Update /etc/nginx/nginx.conf to include sites-enabled if not already present
with open("/etc/nginx/nginx.conf", "r", encoding="utf-8") as f:
    nginx_main = f.read()

if "include /etc/nginx/sites-enabled/*;" not in nginx_main:
    # insert inside http block
    idx = nginx_main.find("http {")
    if idx != -1:
        insert_pos = idx + len("http {")
        nginx_main = nginx_main[:insert_pos] + "\n    include /etc/nginx/sites-enabled/*;\n" + nginx_main[insert_pos:]
        with open("/etc/nginx/nginx.conf", "w", encoding="utf-8") as f:
            f.write(nginx_main)

print("WSL Nginx and Logrotate deployed successfully!")
