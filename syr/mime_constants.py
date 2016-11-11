'''
    MIME constants.

    Copyright 2014-2016 GoodCrypto
    Last modified: 2016-04-19

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

CONTENT_TYPE_KEYWORD = 'Content-Type'
CONTENT_XFER_ENCODING_KEYWORD = 'Content-Transfer-Encoding'
CONTENT_DISPOSITION_KEYWORD = 'Content-Disposition'

RETURN_PATH_KEYWORD = 'Return-Path'
DELIVERED_TO_KEYWORD = 'Delivered-To'
X_ORIGINAL_TO_KEYWORD = 'X-Original-To'
FROM_KEYWORD = 'From'
TO_KEYWORD = 'To'
CC_KEYWORD = 'Cc'
SUBJECT_KEYWORD = 'Subject'
DATE_KEYWORD = 'Date'


MESSAGE_ID_KEYWORD = 'Message-ID'
MIME_VERSION_KEYWORD = 'Mime-Version'
MIME_VERSION = '1.0'

PRIMARY_TYPE_DELIMITER = '/'
TEXT_PRIMARY_TYPE = 'text'
PLAIN_SUB_TYPE = 'plain'
TEXT_PLAIN_TYPE = '{}{}{}'.format(TEXT_PRIMARY_TYPE, PRIMARY_TYPE_DELIMITER, PLAIN_SUB_TYPE)
HTML_SUB_TYPE = 'html'
TEXT_HTML_TYPE = '{}{}{}'.format(TEXT_PRIMARY_TYPE, PRIMARY_TYPE_DELIMITER, HTML_SUB_TYPE)

MULTIPART_PRIMARY_TYPE = 'multipart'
ENCRYPTED_SUB_TYPE = 'encrypted'
ALTERNATIVE_SUB_TYPE = 'alternative'
MIXED_SUB_TYPE = 'mixed'
SIGNED_SUB_TYPE = 'signed'
MULTIPART_ENCRYPTED_TYPE = '{}{}{}'.format(MULTIPART_PRIMARY_TYPE, PRIMARY_TYPE_DELIMITER, ENCRYPTED_SUB_TYPE)
MULTIPART_ALT_TYPE = '{}{}{}'.format(MULTIPART_PRIMARY_TYPE, PRIMARY_TYPE_DELIMITER, ALTERNATIVE_SUB_TYPE)
MULTIPART_MIXED_TYPE = '{}{}{}'.format(MULTIPART_PRIMARY_TYPE, PRIMARY_TYPE_DELIMITER, MIXED_SUB_TYPE)
MULTIPART_SIGNED_TYPE = '{}{}{}'.format(MULTIPART_PRIMARY_TYPE, PRIMARY_TYPE_DELIMITER, SIGNED_SUB_TYPE)
APPLICATION_TYPE = 'application'
APPLICATION_ALT_TYPE = '{}{}{}'.format(APPLICATION_TYPE, PRIMARY_TYPE_DELIMITER, ALTERNATIVE_SUB_TYPE)
PGP_SUB_TYPE = 'pgp-encrypted'
PGP_TYPE = '{}{}{}'.format(APPLICATION_TYPE, PRIMARY_TYPE_DELIMITER, PGP_SUB_TYPE)
PGP_SIG_SUB_TYPE = 'pgp-signature'
PGP_SIG_TYPE = '{}{}{}'.format(APPLICATION_TYPE, PRIMARY_TYPE_DELIMITER, PGP_SIG_SUB_TYPE)
OCTET_STREAM_SUB_TYPE = 'octet-stream'
OCTET_STREAM_TYPE = '{}{}{}'.format(APPLICATION_TYPE, PRIMARY_TYPE_DELIMITER, OCTET_STREAM_SUB_TYPE)

PROTOCOL_KEYWORD = 'protocol'
CHARSET_KEYWORD = 'charset'
PGP_MIME_VERSION_FIELD = 'Version: 1'

MIME_7BIT = '7BITMIME'
MIME_8BIT = '8BITMIME'
BITS_7 = '7bit'
BITS_8 = '8bit'

QUOTED_PRINTABLE_ENCODING = 'quoted-printable'
BASE64_ENCODING = 'base64'

