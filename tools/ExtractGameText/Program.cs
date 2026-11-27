// Read-only extraction of all current item/menu FMG entries for research.
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;
using System.Xml.Linq;
using SoulsFormats;

if (args.Length != 4)
    throw new ArgumentException("Usage: ExtractGameText <Smithbox> <Game> <MMV mod> <output.json>");
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
var hashes = new SortedDictionary<string,string>();
var all = new SortedDictionary<string,SortedDictionary<string,SortedDictionary<int,string>>>();
foreach(var folder in new[]{"engus","zhocn"}) {
 var tables = new SortedDictionary<string,SortedDictionary<int,string>>();
 foreach(var kind in new[]{"item","menu"}) {
  var path=Path.Combine(mod,"msg",folder,kind+"_dlc01.msgbnd.dcx");hashes[folder+"/"+kind]=Hash(path);
  foreach(var file in BND4.Read(path).Files) {
   var name=Path.GetFileName(file.Name.Replace('\\','/'));
   if(!name.EndsWith(".fmg"))continue;
   var rows=new SortedDictionary<int,string>();
   foreach(var entry in FMG.Read(file.Bytes).Entries)if(!string.IsNullOrWhiteSpace(entry.Text))rows[entry.ID]=entry.Text;
   tables[name]=rows;
  }
 }
 all[folder]=tables;
}
Directory.CreateDirectory(Path.GetDirectoryName(output)!);
using(var stream=File.Create(output))JsonSerializer.Serialize(stream,new{hashes,all});
