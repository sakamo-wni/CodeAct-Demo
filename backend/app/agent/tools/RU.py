#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Python 3 ReUsable module.
#
# Copyright (c) 2018, Weathernews, Inc.
# Copyright (c) 2018, Tsuyoshi Hatakenaka (Tsuyoshi@WNI.COM).
# All Rights Reserved.
#
# $Id: RU.py,v 1.4 2019/10/29 04:19:42 tsuyoshi Exp $
# $Source: /home/cvs/EXPRESS/python-lib/RU/RU.py,v $
#
import copy
import datetime
import io
import re
import struct

#
# 定数
#
CHAR_BIT		= 8

#
# RUヘッダ定数群
#
HEADER_SIGNATURE	= b"WN\n"
HEADER_END_SIGNATURE	= "\x04\x1a"
HEADER_KEYS = [
    "announced", "created", "compress_type",
    "global_id", "category", "data_id",
    "data_name", "data_size",
    "format", "header_comment", "header_version", "revision",
]
HEADER_OPTIONAL_KEYS = [
    "compress_type",
]

#
# RUヘッダクラス
#
class Header(object):
    """
    ReUsable Header class.
    """
    def __init__(self):
        "Initialize this instance."
        self.reset()
        self.encoding = "ascii"

    def __contains__(self, item):
        "Contains."
        return item in self._keys

    def __iter__(self):
        "Return the iterator object."
        self._i = 0
        return self

    def __next__(self):
        "Return the value and forward iterator object."
        if self._i >= len(HEADER_KEYS):
            raise StopIteration()
        key = HEADER_KEYS[self._i]
        self._i += 1
        return key

    def __getattr__(self, name):
        "Get the attribute."
        if name in HEADER_KEYS:
            value = self._keys[name]
        else:
            value = self.__getattribute__(name)
        return value

    def __setattr__(self, name, value):
        "Set the attribute."
        if name in HEADER_KEYS:
            self.set_value(name, value)
        else:
            super(Header, self).__setattr__(name, value)

    def __getitem__(self, key):
        "Get the item value."
        if not type(key) is str:
            raise TypeError("key is not str")
        if not key in HEADER_KEYS:
            raise KeyError("no %s" % key)
        return self._keys[key]

    def __setitem__(self, key, value):
        "Set the item value."
        if not type(key) is str:
            raise TypeError("key is not str")
        if not key in HEADER_KEYS:
            raise KeyError("no %s" % key)
        self.set_value(key, value)

    def dump(self):
        "Dump."
        for key in HEADER_KEYS:
            value = self._keys[key]
            if value is None:
                continue
            decoded_value = str(value)
            if key == "created" or key == "announced":
                decoded_value = value.strftime("%Y/%m/%d %T GMT")
            print("%s=%s" % (key, decoded_value))

    def keys(self):
        "Return the RU header keys."
        return HEADER_KEYS

    def reset(self):
        "Reset the attributes."
        self._keys = {}
        for key in HEADER_KEYS:
            value = ""
            if key == "announced" or key == "created" or key == "compress_type":
                value = None
            elif key == "data_size":
                value = 0
            self._keys[key] = value

    def get_value(self, name):
        "Get the value."
        if name not in HEADER_KEYS:
            raise KeyError("no %s" % name)
        return self._keys[name]

    def set_value(self, name, value):
        "Set the value."
        if name not in HEADER_KEYS:
            raise KeyError("no %s" % name)
        if name == "announced" or name == "created":
            if not type(value) is datetime.datetime:
                raise RuntimeError("%s %s is not datetime" % (name, value))
        elif name == "compress_type":
            if value is not None:
                if type(value) is not str:
                    raise RuntimeError("%s %s is not str" % (name, value))
        elif name == "data_size":
            if type(value) is not int:
                raise RuntimeError("%s %s is not int" % (name, value))
        else:
            if type(value) is not str:
                raise RuntimeError("%s %s is not str" % (name, value))
            if name == "global_id" or name == "category":
                if len(value) != 4:
                    raise RuntimeError("%s %s length != 4" % (name, value))
            elif name == "data_id":
                if len(value) != 8:
                    raise RuntimeError("%s %s length != 8" % (name, value))
        self._keys[name] = value

    def load(self, io_obj, strict = True):
        "Load from the IO object."
        signature = io_obj.read(len(HEADER_SIGNATURE))
        if len(signature) != len(HEADER_SIGNATURE) or \
                signature != HEADER_SIGNATURE:
            raise RuntimeError("no RU header")
        lines = b""
        end_signature = HEADER_END_SIGNATURE.encode(self.encoding)
        while True:
            c = io_obj.read(1)
            if len(c) != 1:
                raise RuntimeError("no end of RU header")
            lines += c
            if len(lines) >= len(end_signature) and \
                    lines[len(lines) - 2:len(lines)] == end_signature:
                break
        # Remove the end of signature
        lines = lines[0:len(lines) - len(end_signature)]

        #
        self._keys = {}
        iter_ = iter(lines.splitlines())
        while True:
            try:
                line = next(iter_).decode(self.encoding)
            except StopIteration:
                break

            while line.endswith("\\"):
                try:
                    line = line[:-1] + next(iter_).decode(self.encoding)
                except StopIteration:
                    raise RuntimeError("unexpected end of the header")
            pos = line.find("=")
            if pos >= 0:
                key = line[0:pos].strip()
                value = line[pos + 1:len(line)].strip()
            else:
                key = line
                value = ""
            if len(key) == 0:
                continue
            if not key in HEADER_KEYS:
                raise RuntimeError("no %s" % key)
            decoded_value = value
            if key == "announced" or key == "created":
                decoded_value = Header.get_time(value)
                if decoded_value is None:
                    raise RuntimeError("%s %s can't parse as time" %
                                       (key, value))
            elif key == "data_size":
                decoded_value = int(value)
            self.set_value(key, decoded_value)

        for key in HEADER_KEYS:
            if not key in self._keys:
                self._keys[key] = None
                if strict and not key in HEADER_OPTIONAL_KEYS:
                    raise RuntimeError("no %s" % key)

    def save(self, io_obj):
        "Save to the IO object"
        io_obj.write(HEADER_SIGNATURE)
        for key in HEADER_KEYS:
            value = self._keys[key]
            if value is None:
                if key in HEADER_OPTIONAL_KEYS:
                    continue
                raise RuntimeError("%s is no value" % key)
            encoded_value = str(value)
            if key == "announced" or key == "created":
                encoded_value = value.strftime("%Y/%m/%d %H:%M:%S GMT")
            elif key == "global_id" or key == "category":
                if len(encoded_value) != 4:
                    raise RuntimeError("%s %s length != 4" % (key,
                                                              encoded_value))
            elif key == "data_id":
                if len(encoded_value) != 8:
                    raise RuntimeError("%s %s length != 8" % (key,
                                                              encoded_value))
            line = "%s=%s\n" % (key, encoded_value)
            io_obj.write(line.encode(self.encoding))
        io_obj.write(HEADER_END_SIGNATURE.encode(self.encoding))

    @classmethod
    def get_time(cls, s):
        "Parse the datetime string."
        m = re.match(r"(\d\d\d\d)/(\d\d)/(\d\d)\s+(\d\d):(\d\d):(\d\d)", s)
        if m is None:
            return None
        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))
        hour = int(m.group(4))
        minute = int(m.group(5))
        second = int(m.group(6))
        time = datetime.datetime(year, month, day, hour, minute, second)

        return time

