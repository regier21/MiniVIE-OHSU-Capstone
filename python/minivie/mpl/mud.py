
def encode_mud_message(msgId, msgPayload):
    MSG_LENGTH_FIELD_BYTES = 2;
    MSD_ID_FIELD_BYTES = 1;
    MSG_CHECKSUM_FIELD_BYTES = 1;

    msgLengthField = MSD_ID_FIELD_BYTES + len(msgPayload) + MSG_CHECKSUM_FIELD_BYTES; # 'uint16'
    