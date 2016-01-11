# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals

import os
import sys
import logging


tempdir = os.path.join(os.environ['TMPDIR'], "alfred-alias-launch")
if not os.path.exists(tempdir):
    os.mkdir(tempdir)

log_path = os.path.join(tempdir, "log")
pipe_path = os.path.join(tempdir, "pipe")
lock_path = os.path.join(tempdir, "lock")

logging.basicConfig(
    format='[%(asctime)-15s %(levelname)-1s] %(message)s',
    filename=log_path,
    level=logging.INFO,
)


def query(keyword):
    logging.debug('query ' + keyword)
    try:
        os.open(lock_path, os.O_CREAT | os.O_NONBLOCK | os.O_EXLOCK)
    except OSError:
        pass
    else:
        logging.debug('forked')
        if os.fork() == 0:
            os.setsid()
            os.dup2(os.open('/dev/null', os.O_RDONLY), sys.stdin.fileno())
            os.dup2(os.open('/dev/null', os.O_APPEND), sys.stdout.fileno())
            os.dup2(os.open('/dev/null', os.O_APPEND), sys.stderr.fileno())
            from input_filter import provider
            provider.main()

    pipe = os.open(pipe_path, os.O_WRONLY)
    os.write(pipe, keyword.encode('utf-8'))
    os.close(pipe)
    pipe = os.open(pipe_path, os.O_RDONLY)
    repsonse = os.read(pipe, 1000).decode('utf-8')
    os.close(pipe)
    print(repsonse)
