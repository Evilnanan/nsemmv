// Read only effect parameters and descriptions from the pinned MMV build.
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;
using System.Xml.Linq;
using SoulsFormats;

if (args.Length != 4)
    throw new ArgumentException("Usage: ExtractEffectDetails <Smithbox> <Game> <MMV mod> <output.json>");
var smithbox = Path.GetFullPath(args[0]);
var game = Path.GetFullPath(args[1]);
var mod = Path.GetFullPath(args[2]);
var output = Path.GetFullPath(args[3]);
AppDomain.CurrentDomain.AssemblyResolve += (_, request) => {
    var file = Path.Combine(smithbox, new AssemblyName(request.Name).Name + ".dll");
    return File.Exists(file) ? Assembly.LoadFrom(file) : null;
};
NativeLibrary.SetDllImportResolver(typeof(BND4).Assembly, (name, _, _) => {
    var file = Path.Combine(game, name.EndsWith(".dll") ? name : name + ".dll");
    return File.Exists(file) ? NativeLibrary.Load(file) : IntPtr.Zero;
});
Directory.SetCurrentDirectory(game);
string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();
var regulation = Path.Combine(mod, "regulation.bin");
var hashes = new SortedDictionary<string, string> { ["regulation.bin"] = Hash(regulation) };
if (hashes["regulation.bin"] != "3305ac374b4da1db440e2b6644bc2c3c0ae96b98df9627f1a0e7a2b06d265c06")
    throw new InvalidDataException("Unsupported regulation hash");
var binder = SFUtil.DecryptNightreignRegulation(regulation);
if (binder.Version != "10350000") throw new InvalidDataException("Unsupported regulation version");
var tables = new SortedDictionary<string, SortedDictionary<int, SortedDictionary<string, double>>>();
foreach (var name in new[] { "AttachEffectParam", "SpEffectParam" }) {
    var defPath = Path.Combine(smithbox, "Assets/PARAM/NR/Defs", name + ".xml");
    hashes["defs/" + name + ".xml"] = Hash(defPath);
    var definition = XDocument.Load(defPath);
    foreach (var field in definition.Root!.Element("Fields")!.Elements("Field").ToArray()) {
        if (10350000UL < ((ulong?)field.Attribute("FirstVersion") ?? 0) ||
            10350000UL >= ((ulong?)field.Attribute("RemovedVersion") ?? ulong.MaxValue)) field.Remove();
        else { field.Attribute("FirstVersion")?.Remove(); field.Attribute("RemovedVersion")?.Remove(); }
    }
    var temp = Path.GetTempFileName();
    try {
        definition.Save(temp);
        var bytes = binder.Files.Single(f => Path.GetFileName(f.Name.Replace('\\', '/')) == name + ".param").Bytes;
        var param = PARAM.Read(bytes);
        param.ApplyParamdef(PARAMDEF.XmlDeserialize(temp));
        var rows = new SortedDictionary<int, SortedDictionary<string, double>>();
        foreach (var row in param.Rows) {
            var values = new SortedDictionary<string, double>();
            foreach (var cell in row.Cells)
                if (cell.Value is not byte[]) {
                    var value = Convert.ToDouble(cell.Value);
                    if (double.IsFinite(value)) values[cell.Def.InternalName] = value;
                }
            rows[row.ID] = values;
        }
        tables[name] = rows;
    } finally { File.Delete(temp); }
}
var texts = new SortedDictionary<string, SortedDictionary<string, SortedDictionary<int, string>>>();
foreach (var (folder, locale) in new[] { ("engus", "en_US"), ("zhocn", "zh_CN") }) {
    var labels = new SortedDictionary<string, SortedDictionary<int, string>>();
    foreach (var kind in new[] { "item", "menu" }) {
        var path = Path.Combine(mod, "msg", folder, kind + "_dlc01.msgbnd.dcx");
        hashes[$"msg/{folder}/{kind}_dlc01.msgbnd.dcx"] = Hash(path);
        var messages = BND4.Read(path);
        foreach (var name in kind == "item" ? new[] { "AttachEffectInfo", "AttachEffectName" } : new[] { "SpEffectInfo", "SpEffectName", "SpEffectCaption" }) {
            var entries = new SortedDictionary<int, string>();
            foreach (var suffix in new[] { "", "_dlc01" }) {
                var file = messages.Files.SingleOrDefault(f => Path.GetFileName(f.Name.Replace('\\', '/')) == $"{name}{suffix}.fmg");
                if (file == null) continue;
                foreach (var entry in FMG.Read(file.Bytes).Entries)
                    if (!string.IsNullOrWhiteSpace(entry.Text)) entries[entry.ID] = entry.Text.Trim();
            }
            labels[name] = entries;
        }
    }
    texts[locale] = labels;
}
Directory.CreateDirectory(Path.GetDirectoryName(output)!);
File.WriteAllText(output, JsonSerializer.Serialize(new { schema = 1, regulationVersion = binder.Version, hashes, tables, texts }));
Console.WriteLine("Extracted effect parameters and descriptions; inputs unchanged.");
