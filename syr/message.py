#!/usr/bin/env python
'''
    Prepare a MIME message.
    
    Copyright 2015 GoodCrypto
    Last modified: 2015-04-10

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import os, time
from email.Encoders import encode_base64
from email.mime.text import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from traceback import format_exc

from syr import mime_constants
from syr.log import get_log

log = get_log()


def prep_mime_message(from_address, to_address, subject, text=None, attachment=None, filename=None):
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

