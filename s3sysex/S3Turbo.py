S3Functions = {
    # FILE FUNCTIONS  FILE_F
    "F_DHDR"                 : (0x0, 0x01, True),  # FILE DUMP HEADER
    "F_DPKT"                 : (0x0, 0x02, True),  # FILE DUMP DATA BLOCK
    "F_DREQ"                 : (0x0, 0x03, True),  # FILE DUMP REQUEST
    "DIR_HDR"                : (0x0, 0x00, True),  # FILE DIRECTORY HEADER
    "DIR_DRQ"                : (0x0, 0x04, True),  # FILE DIRECTORY REQUEST
    "F_ERR"                  : (0x0, 0x7B, False), # FILE ERROR
    # EDIT FUNCTIONS  EDIT_F
    "PAR_REQ"                : (0x2, 0x02, True),  # EDIT PARAMETER REQUEST
    "PAR_ASW"                : (0x2, 0x04, True),  # EDIT PARAMETER ANSWER
    "PAR_SND"                : (0x2, 0x03, True),  # EDIT PARAMETER SEND+REQUEST
    "EXECUTE"                : (0x2, 0x05, True),  # EDIT EXECUTE
    "_UPDATE"                : (0x2, 0x06, False), # EDIT UPDATE
    # DEVICE COMMAND  DEVICE_CMD
    "STAT_REQUEST"           : (0x5, 0x00, False), # STATUS REQUEST
    "STAT_ANSWER"            : (0x5, 0x01, True),  # STATUS ANSWER
    "BANK_PERF_CHG"          : (0x5, 0x02, False), # BANK PERFORMANCE CHANGE
    "PREPARE_soundAccess"    : (0x5, 0x03, False), # PREPARE SOUND ACCESS
    "UNPREPARE_soundAccess"  : (0x5, 0x04, False), # UNPREPARE SOUND ACCESS
    "PREPARE_bankAccess"     : (0x5, 0x05, False), # PREPARE BANK ACCESS
    "UNPREPARE_bankAccess"   : (0x5, 0x06, False), # UNPREPARE BANK ACCESS
    "PREPARE_effectAccess"   : (0x5, 0x07, False), # PREPARE EFFECT ACCESS
    "UNPREPARE_effectAccess" : (0x5, 0x08, False), # UNPREPARE EFFECT ACCESS
    "PREPARE_generalAccess"  : (0x5, 0x09, False), # PREPARE GENERAL ACCESS
    "UNPREPARE_generalAccess": (0x5, 0x0A, False), # UNPREPARE GENERAL ACCESS
    "PREPARE_StyleAccess"    : (0x5, 0x18, False), # PREPARE STYLE ACCESS
    "UNPREPARE_StyleAccess"  : (0x5, 0x19, False), # UNPREPARE STYLE ACCESS
    "DATA_HEADER"            : (0x5, 0x0C, True),  # DATA DUMP HEADER
    "DATA_DUMP"              : (0x5, 0x0D, True),  # DATA DUMP
    "DELETE"                 : (0x5, 0x0E, True),  # DELETE
    "DIR_REQUEST"            : (0x5, 0x0F, True),  # DIRECTORY REQUEST
    "DIR_ANSWER"             : (0x5, 0x10, True),  # DIRECTORY ANSWER
    "DATA_REQUEST"           : (0x5, 0x0B, True),  # DATA_REQUEST
    "MESSAGECAPTUREON"       : (0x5, 0x11, False), # MESSAGE CAPTURE ON
    "MESSAGECAPTUREOFF"      : (0x5, 0x12, False), # MESSAGE CAPTURE OFF
    "MESSAGESEND"            : (0x5, 0x13, True),  # MESSAGE SEND
    "MESSAGEANSWER"          : (0x5, 0x14, False), # MESSAGE ANSWER
    "ENABLEEDITUPDATE"       : (0x5, 0x15, False), # ENABLE EDIT UPDATE
    "DISABLEEDITUPDATE"      : (0x5, 0x16, False), # DISABLE EDIT UPDATE
    "D_ERR"                  : (0x5, 0x7B, False), # DEVICE ERROR
    "PUT_KEY"                : (0x5, 0x17, False), # WRITE KEY
    # EXTRA
    "F_WAIT"                 : (0x0, 0x7C, False), # WAIT
    "F_CANCEL"               : (0x0, 0x7D, False), # CANCEL
    "F_NACK"                 : (0x0, 0x7E, False), # NACK
    "F_ACK"                  : (0x0, 0x7F, False), # ACK
    "D_WAIT"                 : (0x5, 0x7C, False), # DEVICE WAIT
    "D_CANCEL"               : (0x5, 0x7D, False), # DEVICE CANCEL
    "D_NACK"                 : (0x5, 0x7E, False), # DEVICE NACK
    "D_ACK"                  : (0x5, 0x7F, False), # DEVICE ACK
    }

# Tries to match message to S3 function
def S3FunctionName(msg):
    func    = (msg[2] >> 4)
    subfunc = msg[3]
    for k,v in S3Functions.iteritems():
        if v[:2] == (func,subfunc):
            return k
    return None

# not used but defined in manual
class S3HandshakeMessage(object):
    @staticmethod
    def WAIT(function,chan=0,ownchan=0):
        return S3HandshakeMessage.Generate(function,chan,ownchan,0x7c)

    @staticmethod
    def CANCEL(function,chan=0,ownchan=0):
        return S3HandshakeMessage.Generate(function,chan,ownchan,0x7d)

    @staticmethod
    def NACK(function,chan=0,ownchan=0):
        return S3HandshakeMessage.Generate(function,chan,ownchan,0x7e)

    @staticmethod
    def ACK(function,chan=0,ownchan=0):
        return S3HandshakeMessage.Generate(function,chan,ownchan,0x7f)

    @staticmethod
    def Generate(function,chan,ownchan,command):
        fun, subfun = S3Functions[function]
        return [ 0xF0, 0x2F, fun << 4 | chan, subfun, command, ownchan, 0xF7 ]
