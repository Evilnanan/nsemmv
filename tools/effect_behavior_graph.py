"""Read selected references from a pinned Havok tagfile without registry objects.

Every reference read must have a PTCH entry and point to an in-bounds ITEM.
Only reviewed generator edges are followed; this is not a behavior VM.
"""
import json
import struct
from pathlib import Path
from native_effect_runtime import sha


class BehaviorGraph:
    def __init__(self, snapshot):
        snapshot = Path(snapshot)
        self.metadata = json.loads(snapshot.read_text())
        self.raw = snapshot.with_suffix('.hkx').read_bytes()
        assert self.metadata['schema'] == 1 and self.metadata['metadataOnly']
        assert sha(self.raw) == self.metadata['hkxSha256']
        assert self.metadata['bundleSha256'] == '0eab914717c59464b19a0cbff4c67841a92b01aef495812ed2bfa8feba7f5fd5'
        assert self.metadata['mismatches'] == ['CustomManualSelectorGenerator']
        self.types = self.metadata['types']
        chunks = {}

        def walk(start, end):
            while start < end:
                size = struct.unpack_from('>I', self.raw, start)[0]
                length = size & 0x3fffffff
                tag = self.raw[start + 4:start + 8].decode()
                assert length >= 8 and start + length <= end
                chunks[tag] = (start + 8, start + length)
                if not size & 0x40000000:
                    walk(start + 8, start + length)
                start += length
            assert start == end

        walk(0, len(self.raw))
        self.data = self.raw[slice(*chunks['DATA'])]
        raw_items = self.raw[slice(*chunks['ITEM'])]
        assert len(raw_items) % 12 == 0
        self.items = [struct.unpack_from('<III', raw_items, i) for i in range(0, len(raw_items), 12)]
        self.patches = {}
        pos, end = chunks['PTCH']
        while pos < end:
            typ, count = struct.unpack_from('<II', self.raw, pos)
            pos += 8
            for _ in range(count):
                offset = struct.unpack_from('<I', self.raw, pos)[0]
                assert offset not in self.patches and offset + 8 <= len(self.data)
                self.patches[offset] = typ
                pos += 4
        assert pos == end

    def item(self, index):
        assert 0 < index < len(self.items)
        typ, offset, count = self.items[index]
        typ = self.types[typ & 0xffffff]
        end = offset + typ['Size'] * count
        assert end <= len(self.data)
        return typ, offset, count

    def reference(self, index, field):
        typ, offset, count = self.item(index)
        assert count == 1
        definition = next(f for f in typ['Fields'] if f['Name'] == field)
        position = offset + definition['Offset']
        assert position in self.patches, (index, field, position)
        assert self.types[self.patches[position]]['Identity'] == definition['Type']
        ref = struct.unpack_from('<Q', self.data, position)[0]
        self.item(ref)
        return ref

    def string(self, index):
        typ, offset, count = self.item(index)
        assert typ['Identity'] == 'char' and self.data[offset + count - 1] == 0
        return self.data[offset:offset + count - 1].decode()

    def name(self, index):
        typ, _, _ = self.item(index)
        if not any(f['Name'] == 'name' for f in typ['Fields']):
            return None
        return self.string(self.reference(index, 'name'))

    def state(self, name):
        matches = [i for i, (typ, _, count) in enumerate(self.items) if typ and count == 1
                   and self.types[typ & 0xffffff]['Identity'] == 'hkbStateMachine::StateInfo'
                   and self.name(i) == name]
        assert len(matches) == 1, (name, matches)
        index = matches[0]
        generator = self.reference(index, 'generator')
        typ, _, _ = self.item(generator)
        assert typ['Identity'] == 'CustomManualSelectorGenerator'
        array = self.reference(generator, 'generators')
        element_type, offset, count = self.item(array)
        assert element_type['Identity'] == 'T*<hkbGenerator>' and element_type['Size'] == 8
        assert count == 1
        assert self.types[self.patches[offset]]['Identity'] == element_type['Identity']
        clip = struct.unpack_from('<Q', self.data, offset)[0]
        clip_type, _, clip_count = self.item(clip)
        assert clip_type['Identity'] == 'hkbClipGenerator' and clip_count == 1
        animation = self.string(self.reference(clip, 'animationName'))
        return dict(state=name, stateItem=index, generator=self.name(generator), generatorItem=generator,
                    arrayItem=array, clip=self.name(clip), clipItem=clip, animation=animation)

    def children(self, index):
        array = self.reference(index, 'generators')
        typ, offset, count = self.item(array)
        assert typ['Identity'] == 'T*<hkbGenerator>' and typ['Size'] == 8
        result = []
        for i in range(count):
            position = offset + i * 8
            assert self.types[self.patches[position]]['Identity'] == typ['Identity']
            child = struct.unpack_from('<Q', self.data, position)[0]
            self.item(child)
            result.append(child)
        return result

    def selector_binding(self, index):
        """Resolve a reviewed manual-selector binding to its graph variable name."""
        binding_set = self.reference(index, 'variableBindingSet')
        array = self.reference(binding_set, 'bindings')
        typ, offset, count = self.item(array)
        assert typ['Identity'] == 'hkbVariableBindingSet::Binding' and count == 1
        assert typ['Size'] == 40
        fields = {f['Name']: f['Offset'] for f in typ['Fields']}
        assert fields['memberPath'] == 0 and fields['variableIndex'] == 28
        assert self.types[self.patches[offset]]['Identity'] == 'hkStringPtr'
        member = self.string(struct.unpack_from('<Q', self.data, offset)[0])
        assert member == 'selectedGeneratorIndex'
        variable = struct.unpack_from('<i', self.data, offset + 28)[0]
        string_sets = [i for i, (t, _, n) in enumerate(self.items) if t and n == 1 and
                       self.types[t & 0xffffff]['Identity'] == 'hkbBehaviorGraphStringData']
        assert len(string_sets) == 1
        names = self.reference(string_sets[0], 'variableNames')
        nt, no, nc = self.item(names)
        assert nt['Identity'] == 'hkStringPtr' and nt['Size'] == 8 and 0 <= variable < nc
        position = no + variable * 8
        assert self.types[self.patches[position]]['Identity'] == 'hkStringPtr'
        name = self.string(struct.unpack_from('<Q', self.data, position)[0])
        return dict(selector=index, bindingSet=binding_set, binding=array, member=member,
                    variable=variable, name=name, stringSet=string_sets[0], names=names)

    def blender_children(self, index):
        """Resolve reviewed blender-child pointers and their generator references."""
        typ, _, count = self.item(index)
        assert typ['Identity'] == 'hkbBlenderGenerator' and count == 1
        array = self.reference(index, 'children')
        typ, offset, count = self.item(array)
        assert typ['Identity'] == 'T*<hkbBlenderGeneratorChild>' and typ['Size'] == 8
        result = []
        for i in range(count):
            position = offset + i * 8
            assert self.types[self.patches[position]]['Identity'] == typ['Identity']
            child = struct.unpack_from('<Q', self.data, position)[0]
            ct, _, cn = self.item(child)
            assert ct['Identity'] == 'hkbBlenderGeneratorChild' and cn == 1
            result.append(dict(child=child, generator=self.reference(child, 'generator')))
        return result
