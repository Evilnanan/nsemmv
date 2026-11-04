// Read the actually loaded compiled events; decompiled JS is not evidence.
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;
using SoulsFormats;

if (args.Length != 4)
    throw new ArgumentException("Usage: ExtractEffectEvents <Smithbox> <Game> <MMV mod> <private output.json>");
var smithbox = Path.GetFullPath(args[0]);
var game = Path.GetFullPath(args[1]);
var mod = Path.GetFullPath(args[2]);
var output = Path.GetFullPath(args[3]);
AppDomain.CurrentDomain.AssemblyResolve += (_, r) => Assembly.LoadFrom(Path.Combine(smithbox, new AssemblyName(r.Name).Name + ".dll"));
NativeLibrary.SetDllImportResolver(typeof(EMEVD).Assembly, (name, _, _) => NativeLibrary.Load(Path.Combine(game, name.EndsWith(".dll") ? name : name + ".dll")));
Directory.SetCurrentDirectory(game);
string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();
var regulationHash = Hash(Path.Combine(mod, "regulation.bin"));
if (regulationHash != "3305ac374b4da1db440e2b6644bc2c3c0ae96b98df9627f1a0e7a2b06d265c06")
    throw new InvalidDataException("Unsupported regulation hash");
var files = Directory.GetFiles(Path.Combine(mod, "event"), "*.emevd.dcx").Order().Select(path => {
    var emevd = EMEVD.Read(path);
    return new { path = Path.GetRelativePath(mod, path).Replace('\\', '/'), sha256 = Hash(path),
        events = emevd.Events.Select(e => new { e.ID, e.RestBehavior, e.Parameters,
            instructions = e.Instructions.Select(i => new { i.Bank, i.ID, hex = Convert.ToHexString(i.ArgData) }) }) };
}).ToArray();
var maps = Directory.GetFiles(Path.Combine(mod, "map/mapstudio"), "*.msb.dcx").Order().Select(path => {
    var map = MSB_NR.Read(path);
    return new { path = Path.GetRelativePath(mod, path).Replace('\\', '/'), sha256 = Hash(path),
        enemies = map.Parts.Enemies.Select(e => new { e.EntityData.EntityID, e.Name, e.ModelName }),
        assets = map.Parts.Assets.Select(e => new { e.EntityData.EntityID, e.Name, e.ModelName }),
        interactions = map.Events.ObjActs.Select(e => new { e.Name, e.ObjActPartName, e.ObjActParamId, e.StateType, e.EventFlagID }),
        treasures = map.Events.Treasures.Select(e => new { e.Name, e.TreasurePartName, e.ItemLotID, e.InChest }) };
}).ToArray();
Directory.CreateDirectory(Path.GetDirectoryName(output)!);
using (var stream = File.Create(output)) JsonSerializer.Serialize(stream, new { schema = 1, regulationSha256 = regulationHash, files, maps });
using (var stream = File.OpenRead(output)) using (var check = JsonDocument.Parse(stream)) {
    Console.WriteLine($"Validated {check.RootElement.GetProperty("files").GetArrayLength()} compiled event files");
}
