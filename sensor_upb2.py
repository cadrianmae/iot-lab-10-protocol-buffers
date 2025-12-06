from uprotobuf import *


@registerMessage
class TimeMessage(Message):
    _proto_fields=[
        dict(name='hour', type=WireType.Varint, subType=VarintSubType.UInt32, fieldType=FieldType.Required, id=1),
        dict(name='minute', type=WireType.Varint, subType=VarintSubType.UInt32, fieldType=FieldType.Required, id=2),
        dict(name='second', type=WireType.Varint, subType=VarintSubType.UInt32, fieldType=FieldType.Required, id=3),
    ]

@registerMessage
class SensorreadingMessage(Message):
    _proto_fields=[
        dict(name='publisher_id', type=WireType.Length, subType=LengthSubType.String, fieldType=FieldType.Required, id=1),
        dict(name='temperature', type=WireType.Bit32, subType=FixedSubType.Float, fieldType=FieldType.Required, id=2),
        dict(name='time', type=WireType.Length, subType=LengthSubType.Message, fieldType=FieldType.Required, id=3, mType='.Time'),
    ]
