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
import sys
import time

from appJar import gui
from datetime import date, datetime
from fpdf import FPDF
from tomputils import mattermost as mm

USERS = {}
CHANNELS = {}


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
    pdf.set_font('Arial', 'B', 12)
    dt = datetime.fromtimestamp(line[1]/1000)
    msg = '%s - %s' % (line[0], dt.strftime('%Y-%m-%d %H:%M:%S'))
    pdf.cell(w=0, h=8, txt=msg, ln=1)


def add_message_line(pdf, line):
    pdf.set_font('Arial', '', 10)
    pdf.cell(15)
    line = line.encode('ascii', 'backslashreplace')
    line = (line.replace('\u201c', '"')
            .replace('\u201d', '"')
            .replace('\u2019', "'"))
    pdf.multi_cell(w=0, h=6, txt=line)
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


def extract_channel():
    chname = app.getListBox('Channels')[0]
    pdf = setup_pdf(chname)
    ch = CHANNELS[chname]
    nposts = ch['num_posts']
    conn.channel_name(ch['name'])
    d = date(2018, 5, 1)
    t = time.mktime(d.timetuple())
    order = []
    posts = {}
    for i in range(0, (nposts/30) + 1):
        resp = json.loads(conn.get_posts(page=i, since=t))
        order = list(reversed(resp['order'])) + order
        posts = merge_dicts(posts, resp['posts'])
    for itm in order:
        post = posts[itm]
        if post['type'] == 'system_join_channel' or \
           post['type'] == 'system_leave_channel':
            continue
        else:
            add_title_line(pdf, [USERS[post['user_id']], post['create_at']])
            add_message_line(pdf, post['message'])
    pdf.output('%s.pdf' % chname, 'F')
    app.infoBox('Completed', 'Exporting to PDF has completed for %s' % chname)


def quit_app():
    sys.exit()


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
setup_app(app)
app.go()