#
# RUの型定義
#

#
# すべての型のベースクラス
#
class Type(object):
    "RU type base class for all types."
    def __init__(self, name, type_, size = None):
        "Initialize this instance."
        self.name = name
        self.type = type_
        self.size = size
        self.encoding = None
        self.format = None
        self.value = None

    def copy(self):
        "Copy this instance."
        return copy.copy(self)

    def get_name(self):
        "Return the name."
        return self.name

    def get_name_type(self):
        "Return the name and type string."
        if self.name == "":
            r = "%s" % self.type
        else:
            r = "%s:%s" % (self.name, self.type)
        return r

    def get_type(self):
        "Return the type."
        return self.type

    def get_size(self):
        "Return the size."
        return self.size

    def is_array(self):
        "Is array type ?"
        return False

    def is_float(self):
        "Is float type ?"
        return False

    def is_integer(self):
        "Is integer type ?"
        return False

    def is_scalar(self):
        "Is scalar type ?"
        return False

    def is_string(self):
        "Is string type ?"
        return False

    def is_struct(self):
        "Is struct type ?"
        return False

    def read(self, ru, io_obj):
        "Read the value from I/O object."
        if self.format is None:
            raise RuntimeError("%s no pack format" % self.type)
        data = io_obj.read(self.size)
        if len(data) != self.size:
            raise RuntimeError("unexpected EOF at %s" % self.name)
        self.value = struct.unpack(self.format, data)[0]
        if self.is_integer():
            ru._set_array_size(self.name, self.value)

    def write(self, ru, io_obj):
        "Write the value to I/O object."
        if self.format is None:
            raise RuntimeError("%s no pack format" % self.type)
        data = struct.pack(self.format, self.value)
        io_obj.write(data)
        if self.is_integer():
            ru._set_array_size(self.name, self.value)            

#
# RU スカラー型のベースクラス
#
class ScalarType(Type):
    "RU Scalar type base class."
    def __init__(self, name, type_, size):
        "Initialize this instance."
        super(ScalarType, self).__init__(name, type_, size)

    def get_value(self):
        "Get the value."
        return self.value

    def is_scalar(self):
        "Is scalar type ?"
        return True

