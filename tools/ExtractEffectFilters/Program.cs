// Read only the native filter tables and their menu labels from the pinned MMV build.
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;
using System.Xml.Linq;
using SoulsFormats;

if (args.Length != 4)
    throw new ArgumentException("Usage: ExtractEffectFilters <Smithbox> <Game> <MMV mod> <output.json>");
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
var tables = new SortedDictionary<string, List<SortedDictionary<string, int>>>();
foreach (var name in new[] { "AttachEffectFilterParam", "AttachEffectFilterCategoryParam", "AttachEffectFilterSubCategoryParam" }) {
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
        var rows = new List<SortedDictionary<string, int>>();
        foreach (var row in param.Rows) {
            var values = new SortedDictionary<string, int> { ["ID"] = row.ID };
            foreach (var cell in row.Cells)
                if (cell.Value is not byte[]) values[cell.Def.InternalName] = Convert.ToInt32(cell.Value);
            rows.Add(values);
        }
        tables[name] = rows;
    } finally { File.Delete(temp); }
}
var wanted = tables["AttachEffectFilterCategoryParam"].Concat(tables["AttachEffectFilterSubCategoryParam"])
    .Select(row => row["textId"]).Where(id => id >= 0).ToHashSet();
var texts = new SortedDictionary<string, SortedDictionary<int, string>>();
foreach (var (folder, locale) in new[] { ("engus", "en_US"), ("zhocn", "zh_CN") }) {
    var path = Path.Combine(mod, "msg", folder, "menu_dlc01.msgbnd.dcx");
    hashes[$"msg/{folder}/menu_dlc01.msgbnd.dcx"] = Hash(path);
    var menu = BND4.Read(path);
    var labels = new SortedDictionary<int, string>();
    foreach (var suffix in new[] { "", "_dlc01" }) {
        var file = menu.Files.Single(f => Path.GetFileName(f.Name.Replace('\\', '/')) == $"CL_MenuText{suffix}.fmg");
        foreach (var entry in FMG.Read(file.Bytes).Entries)
            if (wanted.Contains(entry.ID) && !string.IsNullOrWhiteSpace(entry.Text)) labels[entry.ID] = entry.Text.Trim();
    }
    if (wanted.Any(id => !labels.ContainsKey(id))) throw new InvalidDataException("Missing filter labels: " + locale);
    texts[locale] = labels;
}
Directory.CreateDirectory(Path.GetDirectoryName(output)!);
File.WriteAllText(output, JsonSerializer.Serialize(new { schema = 1, regulationVersion = binder.Version, hashes, tables, texts }));
Console.WriteLine("Wrote native filter tables and labels; inputs unchanged.");
