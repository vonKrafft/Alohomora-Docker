#!/bin/sh

# Copyright (c) 2019 vonKrafft <contact@vonkrafft.fr>
# 
# This file is part of Alohomora-Docker
# Source code available on https://github.com/vonKrafft/Alohomora-Docker
# 
# This file may be used under the terms of the GNU General Public License
# version 3.0 as published by the Free Software Foundation and appearing in
# the file LICENSE included in the packaging of this file. Please review the
# following information to ensure the GNU General Public License version 3.0
# requirements will be met: http://www.gnu.org/copyleft/gpl.html.
# 
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.

NGINX_VHOST_DIR=/docker/proxy/vhost.d
ALOHOMORA_DIR=/docker/alohomora

while inotifywait -e close_write "${ALOHOMORA_DIR}/allow.conf"; do
    cp "${ALOHOMORA_DIR}/allow.conf" "${NGINX_VHOST_DIR}/allow.conf"
    NGINX_IMG=$(docker ps --filter "label=com.github.jrcs.letsencrypt_nginx_proxy_companion.nginx_proxy=true" -q)
    docker exec $NGINX_IMG nginx -s reload
done
