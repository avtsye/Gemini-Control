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

class BridgeHost {
 static readonly JavaScriptSerializer Json=new JavaScriptSerializer();
 static readonly Dictionary<string,string> Apps=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase){
  {"notepad","notepad.exe"},{"calculator","calc.exe"},{"explorer","explorer.exe"},{"paint","mspaint.exe"}
 };
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
 static object Handle(Dictionary<string,object> data){
  object id=Get(data,"id");string command=Str(data,"command");
  if(command=="ping")return new {id=id,ok=true,message="Gemini Control Bridge 0.2.0"};
  if(command=="list_apps")return new {id=id,ok=true,apps=new string[]{"notepad","calculator","explorer","paint"}};
  if(command=="draw_paint")return Draw(data,id);
  if(command=="open_app"){
   string app=Str(data,"app"),exe;
   if(!Apps.TryGetValue(app,out exe))return new {id=id,ok=false,error="Application not allowlisted"};
   Process.Start(new ProcessStartInfo(exe){UseShellExecute=false});
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