#
# RU INT型のベースクラス
#
class INTType(ScalarType):
    "RU Integer type base class."
    def __init__(self, name, size):
        "Initialize this instance."
        type_ = "INT%d" % (size * CHAR_BIT)
        super(INTType, self).__init__(name, type_, size)
        self.value = 0

    def is_integer(self):
        "Is integer type ?"
        return True

    def set_value(self, value):
        "Set the value."
        self.value = int(value)

#
# RU UINT型のベースクラス
#
class UINTType(ScalarType):
    "RU Unsigned Integer type base class."
    def __init__(self, name, size):
        "Initialize this instance."
        type_ = "UINT%d" % (size * CHAR_BIT)
        super(UINTType, self).__init__(name, type_, size)
        self.value = 0

    def is_integer(self):
        "Is integer type ?"
        return True

    def set_value(self, value):
        "Set the value."
        self.value = int(value)

#
# RU FLOAT型のベースクラス
#
class FLOATType(ScalarType):
    "RU FLOAT type base class."
    def __init__(self, name, size):
        "Initialize this instance."
        type_ = "FLOAT%d" % (size * CHAR_BIT)
        super(FLOATType, self).__init__(name, type_, size)
        self.value = 0.0

    def is_float(self):
        "Is float type ?"
        return True

    def set_value(self, value):
        "Set the value."
        self.value = float(value)

#
# RU 文字列型のベースクラス
#
class StringType(Type):
    "RU String type base class."
    def __init__(self, name, type_, size = None):
        "Initialize this instance."
        super(StringType, self).__init__(name, type_, size)
        self.value = ""

    def get_name_type(self):
        "Return the name and type."
        if self.size is None:
            r = "%s:%s" % (self.name, self.type)
        else:
            r = "%s:<%s>%s" % (self.name, self.size, self.type)
        return r

    def get_encoding(self, ru = None):
        "Get the encoding."
        encoding = None
        if ru is not None:
            encoding = ru.get_encoding(self.type)
        if encoding is None or encoding == "":
            encoding = self.encoding
            if encoding is None or encoding == "":
                encoding = "ascii"
        return encoding

    def get_value(self):
        "Get the value."
        return self.value

    def is_string(self):
        "Is string type ?"
        return True

    def set_value(self, value):
        "Set the value."
        self.value = str(value)

    def read(self, ru, io_obj):
        "Read the RU string type value from I/O object."
        if self.size is None:
            s = b""
            while True:
                c = io_obj.read(1)
                if len(c) == 0:
                    raise RuntimeError("unexpected EOF at %s" % self.name)
                if c == b"\x00":
                    break
                s += c
        else:
            s = io_obj.read(self.size)
            if len(s) != self.size:
                raise RuntimeError("unexpected EOF at %s" % self.name)

        encoding = self.get_encoding(ru)
        self.value = s.decode(encoding)

    def write(self, ru, io_obj):
        "Write the RU string type value to I/O object."
        encoding = self.get_encoding(ru)
        buf = self.value.encode(encoding)
        if self.size is None:
            io_obj.write(buf)
            io_obj.write(b"\x00")
        else:
            sz = len(buf)
            if sz < self.size:
                buf += b"\x00" * (self.size - sz)
            else:
                buf = buf[0 : self.size]
            io_obj.write(buf)

#
# RU FLOAT32/64型
#
class FLOAT32Type(FLOATType):
    "RU FLOAT32 type."
    def __init__(self, name):
        "Initialize this instance."
        super(FLOAT32Type, self).__init__(name, 4)
        self.format = "!f"

class FLOAT64Type(FLOATType):
    "RU FLOAT64 type."
    def __init__(self, name):
        "Initialize this instance."
        super(FLOAT64Type, self).__init__(name, 8)
        self.format = "!d"

#
# RU INT8/16/32型
#
class INT8Type(INTType):
    "RU INT8 type."
    def __init__(self, name):
        "Initialize this instance."
        super(INT8Type, self).__init__(name, 1)
        self.format = "b"

class INT16Type(INTType):
    "RU INT16 type."
    def __init__(self, name):
        "Initialize this instance."
        super(INT16Type, self).__init__(name, 2)
        self.format = "!h"

class INT32Type(INTType):
    "RU INT32 type."
    def __init__(self, name):
        "Initialize this instance."
        super(INT32Type, self).__init__(name, 4)
        self.format = "!l"

#
# RU UINT8/16/32型
#
class UINT8Type(UINTType):
    "RU UINT8 type."
    def __init__(self, name):
        "Initialize this instance."
        super(UINT8Type, self).__init__(name, 1)
        self.format = "B"

class UINT16Type(UINTType):
    "RU UINT16 type."
    def __init__(self, name):
        "Initialize this instance."
        super(UINT16Type, self).__init__(name, 2)
        self.format = "!H"

class UINT32Type(UINTType):
    "RU UINT32 type."
    def __init__(self, name):
        "Initialize this instance."
        super(UINT32Type, self).__init__(name, 4)
        self.format = "!L"

#
# RU STR/ESTR/JSTR/SSTR/USTR型
#
class STRType(StringType):
    "RU STR type."
    def __init__(self, name):
        "Initialize this instance."
        super(STRType, self).__init__(name, "STR")

