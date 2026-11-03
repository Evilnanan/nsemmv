"""Read-only checks against the supported local PC executable. No binary is distributed.

Requires pefile and capstone. This verifies selected instruction sequences, not a
complete decompilation or proof of the entire character save layout.
"""
import argparse
import hashlib
import json
from pathlib import Path
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

EXPECTED = '9545e8732919bb6a63904cb73223641b3c4f9a67869be5722612acca413e8b3a'
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('executable', type=Path)
args = p.parse_args()
raw = args.executable.read_bytes()
if hashlib.sha256(raw).hexdigest() != EXPECTED:
    raise SystemExit('Unsupported executable hash; do not apply these RVAs to another build.')
pe = pefile.PE(data=raw, fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
md = Cs(CS_ARCH_X86, CS_MODE_64)

def instructions(rva, length):
    return [{'rva': hex(i.address-base), 'instruction': f'{i.mnemonic} {i.op_str}'.strip()}
            for i in md.disasm(pe.get_data(rva, length), base+rva)]

checks = {
    'CSAtqGaitemIns.writer': instructions(0x69e940, 0x20),
    'CSAtqGaitemIns.reader_current_body': instructions(0x69e90a, 0x29),
    'CSProGaitemIns.writer': instructions(0x6a1d00, 0x41),
    'InventoryEntry.reader': instructions(0x7541c0, 0x190),
    'EquipInventoryData.writer': instructions(0x1f6780, 0x75),
}
relic = '\n'.join(i['instruction'] for i in checks['CSAtqGaitemIns.writer'])
assert 'mov r8d, 0x48' in relic and 'lea rdx, [rcx + 0x10]' in relic
assert 'jmp qword ptr [rax + 0x18]' in relic
armor = '\n'.join(i['instruction'] for i in checks['CSProGaitemIns.writer'])
assert armor.count('mov r8d, 4') == 2
print(json.dumps({'sha256': EXPECTED, 'image_base': hex(base), 'checks': checks}, indent=2))
