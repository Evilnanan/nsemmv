"""Execute the pinned font lookup's UTF-16 remapping for every code unit.

Stops before glyph-table access: this checks character selection, not a rendered
game screenshot. No game, user save, or font assets are included in the output.
"""
import argparse
import hashlib
import json
from pathlib import Path

import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_MEM_UNMAPPED
from unicorn.x86_const import UC_X86_REG_RDX, UC_X86_REG_R9, UC_X86_REG_RSP, UC_X86_REG_RIP

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('exe', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
raw = a.exe.read_bytes()
digest = hashlib.sha256(raw).hexdigest()
assert digest == '9545e8732919bb6a63904cb73223641b3c4f9a67869be5722612acca413e8b3a'
pe = pefile.PE(data=raw, fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
u = Uc(UC_ARCH_X86, UC_MODE_64)

def mapped(u, access, address, size, value, user):
    page = address & ~4095
    assert base <= page < base + pe.OPTIONAL_HEADER.SizeOfImage
    u.mem_map(page, 4096)
    u.mem_write(page, pe.get_data(page - base, 4096).ljust(4096, b'\0'))
    return True

u.hook_add(UC_HOOK_MEM_UNMAPPED, mapped)
mapping = {}
for code in range(65536):
    u.reg_write(UC_X86_REG_RSP, 0x20008000)
    u.reg_write(UC_X86_REG_RDX, code)
    u.emu_start(base + 0x13bf850, base + 0x13bf8c9, count=100)
    assert u.reg_read(UC_X86_REG_RIP) == base + 0x13bf8c9
    glyph = u.reg_read(UC_X86_REG_R9)
    if glyph != code:
        mapping[f'{code:04X}'] = f'{glyph:04X}'
assert mapping == {'2472': '0023', '2473': '003F', '3251': '003C', '3252': '003E',
                   '3253': '0025', '3254': 'FF3C', '3255': '00A5'}
a.output.write_text(json.dumps(dict(schema=1, exeSha256=digest, entry='13BF850',
    stopBefore='13BF8C9', testedCodeUnits=65536, mapping=mapping,
    unchangedCodeUnits=65536-len(mapping), gameplayVerified=False), indent=2) + '\n')
print(f'Checked 65536 UTF-16 units: {len(mapping)} font substitutions.')
