"""Load a pinned raw TAE with native relocation and event iteration.

The caller selects an animation and supplies the dispatch activity/time inputs.
Event payloads, format flags and parameter pointers come from the actual file.
This is not a full animation scheduler or behavior VM.
"""
import struct
from native_effect_runtime import OBJ, sha

class NativeTae:
    def __init__(self, runtime, raw, expected_sha, base=0x11000000):
        assert sha(raw)==expected_sha and raw[:4]==b'TAE '
        assert struct.unpack_from('<I',raw,8)[0]==0x1000d
        self.runtime=runtime;self.base=base
        u=runtime.u;u.mem_map(base,(len(raw)+4095)&~4095);u.mem_write(base,raw)
        runtime.invoke(0x27d0f10,[OBJ+0x4000,base,0,0])
        # Current selected assets have one TAE group. Read the native-relocated
        # group/list pointers, not guessed animation body offsets.
        assert struct.unpack('<I',u.mem_read(base+0x18,4))[0]==1
        group=struct.unpack('<Q',u.mem_read(base+0x20,8))[0]
        self.id,count,entries=struct.unpack('<IIQ',u.mem_read(group,16))
        self.animations={}
        for index in range(count):
            id,ptr=struct.unpack('<QQ',u.mem_read(entries+index*16,16))
            assert base<=ptr<base+len(raw) and id not in self.animations
            self.animations[id]=ptr
        self.bank=u.mem_read(base+0x30,1)[0]

    def select(self, animation, event_type):
        c=self.runtime;ctx=OBJ+0xd100;c.u.mem_write(ctx,bytes(0x40))
        for _ in range(10000):
            if not c.invoke(0x27d0400,[self.animations[animation],ctx]):break
            typ=struct.unpack('<I',c.u.mem_read(ctx,4))[0]
            if typ==event_type:
                version=struct.unpack('<H',c.u.mem_read(ctx+0x1a,2))[0]
                assert version==self.bank
                return ctx
        raise AssertionError((animation,event_type,'missing native event'))
