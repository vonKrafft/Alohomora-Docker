# Alohomora-Docker

**Alohomora** is a python WebUI designed to manage Nginx white-listed IP addresses.

The web interface allows you to add and remove IP addresses from a list. These IP addresses are stored in a SQLite database and associated with a label and an expiration date. As soon as an IP address is added, deleted, or expired, an `allow.conf` file is generated. A watcher automatically detects any change in the `allow.conf` file and copies it in the Nginx configuration directory before reloading Nginx.

![Web interface of Alohomora](https://raw.githubusercontent.com/vonKrafft/Alohomora-Docker/master/preview.png)

> This project is based on Blusky's work (https://github.com/TheBlusky/alohomora).

## Installation

You have to install `docker` and `docker-compose` (https://docs.docker.com/compose/install/). Remember to set your own token as an environment variable **ALOHOMORA_TOKEN** in `docker-compose.yml`!

```
$ git clone https://github.com/vonKrafft/Alohomora-Docker
$ cd Alohomora-Docker
$ docker-compose up -d
```

You will need to install `inotify` to detect changes to the `allow.conf` file. Make sure the script is executable and run it as a daemon (you can redirect _stdout_ to a log file). Remember to change the **NGINX_VHOST_DIR** and **ALOHOMORA_DIR** values to fit your directory organization!

```
$ sudo apt install inotify-tools
$ chmod +x web-alohomora/alohomora-watcher.sh 
$ setsid ./alohomora_watcher.sh >alohomora.logs 2>&1 < /dev/null &
```

## Dependencies

**Docker**

- Python:3-alpine - Docker Official Images (https://hub.docker.com/_/python)

**Web interface**

- Bootstrap v4.3.1 (https://getbootstrap.com/)

## License

This source code may be used under the terms of the GNU General Public License version 3.0 as published by the Free Software Foundation and appearing in the file LICENSE included in the packaging of this file. Please review the following information to ensure the GNU General Public License version 3.0 requirements will be met: http://www.gnu.org/copyleft/gpl.html.