class ESTRType(StringType):
    "RU ESTR type."
    def __init__(self, name):
        "Initialize this instance."
        super(ESTRType, self).__init__(name, "ESTR")
        self.encoding = "euc_jp"

class JSTRType(StringType):
    "RU JSTR type."
    def __init__(self, name):
        "Initialize this instance."
        super(JSTRType, self).__init__(name, "JSTR")
        self.encoding = "iso2022_jp"

class SSTRType(StringType):
    "RU SSTR type."
    def __init__(self, name):
        ""
        super(SSTRType, self).__init__(name, "SSTR")
        self.encoding = "shift_jis"

class USTRType(StringType):
    "RU USTR type."
    def __init__(self, name):
        "Initialize this instance."
        super(USTRType, self).__init__(name, "USTR")
        self.encoding = "utf_8"

#
# RU NSTR/NESTR/NJSTR/NSSTR/NUSTR型
#
class NSTRType(StringType):
    "RU NSTR type."
    def __init__(self, name, size):
        "Initialize this instance."
        super(NSTRType, self).__init__(name, "NSTR", size)

class NESTRType(StringType):
    "RU NESTR type."
    def __init__(self, name, size):
        "Initialize this instance."
        super(NESTRType, self).__init__(name, "NESTR", size)
        self.encoding = "euc_jp"

class NJSTRType(StringType):
    "RU NJSTR type."
    def __init__(self, name, size):
        "Initialize this instance."
        super(NJSTRType, self).__init__(name, "NJSTR", size)
        self.encoding = "iso2022_jp"

class NSSTRType(StringType):
    "RU SNSTR type."
    def __init__(self, name, size):
        "Initialize this instance."
        super(NSSTRType, self).__init__(name, "NSSTR", size)
        self.encoding = "shift_jis"


class NUSTRType(StringType):
    "RU NUSTR type."
    def __init__(self, name, size):
        "Initialize this instance."
        super(NUSTRType, self).__init__(name, "NUSTR", size)
        self.encoding = "utf_8"

#
# RU Array型
#
class ArrayType(Type):
    """
    RU Array Type.
    """
    def __init__(self, name, size, member):
        "Initialize this instance."
        super(ArrayType, self).__init__(name, "Array", size)
        self.member = member
        self.value = []

    def __len__(self):
        "Return the length."
        return len(self.value)

    def __iter__(self):
        "Return the iterator object."
        self._i = 0
        return self

    def __next__(self):
        "Return the value and forward iterator object."
        if self._i >= len(self.value):
            raise StopIteration()
        obj = self.value[self._i]
        self._i += 1
        return obj

    def __getitem__(self, key):
        "Get the item value."
        if not type(key) is int:
            raise TypeError("key is not int")
        if key < 0 or key >= len(self.value):
            raise IndexError("%d out of range" % key)
        obj = self.value[key]
        if obj.is_struct() or obj.is_array():
            return obj
        else:
            return obj.get_value()

    def __setitem__(self, key, value):
        "Set the item value."
        if not type(key) is int:
            raise TypeError("key is not int")
        if key < 0 or key >= len(self.value):
            raise IndexError("%d out of range" % key)
        obj = self.value[key]
        if obj.is_struct() or obj.is_array():
            raise RuntimeError("Array or Struct type assignment not supported")
        obj.set_value(value)

    def append(self, value):
        "Append the value."
        if self.member.is_array() or self.member.is_struct():
            raise RuntimeError("Array or Struct type append not supported")
        member = self.member.copy()
        member.set_value(value)
        self.value.append(member)
        
    def copy(self):
        "Copy this array instance."
        return ArrayType(self.name, self.size, self.member.copy())

    def get_name_type(self):
        "Return the name and type."
        if self.size is None:
            r = "%s:+" % self.name
        else:
            r = "%s:{%s}" % (self.name, self.size)
        r += self.member.get_name_type()

        return r

    def get_ref(self, key):
        "Return the reference."
        if not type(key) is int:
            raise TypeError("key is not int")
        if key < 0 or key >= len(self.value):
            raise IndexError("%d out of range" % key)
        obj = self.value[key]
        return obj

    def is_array(self):
        "Is array type ?"
        return True

    def resize(self, size):
        "Resize this array."
        if size <= 0:
            self.value = []
            return
        if size < len(self.value):
            # Shrink down the array.
            while len(self.value) > size:
                self.value.pop(len(self.value) - 1)
        else:
            # Grow up the array.
            while len(self.value) < size:
                member = self.member.copy()
                self.value.append(member)

    def read(self, ru, io_obj):
        "Read the array values from I/O."
        self.value = []
        if self.size is None:
            # unlimit array size for '+'
            array = io_obj.read()
            array_io = io.BytesIO(array)
            while True:
                if array_io.tell() >= len(array):
                    break
                member = self.member.copy()
                member.read(ru, array_io)
                self.value.append(member)
        else:
            if type(self.size) is int:
                size = self.size
            else:
                size = ru._get_array_size(self.size)
            for i in range(size):
                member = self.member.copy()
                member.read(ru, io_obj)
                self.value.append(member)

    def write(self, ru, io_obj):
        "Write the array values to I/O."
        if self.size is not None:
            if type(self.size) is int:
                size = self.size
                if size != len(self.value):
                    raise RuntimeError("%s array size %s expected %s" %
                                       (self.name, len(self.value), size))
            else:
                size = ru._get_array_size(self.size)
                if size != len(self.value):
                    raise RuntimeError("%s array size %s expected %s %s" %
                                       (self.name, len(self.value),
                                        self.size, size))

        for v in self.value:
            v.write(ru, io_obj)

