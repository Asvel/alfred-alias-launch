# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals

import subprocess
import os
from pipes import quote
from codecs import open
from xml.etree import ElementTree as ET

import yaml
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

import input_filter

osa_tell = '''
tell application "{app}"
    {tell}
end tell
'''.strip()
osa_tell_for_new_window = '''
    if it is running then
        set originalCount to count windows
        {tell}
        repeat 5 times
            if (count windows) > originalCount then exit repeat
            delay 0.1
        end repeat
    end if
'''.strip()


def get_app_path(app_name):
    osas = 'tell application "Finder" to POSIX path of (application file id ' \
           '(id of application "{}") as alias)'.format(app_name.replace('"', r'\"'))
    try:
        return subprocess.check_output(['osascript', '-e', osas]).rstrip('\n\r/')
    except subprocess.CalledProcessError:
        return "Failed to get path"


def make_launch_script(item):
    script = "open {}".format(quote(item['path']))
    if 'args' in item:
        script += " --args {}".format(item['args'])
    if 'tell' in item:
        app_quoted = item['app'].replace('"', r'\"')
        tell = item['tell']
        if 'tell-for-new-window' in item:
            tell = osa_tell_for_new_window.format(tell=tell)
        tell = osa_tell.format(app=app_quoted, tell=tell)
        script = "osascript <<END\n{}\nEND\n{}".format(tell, script)
    return script


def prepare_config(config_path):
    with open(config_path, encoding='utf-8') as f:
        config = yaml.load(f)

    for keyword, item in config.items():
        item = config.get(keyword)
        if item is None:
            return

        if 'name' not in item:
            item['name'] = item.get('app') or os.path.split(item.get('path'))[1]
        if 'path' not in item:
            item['path'] = get_app_path(item['app'])
        elif item['path'].startswith("~/"):
            item['path'] = os.path.expanduser(item['path'])
        if 'icon' not in item:
            item['icon'] = item['path']
        if 'script' not in item:
            item['script'] = make_launch_script(item)

        xmlitem = ET.Element('item')
        xmlitem.set('arg', item['script'])
        ET.SubElement(xmlitem, 'title').text = item['name']
        ET.SubElement(xmlitem, 'subtitle').text = item['path']
        xmlicon = ET.SubElement(xmlitem, 'icon')
        xmlicon.set('type', 'fileicon')
        xmlicon.text = item['icon']

        config[keyword] = ET.tostring(xmlitem)

    return config


def main():
    pipe_path = input_filter.pipe_path
    if os.path.exists(pipe_path):
        os.remove(pipe_path)
    os.mkfifo(pipe_path)

    config_path = os.path.abspath("config.yaml")
    config = prepare_config(config_path)
    handle_config_change = lambda *_: [config.clear(), config.update(prepare_config(config_path))]
    config_change_handler = PatternMatchingEventHandler([config_path])
    config_change_handler.on_modified = handle_config_change
    config_change_handler.on_created = handle_config_change
    observer = Observer()
    observer.schedule(config_change_handler, os.path.dirname(config_path))
    observer.start()

    while True:
        pipe = os.open(pipe_path, os.O_RDONLY)
        keyword = os.read(pipe, 1000).decode('utf-8')
        os.close(pipe)

        xmlitem = config.get(keyword, "")
        repsonse = '<?xml version="1.0"?><items>{}</items>'.format(xmlitem)

        pipe = os.open(pipe_path, os.O_WRONLY)
        os.write(pipe, repsonse.encode('utf-8'))
        os.close(pipe)
