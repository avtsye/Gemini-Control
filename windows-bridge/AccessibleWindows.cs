using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Windows.Automation;
using System.Runtime.InteropServices;
public static class AccessibleWindows {
 [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr handle,out uint pid);
 static readonly HashSet<string> Allowed=new HashSet<string>(StringComparer.OrdinalIgnoreCase){"notepad","mspaint","explorer","CalculatorApp"};
 static AutomationElement Target(IntPtr h){if(h==IntPtr.Zero)throw new InvalidOperationException("No active window");
  uint pid;GetWindowThreadProcessId(h,out pid);
  using(var proc=Process.GetProcessById((int)pid))if(!Allowed.Contains(proc.ProcessName))throw new UnauthorizedAccessException("Application not permitted: "+proc.ProcessName);
  var window=AutomationElement.FromHandle(h);if(window==null)throw new InvalidOperationException("Window unavailable");return window;
 }
 static AutomationElement[] Items(IntPtr handle){
  var root=Target(handle);var elements=root.FindAll(TreeScope.Descendants,Condition.TrueCondition);
  var list=new List<AutomationElement>();
  for(int i=0;i<elements.Count&&list.Count<70;i++){
   var el=elements[i];var type=el.Current.ControlType;
   if(type!=ControlType.Button&&type!=ControlType.Edit&&type!=ControlType.ComboBox&&type!=ControlType.CheckBox)continue;
   if(!el.Current.IsEnabled||el.Current.IsOffscreen)continue;
   string label=(el.Current.Name??"").Trim();
   if(label.Length<1||label.Length>100)continue;
   if(el.Current.IsPassword)continue;
   list.Add(el);
  }return list.ToArray();
 }
 public static object Inspect(){
  IntPtr handle=GetForegroundWindow();
  var items=new List<object>();var arr=Items(handle);
  for(int i=0;i<arr.Length;i++)items.Add(new{index=i,label=arr[i].Current.Name,role=arr[i].Current.ControlType.ProgrammaticName.Replace("ControlType.","")});
  return new {handle=handle.ToInt64().ToString(), controls=items};
 }
 public static string Activate(string handleText,int index,string expectedLabel){
  long raw;
  if(!long.TryParse(handleText,out raw))throw new ArgumentException("Invalid target window");
  var list=Items(new IntPtr(raw));if(index<0||index>=list.Length)throw new ArgumentOutOfRangeException("index");
  var item=list[index];
  if(item.Current.Name!=expectedLabel)throw new InvalidOperationException("Control changed; inspect again");
  if(item.Current.ControlType!=ControlType.Button)throw new InvalidOperationException("Only button click supported");
  object pattern;if(!item.TryGetCurrentPattern(InvokePattern.Pattern,out pattern))throw new InvalidOperationException("Button cannot be invoked");
  ((InvokePattern)pattern).Invoke();return "Clicked "+item.Current.Name;
 }
}