#
# RU Struct型
#
class StructType(Type):
    """
    RU Struct type.
    """
    def __init__(self, name, members = []):
        "Initialize this instance."
        super(StructType, self).__init__(name, "Struct")
        self.members = []
        self.member_by_name = {}
        for member in members:
            if member in self.member_by_name:
                raise RuntimeError("duplicate member %s" % member.name)
            self.members.append(member)
            self.member_by_name[member.name] = member

    def __contains__(self, item):
        "Contains for in."
        return item in self.member_by_name

    def __len__(self):
        "Return the length."
        return len(self.members)

    def __iter__(self):
        "Return the iterator object."
        self._i = 0
        return self

    def __next__(self):
        "Return the member and forward iterator object."
        if self._i >= len(self.members):
            raise StopIteration()
        obj = self.members[self._i]
        self._i += 1
        return obj

    def __getitem__(self, key):
        "Get the item value."
        if not type(key) is str:
            raise TypeError("key is not str")
        if not key in self.member_by_name:
            raise KeyError("no %s" % key)
        obj = self.member_by_name[key]
        if obj.is_array() or obj.is_struct():
            return obj
        else:
            return obj.get_value()

    def __setitem__(self, key, value):
        "Set the item value."
        if not type(key) is str:
            raise TypeError("key is not str")
        if not key in self.member_by_name:
            raise KeyError("no key %s" % key)
        obj = self.member_by_name[key]
        if obj.is_array() or obj.is_struct():
            raise RuntimeError("Array or Struct type assignment not supported")
        obj.set_value(value)

    def copy(self):
        "Copy this struct instance."
        members = []
        for member in self.members:
            members.append(member.copy())
        return StructType(self.name, members)

    def get_name_type(self):
        "Return the name and type."
        r = ""
        if self.name != "/":
            # 名前がない場合は、Array下にあるStruct
            if self.name != "":
                r += "%s:" % self.name
            r += "["
        for i in range(len(self.members)):
            if i != 0:
                r += ","
            r += self.members[i].get_name_type()
        if self.name != "/":
            r += "]"
        return r

    def get_ref(self, key):
        "Return the reference."
        if not type(key) is str:
            raise TypeError("key is not str")
        if not key in self.member_by_name:
            raise KeyError("no %s" % key)
        obj = self.member_by_name[key]
        return obj
        
    def has_member(self, name):
        "Has member ?"
        if name in self.member_by_name:
            return True
        else:
            return False

    def is_struct(self):
        "Is struct type ?"
        return True

    def keys(self):
        "Return the struct member's name."
        return self.member_by_name.keys()

    def is_time(self):
        "Is time struct ?"
        keys = ("year", "mon", "month", "day", "hour", "min", "minute",
                "sec", "second")
        for member in self.members:
            if member.name != "" and not member.name in keys:
                return False
        if not "year" in self.member_by_name:
            return False
        if not "mon" in self.member_by_name and \
                not "month" in self.member_by_name:
            return False
        if not "day" in self.member_by_name:
            return False
        return True

    def get_time(self):
        "Set the datetime."
        if not self.is_time():
            raise RuntimeError("struct is not time")
        year = self.member_by_name["year"].get_value()
        month = None
        mon_keys = ("mon", "month")
        for key in mon_keys:
            if self.has_member(key):
                month = self.member_by_name[key].get_value()
                break
        day = self.member_by_name["day"].get_value()
        hour = minute = second = 0
        if self.has_member("hour"):
            hour = self.member_by_name["hour"].get_value()
        minute_keys = ("min", "minute")
        for key in minute_keys:
            if self.has_member(key):
                minute = self.member_by_name[key].get_value()
                break
        second_keys = ("sec", "second")
        for key in second_keys:
            if self.has_member(key):
                second = self.member_by_name[key].get_value()
                break

        return datetime.datetime(year, month, day, hour, minute, second)

    def set_time(self, value):
        "Set the time."
        if not self.is_time():
            raise RuntimeError("struct is not time")
        self.member_by_name["year"].set_value(value.year)
        mon_keys = ("mon", "month")
        for key in mon_keys:
            if self.has_member(key):
                self.member_by_name[key].set_value(value.month)
        self.member_by_name["day"].set_value(value.day)
        if self.has_member("hour"):
            self.member_by_name["hour"].set_value(value.hour)
        minute_keys = ("min", "minute")
        for key in minute_keys:
            if self.has_member(key):
                self.member_by_name[key].set_value(value.minute)
        second_keys = ("sec", "second")
        for key in second_keys:
            if self.has_member(key):
                self.member_by_name[key].set_value(value.second)

    def read(self, ru, io_obj):
        "Read the struct member's value from I/O."
        if self.name != "/":
            ru._enter_struct()
        for member in self.members:
            member.read(ru, io_obj)
        if self.name != "/":
            ru._leave_struct()

    def write(self, ru, io_obj):
        "Weite the struct member's value to I/O."
        for member in self.members:
            member.write(ru, io_obj)

