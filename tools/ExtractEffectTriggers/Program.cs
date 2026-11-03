using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;
using SoulsFormats;
if (args.Length != 4) throw new ArgumentException("Usage: ExtractEffectTriggers <Smithbox> <Game> <MMV mod> <private output.json>");
var smithbox=Path.GetFullPath(args[0]);var game=Path.GetFullPath(args[1]);var mod=Path.GetFullPath(args[2]);var output=Path.GetFullPath(args[3]);
AppDomain.CurrentDomain.AssemblyResolve += (_, r) => Assembly.LoadFrom(Path.Combine(smithbox, new AssemblyName(r.Name).Name+".dll"));
NativeLibrary.SetDllImportResolver(typeof(BND4).Assembly,(name,_,_)=>NativeLibrary.Load(Path.Combine(game,name.EndsWith(".dll")?name:name+".dll")));
Directory.SetCurrentDirectory(game);
string Hash(string path)=>Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();
if (Hash(Path.Combine(mod,"regulation.bin")) != "3305ac374b4da1db440e2b6644bc2c3c0ae96b98df9627f1a0e7a2b06d265c06")
 throw new InvalidDataException("Unsupported regulation hash");
var bundles=new List<object>();
foreach(var path in new[]{"chr/c0000.anibnd.dcx","chr/c0000_a6x.anibnd.dcx"}) {
 var full=Path.Combine(mod,path);var b=BND4.Read(full);var records=new List<object>();
 foreach(var f in b.Files.Where(f=>f.Name.EndsWith(".tae"))) {
  var t=TAE.Read(f.Bytes);
  records.Add(new {f.Name,t.ID,animations=t.Animations.Select(a=>new{a.ID,a.AnimFileName,headerType=a.MiniHeader.Type.ToString(),header=JsonSerializer.Serialize(a.MiniHeader,a.MiniHeader.GetType()),events=a.Events.Select((e,index)=>(e,index)).Where(x=>new[]{66,67,302,331,401}.Contains(x.e.Type)).Select(x=>new{x.index,x.e.Type,x.e.StartTime,x.e.EndTime,hex=Convert.ToHexString(x.e.GetParameterBytes(false))})})});
 }
 bundles.Add(new{path,sha256=Hash(full),taes=records});Console.WriteLine(path+" "+records.Count+" TAE files");
}
using(var stream=File.Create(output)) JsonSerializer.Serialize(stream,new{bundles});
using(var stream=File.OpenRead(output))using(var check=JsonDocument.Parse(stream))Console.WriteLine("Validated JSON");
