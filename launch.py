#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2012-2023 MOD Audio UG
# SPDX-License-Identifier: AGPL-3.0-or-later

# Launcher for mod-ui development on a PC.
#
# - Starts mod-host if available and JACK is running, otherwise uses dev mode.
# - Starts the mod-ui web server.
# - Opens the UI in the default browser once the server is ready.
# - Monitors the /hello endpoint: when the browser tab is closed (WebSocket
#   gone for TAB_CLOSE_GRACE seconds), shuts down the server and mod-host.
# - Also shuts down cleanly on Ctrl+C or if the server exits on its own.

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

ROOT = os.path.dirname(os.path.realpath(__file__))
PORT = int(os.environ.get('MOD_DEVICE_WEBSERVER_PORT', 8888))
URL  = 'http://localhost:{}/'.format(PORT)

MOD_HOST_ARGS = ['mod-host', '-n', '-p', '5555', '-f', '5556']

# Seconds the tab must be offline before we treat it as "closed".
# A short grace period lets the user refresh without triggering shutdown.
TAB_CLOSE_GRACE = 8


def jack_is_running():
    if shutil.which('jack_control') is not None:
        ret = subprocess.call(['jack_control', 'status'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ret == 0
    jack_socket = '/tmp/jack-{}/jack_0'.format(os.getuid())
    return os.path.exists(jack_socket)


def wait_for_server(port, timeout=30):
    """Block until the server accepts TCP connections or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(('localhost', port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def monitor_tab(hello_url, shutdown_event, server_proc):
    """Poll /hello and set shutdown_event when the browser tab has been closed.

    The shutdown is triggered only after the tab was first seen as online
    (so a slow browser start does not cause an immediate exit) and then
    stays offline for TAB_CLOSE_GRACE seconds (so a page refresh is safe).
    """
    was_online    = False
    offline_since = None

    while not shutdown_event.is_set():
        # Stop if the server process has already exited.
        if server_proc.poll() is not None:
            shutdown_event.set()
            return

        try:
            with urllib.request.urlopen(hello_url, timeout=2) as resp:
                data   = json.loads(resp.read())
                online = data.get('online', False)
        except Exception:
            online = False

        if online:
            was_online    = True
            offline_since = None
        elif was_online:
            if offline_since is None:
                offline_since = time.time()
            elif time.time() - offline_since >= TAB_CLOSE_GRACE:
                print('\nBrowser tab closed — shutting down.')
                shutdown_event.set()
                return

        time.sleep(2)


def stop(proc, name, timeout=5):
    if proc is None or proc.poll() is not None:
        return
    print('Stopping {}...'.format(name))
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()


def main():
    env       = os.environ.copy()
    host_proc = None

    # --- mod-host ---
    if shutil.which('mod-host') is not None:
        if jack_is_running():
            print('JACK is running — starting mod-host...')
            host_proc = subprocess.Popen(MOD_HOST_ARGS, env=env)
            time.sleep(1)  # let mod-host bind its sockets
            env['MOD_DEV_HOST']        = '0'
            env['MOD_DEV_ENVIRONMENT'] = '0'
        else:
            print('WARNING: mod-host found but JACK is not running.')
            print('         Start JACK first for audio support.')
            print('         Running in dev mode (no audio) for now.')
            env['MOD_DEV_HOST'] = '1'
    else:
        print('mod-host not found — running in dev mode (no audio).')
        env['MOD_DEV_HOST'] = '1'

    # --- web server ---
    print('Starting mod-ui web server on port {}...'.format(PORT))
    server_proc = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, 'server.py')],
        env=env,
    )

    # --- browser ---
    print('Waiting for server to be ready...')
    if not wait_for_server(PORT):
        print('Server did not respond within 30 s — opening browser anyway.')
    print('Opening {}'.format(URL))
    webbrowser.open(URL)

    # --- background monitor ---
    shutdown_event = threading.Event()
    monitor = threading.Thread(
        target=monitor_tab,
        args=(URL + 'hello', shutdown_event, server_proc),
        daemon=True,
    )
    monitor.start()

    # --- wait for shutdown signal ---
    try:
        shutdown_event.wait()
    except KeyboardInterrupt:
        print('\nCtrl+C — shutting down.')
        shutdown_event.set()
    finally:
        stop(server_proc, 'mod-ui')
        stop(host_proc,   'mod-host')


if __name__ == '__main__':
    main()