#
# トークン定数
#
TOK_ERROR	= -1
TOK_END		= 0
TOK_COLON	= 1
TOK_COMMA	= 2
TOK_LBRKT	= 3
TOK_RBRKT	= 4
TOK_LCBRKT	= 5
TOK_RCBRKT	= 6
TOK_LT		= 7
TOK_GT		= 8
TOK_PLUS	= 9
TOK_SYMBOL	= 10
TOK_NUMBER	= 11

#
# 英字/数字/特殊文字
#
ALPHA_CHARS = (
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J",
    "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
    "U", "V", "W", "X", "Y", "Z",
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j",
    "k", "l", "m", "n", "o", "p", "q", "r", "s", "t",
    "u", "v", "w", "x", "y", "z",
    "_",
)

DIGIT_CHARS = (
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
)

SPEC_CHARS = {
    ":" : TOK_COLON, "," : TOK_COMMA, "[" : TOK_LBRKT, "]" : TOK_RBRKT,
    "{" : TOK_LCBRKT, "}" : TOK_RCBRKT, "<" : TOK_LT, ">" : TOK_GT,
    "+" : TOK_PLUS,
}

BUILTIN_SCALAR_TYPE = {
    "FLOAT32" : FLOAT32Type, "FLOAT64" : FLOAT64Type,
    "INT8" : INT8Type, "INT16" : INT16Type, "INT32" : INT32Type,
    "UINT8" : UINT8Type, "UINT16" : UINT16Type, "UINT32" : UINT32Type,
}

BUILTIN_STR_TYPE = {
    "STR" : STRType, "ESTR" : ESTRType, "JSTR" : JSTRType,
    "SSTR" : SSTRType, "USTR" : USTRType,
}

BUILTIN_NSTR_TYPE = {
    "NSTR" : NSTRType, "NESTR" : NESTRType, "NJSTR" : NJSTRType,
    "NSSTR" : NSSTRType, "NUSTR" : NUSTRType,
}

