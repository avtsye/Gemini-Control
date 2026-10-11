using System;
using System.IO;
using System.Text;
using System.Diagnostics;
using System.Collections.Generic;
using System.Web.Script.Serialization;
class BridgeHost {
  static readonly JavaScriptSerializer Json = new JavaScriptSerializer();
  static readonly Dictionary<string,string> Apps = new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase) {
    {"notepad","notepad.exe"},{"calculator","calc.exe"},{"explorer","explorer.exe"},{"paint","mspaint.exe"}
  };
  static byte[] ReadExact(Stream stream,int n) {
    byte[] data=new byte[n];int pos=0;
    while(pos<n){int k=stream.Read(data,pos,n-pos);if(k<=0)return null;pos+=k;}return data;
  }
  static void Send(Stream stream,object data){
    byte[] content=Encoding.UTF8.GetBytes(Json.Serialize(data));
    byte[] len=BitConverter.GetBytes(content.Length);
    stream.Write(len,0,4);stream.Write(content,0,content.Length);stream.Flush();
  }
  static object Handle(Dictionary<string,object> request){
    object cmdObj,idObj;request.TryGetValue("command",out cmdObj);request.TryGetValue("id",out idObj);
    string command=Convert.ToString(cmdObj??"");
    if(command=="ping")return new {id=idObj,ok=true,message="Gemini Control Windows Bridge 0.1.0"};
    if(command=="list_apps")return new {id=idObj,ok=true,apps=new string[]{"notepad","calculator","explorer","paint"}};
    if(command=="open_app") {
      object appObj;request.TryGetValue("app",out appObj);
      string app=Convert.ToString(appObj??"");
      string exe;
      if(!Apps.TryGetValue(app,out exe))return new {id=idObj,ok=false,error="Application not on allowlist"};
      var info=new ProcessStartInfo(exe){UseShellExecute=false,CreateNoWindow=false};
      Process.Start(info);
      return new {id=idObj,ok=true,message="Launched "+app};
    }
    return new {id=idObj,ok=false,error="Unknown command"};
  }
  static void Main() {
    Stream input=Console.OpenStandardInput(),output=Console.OpenStandardOutput();
    while(true){
      byte[] length=ReadExact(input,4);if(length==null)break;
      int size=BitConverter.ToInt32(length,0);
      if(size<1||size>64*1024){break;}
      byte[] msg=ReadExact(input,size);if(msg==null)break;
      try {
        var data=Json.Deserialize<Dictionary<string,object>>(Encoding.UTF8.GetString(msg));
        Send(output,Handle(data));
      }catch(Exception e){
        Send(output,new {ok=false,error=e.GetType().Name+": "+e.Message});
      }
    }
  }
}
