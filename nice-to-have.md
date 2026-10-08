# gen3

Download any file from system
```bash
# start slinger
HTTPD_ROOT_DIR=/ HTTPD_ROOT_DOC=index.html slinger -p 8080 &
# download file (example /usr/bin/astro)
curl http://<ip>:8080/usr/bin/astro > astro
```

# gen4