#
# FormatParase class.
#
class FormatParser(object):
    """
    Reusable format string parser.
    """
    def __init__(self, input_ = None):
        "Initialize this instance."
        self.debug = False
        self.init(input_)


    def init(self, input_ = None):
        ""
        self.input = input_
        self._ptr = 0
        self._token = None
        self._value = None
        self._last_token = None
        self._last_value = None
        self._size_members = {}

    def parse(self, input_ = None):
        "Parse."
        if input_ is not None:
            self.init(input_)
        members = self._parse_field_list()
        if members is None or self._token != TOK_END:
            left = self.input[0:self._ptr]
            raise RuntimeError("syntax error at %s" % left)

        root = StructType("/", members)

        return (root, self._size_members)

    def _parse_field_list(self):
        """
        Parse the field_list.
        FIELD-LIST := NAME ':' TYPE { ',' NAME ':' TYPE }
        """
        if self.debug:
            print("enter parse_field_list()")
        first = True
        members = []
        while True:
            if not first:
                tok = self._get_token()
                if tok != TOK_COMMA:
                    self._unget_token()
                    break
            tok = self._get_token()
            if tok != TOK_SYMBOL:
                if self.debug:
                    print("leave parse_field_list() NG")
                return None
            name = self._value
            tok = self._get_token()
            if tok != TOK_COLON:
                if self.debug:
                    print("leave parse_field_list() NG")
                return None
            member = self._parse_type(name)
            if member is None:
                if self.debug:
                    print("leave parse_field_list() NG")
                return None
            members.append(member)
            first = False
        if self.debug:
            print("leave parse_field_list() OK")

        return members

    def _parse_type(self, name, allow_array = True):
        """
        Parse the type.
        TYPE :=	'{' NUMBER | NAME '}' TYPE or
        	'+' TYPE or
                '[' FIELD-LIST ']' or
                BULTIN-TYPE
        """
        if self.debug:
            print("enter parse_type()")
        tok = self._get_token()
        if allow_array and tok == TOK_LCBRKT:
            # '{' NUMBER | NAME '}' TYPE
            tok = self._get_token()
            if tok != TOK_NUMBER and tok != TOK_SYMBOL:
                if self.debug:
                    print("leave parse_type() NG")
                return None
            size_member = self._value
            if tok == TOK_SYMBOL:
                self._size_members[size_member] = True
            tok = self._get_token()
            if tok != TOK_RCBRKT:
                if self.debug:
                    print("leave parse_type() NG")
                return None
            member = self._parse_type("", False)
            if member is None:
                if self.debug:
                    print("leave parse_type() NG")
                return None
            node = ArrayType(name, size_member, member)
        elif allow_array and tok == TOK_PLUS:
            # '+' TYPE
            member = self._parse_type("", False)
            node = ArrayType(name, None, member)
        elif tok == TOK_LBRKT:
            # '[' FIELD-LIST ']'
            members = self._parse_field_list()
            if members is None:
                if self.debug:
                    print("leave parse_type() NG")
                return None
            tok = self._get_token()
            if tok != TOK_RBRKT:
                if self.debug:
                    print("leave parse_type() NG")
                return None
            node = StructType(name, members)
        else:
            self._unget_token()
            node = self._parse_builtin_type(name)
            if node is None:
                if self.debug:
                    print("leave parse_type() NG")
                return None
        return node

    def _parse_builtin_type(self, name):
        """
        Parse the builtin type.
        """
        if self.debug:
            print("enter parse_builtin_type()")
        node = None
        tok = self._get_token()
        if tok == TOK_SYMBOL:
            if self._value in BUILTIN_SCALAR_TYPE:
                factory = BUILTIN_SCALAR_TYPE[self._value]
                node = factory(name)
            elif self._value in BUILTIN_STR_TYPE:
                factory = BUILTIN_STR_TYPE[self._value]
                node = factory(name)
        elif tok == TOK_LT:
            # <NUMBER>STRING-TYPE
            tok = self._get_token()
            if tok != TOK_NUMBER:
                if self.debug:
                    print("leave parse_builtin_type() NG")
                return None
            size = self._value
            tok = self._get_token()
            if tok != TOK_GT:
                if self.debug:
                    print("leave parse_builtin_type() NG")
                return None
            tok = self._get_token()
            if tok == TOK_SYMBOL and self._value in BUILTIN_NSTR_TYPE:
                factory = BUILTIN_NSTR_TYPE[self._value]
                node = factory(name, size)

        if node is None:
            if self.debug:
                print("leave parse_builtin_type() NG")
            return None
        else:
            if self.debug:
                print("leave parse_builtin_type() OK")
            return node

    def _get_token(self):
        "Get a token."
        if self._last_token is not None:
            self._token = self._last_token
            self._value = self._last_value
            self._last_token = None
            self._last_value = None
        else:
            while True:
                c = self._getc()
                if c is None:
                    break
                if c != " " and c != "\t":
                    break
            if c is None:
                self._token = TOK_END
                self._value = None
            elif c in DIGIT_CHARS:
                s = ""
                while c in DIGIT_CHARS:
                    s += c
                    c = self._getc()
                    if c is None:
                        break
                if c is not None:
                    self._ungetc()
                self._token = TOK_NUMBER
                self._value = int(s)
            elif c in ALPHA_CHARS:
                s = c
                while True:
                    c = self._getc()
                    if c is None:
                        break
                    if c not in ALPHA_CHARS and c not in DIGIT_CHARS:
                        break
                    s += c
                if c is not None:
                    self._ungetc()
                self._token = TOK_SYMBOL
                self._value = s
            elif c in SPEC_CHARS:
                self._token = SPEC_CHARS[c]
                self._value = c
            else:
                self._token = TOK_ERROR
                self._value = None

        if self.debug:
            print("get token %d:%s" % (self._token, self._value))

        return self._token

    def _unget_token(self):
        "Unget a token."
        if self.debug and self._last_token is not None:
            print("overwrite last token %d:%s" % (self._last_token,
                                                  self._last_value))
        self._last_token = self._token
        self._last_value = self._value
        if self.debug:
            print("unget token %d:%s" % (self._token, self._value))

    def _getc(self):
        "Get a character."
        if self._ptr >= len(self.input):
            return None
        c = self.input[self._ptr]
        self._ptr += 1
        return c

    def _ungetc(self):
        "Unget a character."
        if self._ptr > 0:
            self._ptr -= 1

