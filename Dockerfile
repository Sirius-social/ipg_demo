FROM python:3.8

RUN apt-get update && \
  apt-get install -y coreutils nginx netcat
ENV LANG C.UTF-8
ENV PYTHONUNBUFFERED 1
ENV VERSION ${VERSION}


# Copy project files and install dependencies
ADD app /app
RUN	pip install -r /app/requirements.txt && chmod +x /app/wait-for-it.sh

# Environment
WORKDIR /app
ENV PYTHONPATH=/:$PYTHONPATH
EXPOSE 80

ENV WORKERS=4

RUN echo "[supervisord]\n\
logfile = /tmp/supervisord.log\n\
logfile_maxbytes = 1MB\n\
logfile_backups=1\n\
logLevel = error\n\
pidfile = /tmp/supervisord.pid\n\
nodaemon = true\n\
minfds = 1024\n\
minprocs = 200\n\
umask = 022\n\
user = root\n\
identifier = supervisor\n\
directory = /tmp\n\
nocleanup = true\n\
childlogdir = /tmp\n\
strip_ansi = false\n\
\n\
[program:nginx]\n\
command=nginx -g 'daemon off;'\n\
directory=/app\n\
autorestart = true\n\
stdout_logfile_maxbytes = 0 \n\
stderr_logfile_maxbytes = 0 \n\
stdout_logfile=/dev/stdout\n\
stderr_logfile=/dev/stdout\n\
[program:web]\n\
command=python main.py --production=on\n\
directory=/app\n\
autorestart = true\n\
stdout_logfile_maxbytes = 0 \n\
stderr_logfile_maxbytes = 0 \n\
stdout_logfile=/dev/stdout\n\
stderr_logfile=/dev/stdout\n"\
>> /etc/supervisord.conf

HEALTHCHECK --interval=60s --timeout=3s --start-period=30s \
  CMD curl -f http://localhost/health_check || exit 1

# FIRE!!!
CMD /app/wait-for-it.sh ${DATABASE_HOST}:${DATABASE_PORT-5432} --timeout=60 && \
    alembic upgrade head && \
    supervisord -c /etc/supervisord.conf
