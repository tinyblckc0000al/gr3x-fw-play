// Research-only Ghidra script. Project opened read-only; firmware never written.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.program.model.symbol.*;
public class FollowupAudit extends GhidraScript {
 public void run() throws Exception {
  println("PROGRAM "+currentProgram.getName()+" SHA256 "+currentProgram.getExecutableSHA256());
  long[][] spans={{0x53D453F8L,0x53D45CB0L},{0x53D39C8CL,0x53D3A588L},{0x536EF61CL,0x536EF6DCL},{0x536EF6FCL,0x536EF998L},{0x536EF088L,0x536EF140L},{0x536EF99CL,0x536EF9B8L}};
  for(long[] s:spans){
   println(String.format("SPAN %08x %08x",s[0],s[1]));
   int n=0;
   for(long p=s[0];p<s[1];p++) for(Reference r:currentProgram.getReferenceManager().getReferencesTo(toAddr(p))) {println("XREF "+r);n++;}
   println("DATABASE_XREF_COUNT "+n+" (analysis coverage dependent)");
  }
  DecompInterface d=new DecompInterface(); d.openProgram(currentProgram);
  long[] funcs={0x53633E6CL,0x53633F38L,0x536DB130L,0x536EF140L,0x536DF484L,0x536DF55CL,0x536E4470L};
  for(long p:funcs){
   Address a=toAddr(p);disassemble(a);Function f=getFunctionAt(a);if(f==null) f=createFunction(a,null);
   println(String.format("FUNCTION %08x",p));
   if(f==null){println("NO FUNCTION");continue;}
   println("BODY "+f.getBody());
   DecompileResults r=d.decompileFunction(f,35,monitor);
   if(r.decompileCompleted()&&r.getDecompiledFunction()!=null)println(r.getDecompiledFunction().getC());else println("DECOMPILE_FAILED "+r.getErrorMessage());
  }
  d.dispose();
 }
}
