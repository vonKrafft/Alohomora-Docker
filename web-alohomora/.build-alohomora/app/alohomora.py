#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

import aiohttp
import aiohttp_jinja2
import aiohttp_session
import aiohttp_session.cookie_storage
import asyncio
import base64
import cryptography.fernet
import jinja2
import os
import re
import sqlite3
import sys
import time

# Require Python 3.6+
assert sys.version_info >= (3, 6)


class AlohomoraDatabase:

    def __init__(self, dbfile: str):
        self.conn = sqlite3.connect(dbfile)
        self.create_table()

    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()

    def create_table(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS white_list (
            ip TEXT,
            label TEXT,
            expiration INTEGER
        )''')
        self.conn.commit()

    def select(self) -> list:
        c = self.conn.cursor()
        c.execute('SELECT ROWID, ip, label, expiration FROM white_list')
        return [{ 'id': row[0], 'ip': row[1], 'label': row[2], 'expiration': row[3] } for row in c.fetchall()]

    def select_expired(self) -> list:
        c = self.conn.cursor()
        c.execute('SELECT ROWID, ip, label, expiration FROM white_list WHERE expiration > 0 AND expiration < ?', (int(time.time()), ))
        return [{ 'id': row[0], 'ip': row[1], 'label': row[2], 'expiration': row[3] } for row in c.fetchall()]

    def insert(self, ip: str, label: str, expiration: int):
        c = self.conn.cursor()
        c.execute('INSERT INTO white_list (ip, label, expiration) VALUES (?, ?, ?)', (ip, label, expiration))
        self.conn.commit()
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Added {ip} ({expiration}) '{label}'")

    def delete(self, rowid: int):
        c = self.conn.cursor()
        c.execute('DELETE FROM white_list WHERE ROWID = ?', (rowid, ))
        self.conn.commit()
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Deleted #{rowid}")

    def delete_expired(self) -> bool:
        c = self.conn.cursor()
        c.execute('DELETE FROM white_list WHERE expiration > 0 AND expiration < ?', (int(time.time()), ))
        self.conn.commit()
        if c.rowcount > 0:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Cleaned ({c.rowcount} row{'s' if c.rowcount > 1 else ''})")
        return c.rowcount > 0


routes = aiohttp.web.RouteTableDef()
db = AlohomoraDatabase(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'alohomora.sqlite'))
token = os.environ["ALOHOMORA_TOKEN"] if "ALOHOMORA_TOKEN" in os.environ else False


@routes.get('/')
@aiohttp_jinja2.template('index.jinja2')
async def handle_index(request: aiohttp.web.Request) -> dict:
    session = await require_authenticated_user(request)
    return {
        'current_ip': get_ip_address(request),
        'current_time': int(time.time()),
        'white_list': db.select(),
    }


@routes.get('/login')
@aiohttp_jinja2.template('login.jinja2')
async def handle_login(request: aiohttp.web.Request) -> dict:
    return {
        'token_is_not_set': token is False,
    }


@routes.post('/login')
async def handle_login_form(request: aiohttp.web.Request) -> aiohttp.web.Response:
    post = await request.post()
    if post.get('token', None) == token:
        session = await aiohttp_session.get_session(request)
        session['token'] = post.get('token')
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Successfully authenticated from {get_ip_address(request)}")
        return aiohttp.web.HTTPFound('/')
    return aiohttp.web.HTTPFound('/login')


@routes.post('/add')
async def handle_add(request: aiohttp.web.Request) -> aiohttp.web.Response:
    session = await require_authenticated_user(request)
    post = await request.post()
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', post.get('ip')):
        db.insert(
            ip=post.get('ip'),
            label=re.sub(r'[^A-Za-z0-9_.,# \'-]+', '', post.get('label', '')),
            expiration=duration(post.get('expiration', ''))
        )
        update_allow_conf()
    return aiohttp.web.HTTPFound('/')


@routes.get(r'/delete/{id:\d+}')
async def handle_delete(request: aiohttp.web.Request) -> aiohttp.web.Response:
    session = await require_authenticated_user(request)
    db.delete(int(request.match_info['id']))
    update_allow_conf()
    return aiohttp.web.HTTPFound('/')


@routes.get('/allow.conf')
async def download_conf(request: aiohttp.web.Request) -> aiohttp.web.Response:
    session = await require_authenticated_user(request)
    allow_conf = '\n'.join([dbrow_to_str(r['id'], r['ip'], r['label'], r['expiration']) for r in db.select()])
    response = aiohttp.web.Response(text=allow_conf)
    response.headers['Content-Type'] = 'application/force-download' if 'dl' in request.query else 'text/plain'
    return response


async def require_authenticated_user(request: aiohttp.web.Request) -> aiohttp_session.Session:
    session = await aiohttp_session.get_session(request)
    if session.get('token', None) != token:
        raise aiohttp.web.HTTPFound('/login')
    return session


def get_ip_address(request: aiohttp.web.Request) -> str:
    return request.headers['X-Forwarded-For'] if 'X-Forwarded-For' in request.headers else request.transport.get_extra_info('peername')[0]

def duration(text: str) -> int:
    if text.lower() == 'forever':
        return 0
    if 'hour' in text.lower():
        return (3600 * int(re.sub(r'[^0-9]+', '', text))) + int(time.time())
    if 'day' in text.lower():
        return (86400 * int(re.sub(r'[^0-9]+', '', text))) + int(time.time())
    if 'week' in text.lower():
        return (604800 * int(re.sub(r'[^0-9]+', '', text))) + int(time.time())
    return int(time.time())


def dbrow_to_str(rowid: int, ip: str, label: str, expiration: int) -> str:
    expiration = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(expiration)) if expiration > 0 else 'Permanent'.ljust(19)
    conf_row = f"allow {ip};".ljust(22)
    return f"{conf_row} # {str(rowid).ljust(3)} | {expiration} | {label}"


def update_allow_conf():
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'allow.conf')
    with open(filename, 'w') as f:
        f.write('\n'.join([dbrow_to_str(r['id'], r['ip'], r['label'], r['expiration']) for r in db.select()]))
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Update configuration file '{filename}'")


async def refresh_list():
    try:
        update_allow_conf()
        while True:
            if db.delete_expired():
                update_allow_conf()
            await asyncio.sleep(600)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(e)
    finally:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Expiration updater is down")


async def start_background_tasks(app: aiohttp.web.Application):
    app['expiration_updater'] = asyncio.create_task(refresh_list())


async def cleanup_background_tasks(app: aiohttp.web.Application):
    app['expiration_updater'].cancel()
    await app['expiration_updater']


def make_app() -> aiohttp.web.Application:
    app = aiohttp.web.Application()
    secret_key = base64.urlsafe_b64decode(cryptography.fernet.Fernet.generate_key())
    aiohttp_session.setup(app, aiohttp_session.cookie_storage.EncryptedCookieStorage(secret_key))
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')))
    app.router.add_static('/static', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'))
    app.router.add_routes(routes)
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    return app


if __name__ == '__main__':
    aiohttp.web.run_app(make_app())
