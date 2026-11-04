using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;
using SoulsFormats;

if (args.Length != 4) throw new ArgumentException("Usage: ExtractEffectBehavior <Smithbox> <Game> <MMV mod> <private output.json>");
var smithbox = Path.GetFullPath(args[0]);
var game = Path.GetFullPath(args[1]);
var mod = Path.GetFullPath(args[2]);
var output = Path.GetFullPath(args[3]);
AppDomain.CurrentDomain.AssemblyResolve += (_, r) => Assembly.LoadFrom(Path.Combine(smithbox, new AssemblyName(r.Name).Name + ".dll"));
NativeLibrary.SetDllImportResolver(typeof(BND4).Assembly, (name, _, _) => NativeLibrary.Load(Path.Combine(game, name.EndsWith(".dll") ? name : name + ".dll")));
string Hash(byte[] bytes) => Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
var bundle = File.ReadAllBytes(Path.Combine(mod, "chr/c0000.behbnd.dcx"));
if (Hash(bundle) != "0eab914717c59464b19a0cbff4c67841a92b01aef495812ed2bfa8feba7f5fd5")
    throw new InvalidDataException("Unsupported behavior bundle");
Directory.SetCurrentDirectory(game);
var original = BND4.Read(bundle).Files.Single(f => f.ID == 7000500).Bytes.ToArray();
File.WriteAllBytes(Path.ChangeExtension(output, ".hkx"), original);

// Read metadata only. The installed registry has a different custom-selector
// hash; never deserialize that class into registry objects or rewrite a game file.
var copy = original.ToArray();
var thsh = copy.AsSpan().IndexOf("THSH"u8);
if (thsh < 0) throw new InvalidDataException("Missing type hashes");
var hashLength = (int)(System.Buffers.Binary.BinaryPrimitives.ReadUInt32BigEndian(copy.AsSpan(thsh - 4, 4)) & 0x3fffffff);
copy.AsSpan(thsh + 4, hashLength - 8).Clear();
var serializer = new HKLib.Serialization.hk2018.Binary.HavokBinarySerializer();
var reader = new HKLib.Serialization.hk2018.Binary.Util.HavokBinaryReader(copy);
reader.Position = copy.AsSpan().IndexOf("TYPE"u8) - 4;
var readType = serializer.GetType().GetMethod("ReadTYPE", BindingFlags.NonPublic | BindingFlags.Instance)!;
var types = (IReadOnlyList<HKLib.Reflection.hk2018.HavokType>)readType.Invoke(serializer, new object[] { reader })!;
var hashReader = new HKLib.Serialization.hk2018.Binary.Util.HavokBinaryReader(original);
hashReader.Position = thsh + 4;
var hashes = new Dictionary<int, uint>();
var count = hashReader.ReadHavokVarUInt();
for (ulong i = 0; i < count; i++) hashes[(int)hashReader.ReadHavokVarUInt()] = hashReader.ReadUInt32();
var mismatches = hashes.Where(kv => kv.Value != types[kv.Key].Hash).Select(kv => types[kv.Key].Identity).ToArray();
if (!mismatches.SequenceEqual(new[] { "CustomManualSelectorGenerator" }))
    throw new InvalidDataException("Unexpected registry differences");
var report = new {
    schema = 1, bundleSha256 = Hash(bundle), hkxSha256 = Hash(original),
    registrySha256 = Hash(File.ReadAllBytes(Path.Combine(AppContext.BaseDirectory, "Res/HavokTypeRegistry20180100.xml"))),
    metadataOnly = true, mismatches, originalHashes = hashes,
    types = types.Select(t => t is null ? null : new {
        t.Identity, t.Size, t.Alignment, t.Hash, Parent = t.Parent?.Identity,
        Fields = t.Fields.Select(f => new { f.Name, f.Offset, Type = f.Type.Identity })
    })
};
File.WriteAllText(output, JsonSerializer.Serialize(report));
using var check = JsonDocument.Parse(File.ReadAllBytes(output));
Console.WriteLine($"Validated metadata for {types.Count} types; original HKX saved privately for pointer-checked traversal");
