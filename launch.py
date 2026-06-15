#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2012-2023 MOD Audio UG
# SPDX-License-Identifier: AGPL-3.0-or-later

# Launcher for mod-ui development on a PC.
# - Starts mod-host if available and JACK is running, otherwise uses dev mode.
# - Starts the mod-ui web server.
# - Opens the UI in the default browser once the server is ready.
# - Shuts everything down cleanly on exit (Ctrl+C).

import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser

ROOT = os.path.dirname(os.path.realpath(__file__))
PORT = int(os.environ.get('MOD_DEVICE_WEBSERVER_PORT', 8888))
URL  = 'http://localhost:{}/'.format(PORT)

MOD_HOST_ARGS = ['mod-host', '-n', '-p', '5555', '-f', '5556']


def jack_is_running():
    if shutil.which('jack_control') is not None:
        ret = subprocess.call(['jack_control', 'status'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ret == 0
    # Fallback: try to reach the JACK socket directly
    jack_socket = '/tmp/jack-{}/jack_0'.format(os.getuid())
    return os.path.exists(jack_socket)


def wait_for_server(port, timeout=30):
    """Return True once the server is accepting TCP connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(('localhost', port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def main():
    env = os.environ.copy()
    host_proc = None

    # --- mod-host ---
    if shutil.which('mod-host') is not None:
        if jack_is_running():
            print('JACK is running — starting mod-host...')
            host_proc = subprocess.Popen(MOD_HOST_ARGS, env=env)
            # Give mod-host a moment to bind its sockets before the web server connects.
            time.sleep(1)
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
    if wait_for_server(PORT):
        print('Opening {}'.format(URL))
    else:
        print('Server did not respond within 30 s — opening browser anyway.')
    webbrowser.open(URL)

    # --- wait / shutdown ---
    try:
        server_proc.wait()
    except KeyboardInterrupt:
        print('\nShutting down...')
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_proc.kill()
    finally:
        if host_proc is not None:
            print('Stopping mod-host...')
            host_proc.terminate()
            try:
                host_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                host_proc.kill()


if __name__ == '__main__':
    main()