#
# RUクラス
#
class RU(object):
    """
    RU class.
    Usage:
    import RU

    for read:
        fp = open("filename", "rb")
        ru = RU.RU()
        root = ru.load(fp)
        fp.close()
        header = ru.get_header()
        root = ru.get_root()
        ...
    for write:
        header = RU.Header()
        ...
        header.format = "..."
        ...
        ru = RU.RU()
        root = ru.create(header)
        ...
        fp = open("filename", "wb")
        ru.save(fp)
        fp.close()
    """
    def __init__(self, header = None):
        "Initialize this instance"
        self.header = None
        self.root = None
        self.encoding = { "STR" : "euc_jp" }
        if header is not None:
            self.create(header)

    def get_header(self):
        "Return the RU heder."
        return self.header

    def get_root(self):
        "Return the root object."
        return self.root

    def create(self, header = None):
        "Create the Reusable."
        if header is not None:
            self.header = header
        parser = FormatParser()
        self.root, size_members = parser.parse(self.header.format)
        self.level = 0
        self.size_members = {}
        for name in size_members.keys():
            self.size_members[name] = {}

        return self.root

    def dump(self):
        "Dump."
        if self.header is not None:
            self.header.dump()
            print("")
        root = self.root
        if root is not None:
            self._dump(root, "")

    def get_encoding(self, str_type):
        "Get the encoding for string."
        encoding = None
        if str_type in self.encoding:
            encoding = self.encoding[str_type]
        else:
            if str_type[0:1] == "N":
                native_str_type = str_type[1:]
                if native_str_type in self.encoding:
                    encoding = self.encoding[native_str_type]
        return encoding

    def set_encoding(self, str_type, encoding):
        "Set the encoding for string."
        native_str_type = str_type
        if str_type[0:1] == "N":
            native_str_type = str_type[1:]
        if encoding is not None:
            self.encoding[native_str_type] = encoding
        else:
            self.encoding.pop(native_str_type, None)

    def load(self, io_obj, strict = True):
        "Load the Reusable from I/O."
        if self.header is None:
            self.header = Header()
        self.header.load(io_obj, strict)
        data_size = self.header["data_size"]
        data_part = io_obj.read(data_size)
        if len(data_part) != data_size:
            raise RuntimeError("unexpected EOF")
        compress_type = self.header["compress_type"]
        if compress_type is not None and compress_type != "":
            if compress_type == "gzip":
                import gzip

                compressed_data_part = data_part
                data_part = gzip.decompress(compressed_data_part)
            elif compress_type == "bzip2":
                import bz2

                compressed_data_part = data_part
                data_part = bz2.decompress(compressed_data_part)
            else:
                raise RuntimeError("no support compress_type %s" %
                                   compress_type)

        body_io = io.BytesIO(data_part)
        parser = FormatParser()
        self.root, size_members = parser.parse(self.header["format"])
        self.level = 0
        self.size_members = {}
        for name in size_members.keys():
            self.size_members[name] = {}

        self.root.read(self, body_io)

        return self.root

    def save(self, io_obj):
        "Save the Reuable to I/O."
        if self.header is None:
            raise RuntimeError("No RU header")

        body_io = io.BytesIO()
        self.root.write(self, body_io)
        body_part = body_io.getvalue()
        write_data = body_part
        compress_type = self.header["compress_type"]
        if compress_type is not None and compress_type != "":
            if compress_type == "gzip":
                import gzip
            
                write_data = gzip.compress(body_part)
            elif compress_type == "bzip2":
                import bz2

                write_data = bz2.compress(body_part)                
            else:
                raise RuntimeError("no support compress_type %s" %
                                   compress_type)
        self.header["data_size"] = len(write_data)
        self.header.save(io_obj)
        io_obj.write(write_data)

    def _dump(self, obj, path):
        "Dump for internal."
        if obj.is_array():
            p = path
            if p != "":
                p += "."
            p += obj.name
            i = 0
            for member in obj:
                pp = "%s[%s]" % (p, i)
                print(pp)
                self._dump(member, pp)
                i += 1
        elif obj.is_struct():
            p = path
            if obj.name != "/" and obj.name != "":
                if p != "":
                    p += "."
                p += obj.name
            if obj.is_time():
                time = obj.get_time()
                print("%s = %s" % (p, time.strftime("%Y/%m/%d %T GMT")))
            else:
                for member in obj:
                    self._dump(member, p)
        else:
            p = path
            if obj.name != "":
                if p != "":
                    p += "."
                p += obj.name
            if obj.is_string():
                print("%s = \"%s\"" % (p, obj.value))
            else:
                print("%s = %s" % (p, str(obj.value)))

    def _enter_struct(self):
        "Enter the struct."
        self.level += 1

    def _leave_struct(self):
        "Leave the struct and remvoe size member's values."
        for name in  self.size_members.keys():
            this = self.size_members[name]
            if self.level in this:
                del this[self.level]
        self.level -= 1

    def _get_array_size(self, name):
        "Get the array memeber's size."
        if not name in self.size_members:
            raise RuntimeError("size member %s is unknown" % name)
        this = self.size_members[name]
        max_level = None
        value = None
        for level in this.keys():
            if max_level is None or level > max_level:
                max_level = level
                value = this[level]
        if value is None:
            raise RuntimeError("size member %s value is unknown" % name)
        return value

    def _set_array_size(self, name, value):
        "Set the array member size value."
        if not name in self.size_members:
            return
        this = self.size_members[name]
        this[self.level] = value

#
#
#
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        path = sys.argv[1]
        fp = open(path, "rb")
        ru = RU()
        ru.load(fp)
        fp.close()
        ru.dump()
