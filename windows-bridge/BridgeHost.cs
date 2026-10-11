using System;
using System.IO;
using System.Text;
using System.Diagnostics;
using System.Collections;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using System.Drawing;
using System.Drawing.Imaging;
using System.Drawing.Drawing2D;
using System.Runtime.InteropServices;
using System.Windows.Forms;

class BridgeHost {
 static readonly JavaScriptSerializer Json=new JavaScriptSerializer();
 static readonly Dictionary<string,string> Apps=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase){
  {"notepad","notepad.exe"},{"calculator","calc.exe"},{"explorer","explorer.exe"},{"paint","mspaint.exe"}
 };
 static readonly string StateDir=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"GeminiControl");
 static string FlagPath {get{return Path.Combine(StateDir,"enabled.flag");}}
 static string LogPath {get{return Path.Combine(StateDir,"activity.log");}}
 static bool Enabled(){Directory.CreateDirectory(StateDir);return !File.Exists(FlagPath)||File.ReadAllText(FlagPath).Trim()!="off";}
 static void Audit(string action,string result){try{Directory.CreateDirectory(StateDir);File.AppendAllText(LogPath,DateTime.Now.ToString("s")+" "+action+" "+result+Environment.NewLine);}catch{}}
 static byte[] ReadExact(Stream s,int n){byte[] b=new byte[n];int p=0;while(p<n){int c=s.Read(b,p,n-p);if(c<=0)return null;p+=c;}return b;}
 static void Send(Stream s,object o){byte[] b=Encoding.UTF8.GetBytes(Json.Serialize(o));byte[] l=BitConverter.GetBytes(b.Length);s.Write(l,0,4);s.Write(b,0,b.Length);s.Flush();}
 static object Get(IDictionary<string,object> d,string key){object o;return d.TryGetValue(key,out o)?o:null;}
 static int Coord(IDictionary<string,object> d,string k,int fallback=0){object v=Get(d,k);if(v==null)return fallback;double n=Convert.ToDouble(v,System.Globalization.CultureInfo.InvariantCulture);if(double.IsNaN(n)||n < -2000||n > 4000)throw new ArgumentException("Invalid coordinate");return (int)n;}
 static string Str(IDictionary<string,object> d,string k){return Convert.ToString(Get(d,k)??"");}
 static Color ParseColor(string s,Color fallback){
  if(string.IsNullOrEmpty(s))return fallback;
  if(s.Length!=7||s[0]!='#')throw new ArgumentException("Color must be #RRGGBB");
  int n; if(!int.TryParse(s.Substring(1),System.Globalization.NumberStyles.HexNumber,null,out n))throw new ArgumentException("Invalid color");
  return Color.FromArgb((n>>16)&255,(n>>8)&255,n&255);
 }
 static object Draw(IDictionary<string,object> request,object id){
  object raw=Get(request,"shapes");IList list=raw as IList;
  if(list==null||list.Count<1||list.Count>80)throw new ArgumentException("1..80 shapes required");
  string destination=Path.Combine(Path.GetTempPath(),"GeminiControl");
  Directory.CreateDirectory(destination);
  string output=Path.Combine(destination,"drawing-"+DateTime.UtcNow.ToString("yyyyMMdd-HHmmss-fff")+".png");
  using(var image=new Bitmap(1000,700))
  using(var g=Graphics.FromImage(image)){
   g.SmoothingMode=SmoothingMode.AntiAlias;g.Clear(Color.White);
   foreach(object item in list){
    var shape=item as IDictionary<string,object>;if(shape==null)throw new ArgumentException("Invalid shape");
    string kind=Str(shape,"kind");
    Color fill=ParseColor(Str(shape,"fill"),Color.SteelBlue);
    int x=Coord(shape,"x"),y=Coord(shape,"y"),w=Coord(shape,"w",100),h=Coord(shape,"h",100);
    if(w<0||h<0||w>2000||h>2000)throw new ArgumentException("Invalid shape size");
    using(var brush=new SolidBrush(fill)){
     if(kind=="rect")g.FillRectangle(brush,x,y,w,h);
     else if(kind=="ellipse")g.FillEllipse(brush,x,y,w,h);
     else if(kind=="line"){int x2=Coord(shape,"x2"),y2=Coord(shape,"y2");using(var pen=new Pen(fill,Math.Max(1,Math.Min(25,Coord(shape,"width",4)))))g.DrawLine(pen,x,y,x2,y2);}
     else if(kind=="triangle"){Point[] pts={new Point(x+w/2,y),new Point(x+w,y+h),new Point(x,y+h)};g.FillPolygon(brush,pts);}
     else throw new ArgumentException("Unsupported shape kind");
    }
   }
   image.Save(output,ImageFormat.Png);
  }
  Process.Start(new ProcessStartInfo("mspaint.exe",String.Concat("\"",output,"\"")){UseShellExecute=false});
  return new {id=id,ok=true,message="Drawing created and opened in Paint",file=output};
 }

 static readonly string Workspace=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"GeminiControl-Workspace");
 static string SafeFile(IDictionary<string,object> req){
  string name=Str(req,"name");
  if(name.Length<1||name.Length>100||name=="."||name==".."||name.IndexOfAny(Path.GetInvalidFileNameChars())>=0||name.Contains("/")||name.Contains("\\")||name.StartsWith("."))throw new ArgumentException("Invalid filename");
  string ext=Path.GetExtension(name).ToLowerInvariant();
  if(!new HashSet<string>(StringComparer.OrdinalIgnoreCase){".txt",".md",".json",".csv",".html",".css",".js",".ts",".py"}.Contains(ext))throw new ArgumentException("File extension not permitted");
  Directory.CreateDirectory(Workspace);return Path.Combine(Workspace,name);
 }
 static object Files(IDictionary<string,object> request,object id,string cmd){
  Directory.CreateDirectory(Workspace);
  if(cmd=="list_files"){var names=new List<string>();foreach(string p in Directory.GetFiles(Workspace)){string n=Path.GetFileName(p);if(n.Length<101&&!n.StartsWith("."))names.Add(n);}return new{id=id,ok=true,files=names,folder=Workspace};}
  string path=SafeFile(request);
  if(cmd=="read_file"){if(!File.Exists(path))return new{id=id,ok=false,error="File not found"};if(new FileInfo(path).Length>100000)return new{id=id,ok=false,error="File too large"};return new{id=id,ok=true,name=Path.GetFileName(path),content=File.ReadAllText(path,Encoding.UTF8)};}
  if(cmd=="write_file"){
   string content=Str(request,"content");if(content.Length>50000)throw new ArgumentException("Content exceeds 50k characters");
   if(File.Exists(path)){
    string dir=Path.Combine(Workspace,".gemini-control-backups");Directory.CreateDirectory(dir);
    File.Copy(path,Path.Combine(dir,DateTime.UtcNow.ToString("yyyyMMdd-HHmmss-fff")+"-"+Path.GetFileName(path)),false);
   }
   File.WriteAllText(path,content,new UTF8Encoding(false));Audit("write_file",Path.GetFileName(path));return new{id=id,ok=true,name=Path.GetFileName(path),folder=Workspace,message="File saved with backup"};
  }
  return new{id=id,ok=false,error="Unknown file operation"};
 }

 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h,StringBuilder sb,int cap);
 [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] static extern bool IsWindow(IntPtr h);
 [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h,out uint pid);
 [DllImport("user32.dll")] static extern bool EnumWindows(EnumWindowProc callback,IntPtr state);
 delegate bool EnumWindowProc(IntPtr h,IntPtr state);
 static readonly Dictionary<string,string> AllowedProcesses=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase) {
  {"notepad","notepad"},{"calculator","CalculatorApp"},{"explorer","explorer"},{"paint","mspaint"}
 };
 static string Title(IntPtr h){var sb=new StringBuilder(260);GetWindowText(h,sb,sb.Capacity);return sb.ToString();}
 static bool AllowedWindow(IntPtr h){
  if(h==IntPtr.Zero||!IsWindow(h)||!IsWindowVisible(h))return false;
  uint pid;GetWindowThreadProcessId(h,out pid);
  try{using(var p=Process.GetProcessById((int)pid)){foreach(var name in AllowedProcesses.Values)if(string.Equals(p.ProcessName,name,StringComparison.OrdinalIgnoreCase))return true;}}catch{}
  return false;
 }
 static object Windows(object id){
  var items=new List<object>();EnumWindows((h,x)=>{if(AllowedWindow(h)&&Title(h).Length>0&&items.Count<30)items.Add(new{handle=h.ToInt64().ToString(),title=Title(h)});return true;},IntPtr.Zero);
  return new{id=id,ok=true,windows=items};
 }
 static object TypeText(IDictionary<string,object> data,object id){
  string str=Str(data,"text");if(str.Length<1||str.Length>5000)throw new ArgumentException("Text length invalid");
  long handle;if(!long.TryParse(Str(data,"handle"),out handle))throw new ArgumentException("Invalid window handle");
  IntPtr h=new IntPtr(handle);
  if(!AllowedWindow(h))throw new ArgumentException("Window not allowlisted or no longer exists");
  // The user chose this allowlisted window and approved the action in Chrome.
  // Activate the selected window and verify it before sending any characters.
  SetForegroundWindow(h);
  System.Threading.Thread.Sleep(250);
  if(GetForegroundWindow()!=h)return new{id=id,ok=false,error="Could not focus the selected application"};
  // Clipboard paste is intentionally avoided to protect clipboard data.
  foreach(char c in str){
   if(c=='\r')continue;
   if(c=='\n'){SendKeys.SendWait("{ENTER}");continue;}
   if(char.IsControl(c))continue;
   SendKeys.SendWait(c=='{'?"{{}":c=='}'?"{}}":c=='+'?"{+}":c=='^'?"{^}":c=='%'?"{%}":c=='~'?"{~}":c=='('?"{(}":c==')'?"{)}":c.ToString());
  }
  Audit("type_text","approved_window");return new{id=id,ok=true,message="Text sent to active approved application"};
 }

 static object Handle(Dictionary<string,object> data){
  object id=Get(data,"id");string command=Str(data,"command");
  if(command=="ping"||command=="status")return new {id=id,ok=true,enabled=Enabled(),message="Gemini Control Bridge 0.3.0"};
  if(command=="set_enabled"){string value=Str(data,"enabled");if(value!="on"&&value!="off")return new{id=id,ok=false,error="Expected on/off"};Directory.CreateDirectory(StateDir);File.WriteAllText(FlagPath,value);Audit("set_enabled",value);return new{id=id,ok=true,enabled=Enabled()};}
  if(command=="recent_log"){string[] lines=File.Exists(LogPath)?File.ReadAllLines(LogPath):new string[0];int start=Math.Max(0,lines.Length-30);var recent=new List<string>();for(int i=start;i<lines.Length;i++)recent.Add(lines[i]);return new{id=id,ok=true,lines=recent};}
  if(!Enabled())return new{id=id,ok=false,error="Bridge is disabled. Enable it in the control panel."};
  if(command=="list_apps")return new {id=id,ok=true,apps=new string[]{"notepad","calculator","explorer","paint"}};
  if(command=="inspect_controls")return new{id=id,ok=true,controls=AccessibleWindows.Inspect()};
  if(command=="click_control"){
   int index=Coord(data,"index",-1);string expected=Str(data,"label");
   if(expected.Length<1||expected.Length>100)throw new ArgumentException("Missing control label");
   string result=AccessibleWindows.Activate(index,expected);Audit("click_control",result);return new{id=id,ok=true,message=result};
  }
  if(command=="list_windows")return Windows(id);
  if(command=="type_text")return TypeText(data,id);
  if(command=="list_files"||command=="read_file"||command=="write_file")return Files(data,id,command);
  if(command=="draw_paint"){Audit(command,"approved");return Draw(data,id);}
  if(command=="open_app"){
   string app=Str(data,"app"),exe;
   if(!Apps.TryGetValue(app,out exe))return new {id=id,ok=false,error="Application not allowlisted"};
   Audit("open_app",app);Process.Start(new ProcessStartInfo(exe){UseShellExecute=false});
   return new {id=id,ok=true,message="Launched "+app};
  }
  return new {id=id,ok=false,error="Unsupported command"};
 }
 static void Main(){
  Stream input=Console.OpenStandardInput(),output=Console.OpenStandardOutput();
  while(true){
   byte[] len=ReadExact(input,4);if(len==null)break;int size=BitConverter.ToInt32(len,0);
   if(size<1||size>65536)break;byte[] raw=ReadExact(input,size);if(raw==null)break;
   try{Send(output,Handle(Json.Deserialize<Dictionary<string,object>>(Encoding.UTF8.GetString(raw))));}
   catch(Exception e){Send(output,new {ok=false,error=e.GetType().Name+": "+e.Message});}
  }
 }
}