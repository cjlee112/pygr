#!/usr/bin/env python

import ConfigParser, os, smtplib, time
from email.mime.text import MIMEText

config = ConfigParser.ConfigParser({'mailServer' : ''})
config.read([ os.path.expanduser('~/.pygrrc'), os.path.expanduser('~/pygr.cfg'), 'pygrrc', 'pygr.cfg' ])	# FIXME: make this OS-dependent?
logdir = config.get('megatests', 'logDir')
mailsender = config.get('megatests', 'mailFrom')
mailserver = config.get('megatests', 'mailServer')
maillist_fail = config.get('megatests', 'mailTo_failed')
maillist_pass = config.get('megatests', 'mailTo_ok')

timeStr = time.ctime()
dateStr = ' '.join([ix for ix in timeStr.split(' ') if ':' not in ix])

# Gather the runner script's output
os.chdir(logdir)
sendStr = 'MEGATEST report, generated ' + timeStr + '\n\n'
sendStr += 'Test started: ' + open('tmp1_megatest.log', 'r').read()
sendStr += 'PYTHONPATH = ' + open('tmp3_megatest.log', 'r').read() + '\n'
sendStr += 'Output of standard tests:\n' + ''.join(open('tmp2_megatest.log', 'r').readlines()[-5:]) + '\n\n'
sendStr += 'Output of megatests:\n' + open('tmp4_megatest.log', 'r').read() + '\n\n'
sendStr += 'Test finished: ' + open('tmp5_megatest.log', 'r').read()

# Try to determine whether the test has failed or not
nError = 0
abnormalStop = 0
for lines in sendStr.splitlines():
    # Standard-test output
    if lines[:4] == 'INFO' and 'passed' in lines and 'failed' in lines and 'skipped' in lines:
        nError += int(lines[18:].split(',')[1].strip().split(' ')[0])
        abnormalStop += 1
    # Megatest output
    if lines[:6] == 'FINAL:':
        nError += int(lines[7:30].split(' ')[0])
        abnormalStop += 1
if nError == 0 and abnormalStop == 2:
    maillist = maillist_pass
else:
    maillist = maillist_fail

# Create and send the message
msg = MIMEText(sendStr)
msg['From'] = mailsender
msg['To'] = maillist
msg['Subject'] = 'Megatest on ' + dateStr + ' with ' + str(nError) + ' Errors'
s = smtplib.SMTP(mailserver)
s.connect()
s.sendmail(mailsender, maillist.replace(',', ' ').split(), msg.as_string())
s.close()

