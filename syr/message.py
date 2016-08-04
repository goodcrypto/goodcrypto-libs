#!/usr/bin/env python
'''
    Prepare and send a MIME message.

    Copyright 2015 GoodCrypto
    Last modified: 2015-11-11

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
import os, sh, time
from email.Encoders import encode_base64
from email.message import Message
from email.mime.text import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from traceback import format_exc

from syr import mime_constants
from syr.lock import locked
from syr.log import get_log

log = get_log()

DEBUGGING = False

def send_mime_message(sender, recipient, message, use_smtp_proxy=False, mta_address=None, mta_port=None):
    '''
        Send a message.

        The message can be a Message in string format or of the email.Message class.
    '''

    result_ok = False
    msg = None

    # syr.lock.locked() is only a per-process lock
    # syr.lock has a system wide lock, but it is not well tested
    with locked():
        try:
            if message is None:
                result_ok = False
                log('nothing to send')
            else:
                if type(message) == Message:
                    msg = message.as_string()
                else:
                    msg = message

                if use_smtp_proxy and mta_address is not None and mta_port is not None:
                    server = SMTP(mta_address, mta_port)
                    #server.set_debuglevel(1)
                    server.sendmail(sender, recipient, msg)
                    server.quit()
                else:
                    if DEBUGGING:
                        log('sendmail -B 8BITMIME -f {} {}'.format(sender, recipient))
                        log('msg:\n{}'.format(msg))
                    sendmail = sh.Command('/usr/sbin/sendmail')
                    sendmail('-B', '8BITMIME', '-f', sender, recipient, _in=msg)

                result_ok = True
        except Exception as exception:
            result_ok = False
            log('error while sending message: {}'.format(exception))
            raise

    return result_ok, msg

def prep_mime_message(
    from_address, to_address, subject, text=None, attachment=None, filename=None, extra_headers=None):
    '''
        Creates a MIME message.

        >>> # In honor of Sukhbir Singh, developed and maintains TorBirdy.
        >>> message = create_notice_message(
        ...    'mailer-daemon@goodcrypto.remote', 'sukhbir@goodcrypto.remote', 'test notice')
        >>> 'To: sukhbir@goodcrypto.remote' in message
        True
        >>> 'From: mailer-daemon@goodcrypto.remote' in message
        True
        >>> 'Subject: test notice' in message
        True
    '''

    message = None
    if from_address is None or to_address is None or (subject is None and text is None):
        log('unable to prepare message without from and to addresses plus subject or text')
    else:
        if text is None:
            text = subject
        elif type(text) == list:
            text = '\n'.join(text)

        try:
            if attachment is None:
                msg = MIMEText(text)
            else:
                msg = MIMEMultipart()
                log('adding attachment')

            if subject is not None:
                msg[mime_constants.SUBJECT_KEYWORD] = subject
            msg[mime_constants.FROM_KEYWORD] = from_address
            msg[mime_constants.TO_KEYWORD] = to_address
            msg[mime_constants.DATE_KEYWORD] = time.strftime('%a, %e %h %Y %T %Z', time.gmtime())

            try:
                if extra_headers is not None:
                    for (name, value) in extra_headers:
                        msg[name] = value
                    log('added extra headers'.format(len(extra_headers)))
            except:
                log(format_exc())

            if attachment is not None:
                msg.attach(MIMEText(text))

                payload = MIMEBase('application', "octet-stream")
                payload.set_payload(attachment)
                encode_base64(payload)
                payload.add_header(
                  'Content-Disposition', 'attachment; filename="%s"' % os.path.basename(filename))
                if payload is not None:
                    msg.attach(payload)

            message = msg.as_string()
        except Exception:
            log(format_exc())

    return message

