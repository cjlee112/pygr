#!/usr/bin/env python

import ConfigParser, os, smtplib, time
try:
    from email.mime.text import MIMEText
except ImportError:
    from email.MIMEText import MIMEText

config = ConfigParser.ConfigParser({'expectedRunningTime' : '-1', 'mailServer' : '', 'runningTimeAllowedDelay' : '0'})
config.read([ os.path.join(os.path.expanduser('~'), '.pygrrc'), os.path.join(os.path.expanduser('~'), 'pygr.cfg'), '.pygrrc', 'pygr.cfg' ])
expectedRunningTime = config.get('megatests', 'expectedRunningTime')
logdir = config.get('megatests', 'logDir')
mailsender = config.get('megatests', 'mailFrom')
mailserver = config.get('megatests', 'mailServer')
maillist_fail = config.get('megatests', 'mailTo_failed')
maillist_pass = config.get('megatests', 'mailTo_ok')
runningTimeAllowedDelay = config.get('megatests', 'runningTimeAllowedDelay')

timeStr = time.ctime()
dateStr = ' '.join([ix for ix in timeStr.split(' ') if ':' not in ix])

# Gather the runner script's output
os.chdir(logdir)
sendStr = 'MEGATEST report, generated ' + timeStr + '\n\n'
sendStr += 'Test started: ' + open('tmp1_megatest.log', 'r').readlines()[0]
sendStr += 'PYTHONPATH = ' + open('tmp3_megatest.log', 'r').read() + '\n'
sendStr += 'Output of standard tests:\n' + ''.join(open('tmp2_megatest.log', 'r').readlines()[-5:]) + '\n\n'
sendStr += 'Output of megatests:\n' + ''.join(open('tmp4_megatest.log', 'r').readlines()[-5:]) + '\n\n'
sendStr += 'Test finished: ' + open('tmp5_megatest.log', 'r').readlines()[0] + '\n'

# Try to determine whether the test has failed or not
nError = 0
abnormalStop = 0

# Compare running time with expectations, mark test as failed if it took
# significantly longer than it should (some latitude is given to account
# for fluctuations due to machine/network/... load).
# Unlike later on, increment abnormalStop first and decrement it in case
# of failure - it's cleaner than the other way around.
abnormalStop += 1
expectedRunningTime = float(expectedRunningTime)
if expectedRunningTime >= 0.:
    startTime = int(open('tmp1_megatest.log', 'r').readlines()[1].split(':')[1].strip())
    endTime = int(open('tmp5_megatest.log', 'r').readlines()[1].split(':')[1].strip())
    if runningTimeAllowedDelay[-1] == '%':
        maxRunningTime = expectedRunningTime * (1 + float(runningTimeAllowedDelay[:-1]) / 100.)
    else:
        maxRunningTime = expectedRunningTime + float(runningTimeAllowedDelay)
    runMinutes = (endTime - startTime) / 60.
    if runMinutes > maxRunningTime:
        sendStr += '\n#####################################################################\n'
        sendStr += ('ERROR: megatests took %s minutes to complete, expected %s minutes' % (runMinutes, expectedRunningTime))
        sendStr += '\n#####################################################################\n'
        abnormalStop -= 1

for lines in sendStr.splitlines():
    if lines[:4] == 'INFO' and 'passed' in lines and 'failed' in lines and 'skipped' in lines:
        nError += int(lines[18:].split(',')[1].strip().split(' ')[0])
        abnormalStop += 1

if nError == 0 and abnormalStop == 3:
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

