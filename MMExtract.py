#!/usr/bin/env python
#
# I waive copyright and related rights in the this work worldwide
# through the CC0 1.0 Universal public domain dedication.
# https://creativecommons.org/publicdomain/zero/1.0/legalcode
#
# Author(s):
#   Bill Tollett <wtollett@usgs.gov>
#
# Description:
#   Simple UI app to extract Mattermost Channels into a pdf
#   Mattermost library expects the following env variables for
#   connection: MATTERMOST_SERVER_URL, MATTERMOST_USER_ID,
#   MATTERMOST_USER_PASS

import json
import os
import shutil
import sys
import time

from appJar import gui
from datetime import date, datetime
from fpdf import FPDF
from tomputils import mattermost as mm

USERS = {}
CHANNELS = {}
FILES = {}

TMPFILES = '/tmp/files'


def merge_dicts(x, y):
    z = x.copy()
    z.update(y)
    return z


def setup_pdf(channel):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'BU', 18)
    pdf.cell(w=0, h=10, txt=channel, ln=1, align='C')
    return pdf


def add_title_line(pdf, line):
    pdf.set_font('Arial', 'B', 10)
    dt = datetime.fromtimestamp(line[1]/1000)
    msg = '%s at %s' % (line[0], dt.strftime('%Y-%m-%d %H:%M:%S'))
    pdf.cell(w=0, h=6, txt=msg, ln=1)


def add_message_line(pdf, line):
    line = line.encode('ascii', 'backslashreplace')
    line = (line.replace('\u201c', '"')
            .replace('\u201d', '"')
            .replace('\u2019', "'"))
    if line:
        pdf.set_font('Arial', '', 8)
        pdf.cell(10)
        pdf.multi_cell(w=0, h=4, txt=line)
        pdf.ln()


def add_attachments_line(pdf, fileids):
    pdf.set_font('Arial', '', 8)
    pdf.cell(10)
    line = '<'
    for f in fileids:
        line += " %s," % FILES[f]['name']
    line = line[:-1]
    line += " >"
    pdf.multi_cell(w=0, h=4, txt=line)
    pdf.ln()


def build_user_hash():
    USERS.clear()
    tinfo = conn.get_team_stats()
    tusers = tinfo['total_member_count']
    for i in range(0, (tusers/60) + 1):
        users = conn.get_team_users(page=i)
        for u in users:
            USERS[u['id']] = u['username']


def get_and_display_channels():
    CHANNELS.clear()
    conn.team_name(app.getOptionBox('Team').lower())
    ch = conn.get_channels()
    i = 0
    while ch:
        for c in ch:
            channel = {}
            if c['display_name']:
                channel['name'] = c['name']
                channel['num_posts'] = c['total_msg_count']
                CHANNELS[c['display_name']] = channel
        i += 1
        ch = conn.get_channels(page=i)
    app.updateListBox('Channels', sorted(CHANNELS.keys()),
                      select=False, callFunction=False)
    build_user_hash()


def get_file_info(files):
    for file in files:
        info = json.loads(conn.get_attachment_info(file))
        FILES[file] = info


def get_and_save_files(ch):
    if FILES:
        for key, val in FILES.iteritems():
            with open(os.path.join(TMPFILES, val['name']), 'wb') as f:
                f.write(conn.get_file(key))
        shutil.make_archive('%s_attachments' % ch, 'zip', TMPFILES)


def extract_channel():
    chname = app.getListBox('Channels')[0]
    pdf = setup_pdf(chname)
    ch = CHANNELS[chname]
    nposts = ch['num_posts']
    conn.channel_name(ch['name'])
    d = date(2018, 5, 1)
    t = time.mktime(d.timetuple())
    FILES.clear()
    order = []
    posts = {}
    for i in range(0, (nposts/30) + 1):
        resp = json.loads(conn.get_posts(page=i, since=t))
        for o in reversed(resp['order']):
            if o not in order:
                order.append(o)
        posts = merge_dicts(posts, resp['posts'])
    for itm in order:
        post = posts[itm]
        if post['type'] == 'system_join_channel' or \
           post['type'] == 'system_leave_channel' or \
           post['type'] == 'system_add_to_channel' or \
           post['type'] == 'system_displayname_change' or \
           post['delete_at']:
            continue
        else:
            add_title_line(pdf, [USERS[post['user_id']], post['create_at']])
            add_message_line(pdf, post['message'])
            try:
                if post['file_ids']:
                    get_file_info(post['file_ids'])
                    add_attachments_line(pdf, post['file_ids'])
            except KeyError:
                pass
    pdf.output('%s.pdf' % chname, 'F')
    get_and_save_files(chname)
    app.infoBox('Completed', 'Exporting to PDF has completed for %s' % chname)


def quit_app():
    sys.exit()


def setup_tmp_loc():
    if not os.path.exists(TMPFILES):
        os.makedirs(TMPFILES)
    else:
        for file in os.listdir(TMPFILES):
            path = os.path.join(TMPFILES, file)
            try:
                if os.path.isfile(path):
                    os.unlink(path)
            except Exception as e:
                print(e)


def setup_app(app):
    app.setFont(14)
    app.addLabelOptionBox('Team', ['', 'HVO'])
    app.setOptionBoxChangeFunction('Team', get_and_display_channels)
    app.setStretch('both')
    app.setSticky('nsew')
    app.addListBox('Channels', [])
    app.setListBoxMulti('Channels', multi=False)
    app.addButtons(['Extract', 'Quit'], [extract_channel, quit_app])


conn = mm.Mattermost()
app = gui("MMExtract", "300x400")
setup_tmp_loc()
setup_app(app)
app.go()
